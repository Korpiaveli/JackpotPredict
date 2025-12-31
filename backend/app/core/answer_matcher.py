"""
Answer Matcher - Advanced fuzzy matching and answer canonicalization.

Addresses common prediction issues:
1. Name matching (first-name-only answers like Oprah -> Oprah Winfrey)
2. Common confusions disambiguation (Queen Bey -> Beyonce not Honey)
3. Tournament/organization prefix handling (FIFA World Cup, Super Bowl)
4. Improved fuzzy matching with entity registry aliases
"""

import re
import unicodedata
from typing import Optional, List, Tuple, Dict
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


def normalize_unicode(text: str) -> str:
    """
    Normalize Unicode characters to ASCII equivalents.

    Handles accented characters like:
    - BEYONCÉ -> BEYONCE
    - café -> cafe
    - naïve -> naive
    """
    if not text:
        return ""
    # NFKD decomposition splits characters into base + combining marks
    # Then we filter out combining marks (category 'M')
    normalized = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in normalized if not unicodedata.combining(c))


# First-name to full-name mappings for celebrities
# Key: lowercase first name, Value: canonical full name
FIRST_NAME_EXPANSIONS: Dict[str, str] = {
    # Talk show hosts
    "oprah": "Oprah Winfrey",
    "ellen": "Ellen DeGeneres",
    "conan": "Conan O'Brien",
    "jimmy": "Jimmy Fallon",  # Could also be Jimmy Kimmel - handled by context

    # Scientists/Historical figures
    "einstein": "Albert Einstein",
    "darwin": "Charles Darwin",
    "newton": "Isaac Newton",
    "tesla": "Nikola Tesla",
    "edison": "Thomas Edison",
    "galileo": "Galileo Galilei",
    "beethoven": "Ludwig van Beethoven",
    "mozart": "Wolfgang Amadeus Mozart",
    "shakespeare": "William Shakespeare",
    "da vinci": "Leonardo da Vinci",
    "picasso": "Pablo Picasso",
    "michelangelo": "Michelangelo",
    "rembrandt": "Rembrandt",

    # Modern celebrities (single name famous)
    "beyonce": "Beyonce",
    "rihanna": "Rihanna",
    "madonna": "Madonna",
    "cher": "Cher",
    "prince": "Prince",
    "drake": "Drake",
    "shakira": "Shakira",
    "adele": "Adele",
    "eminem": "Eminem",
    "elvis": "Elvis Presley",

    # Athletes
    "lebron": "LeBron James",
    "kobe": "Kobe Bryant",
    "jordan": "Michael Jordan",
    "shaq": "Shaquille O'Neal",
    "serena": "Serena Williams",
    "venus": "Venus Williams",
    "tiger": "Tiger Woods",
    "messi": "Lionel Messi",
    "ronaldo": "Cristiano Ronaldo",
    "pele": "Pele",
    "ali": "Muhammad Ali",

    # Tech figures
    "bezos": "Jeff Bezos",
    "musk": "Elon Musk",
    "zuckerberg": "Mark Zuckerberg",
    "gates": "Bill Gates",
    "jobs": "Steve Jobs",
    "wozniak": "Steve Wozniak",

    # Political/Historical
    "lincoln": "Abraham Lincoln",
    "washington": "George Washington",
    "kennedy": "John F. Kennedy",
    "jfk": "John F. Kennedy",
    "mlk": "Martin Luther King Jr.",
    "gandhi": "Mahatma Gandhi",
    "mandela": "Nelson Mandela",
    "churchill": "Winston Churchill",
    "napoleon": "Napoleon Bonaparte",
    "cleopatra": "Cleopatra",
    "caesar": "Julius Caesar",

    # Actors/Directors
    "dicaprio": "Leonardo DiCaprio",
    "leo": "Leonardo DiCaprio",
    "spielberg": "Steven Spielberg",
    "scorsese": "Martin Scorsese",
    "tarantino": "Quentin Tarantino",
    "deniro": "Robert De Niro",
    "pacino": "Al Pacino",
    "hanks": "Tom Hanks",
    "streep": "Meryl Streep",
    "clooney": "George Clooney",
    "pitt": "Brad Pitt",
    "jolie": "Angelina Jolie",

    # Fictional characters (single name famous)
    "shrek": "Shrek",
    "pikachu": "Pikachu",
    "spongebob": "SpongeBob SquarePants",
    "homer": "Homer Simpson",
    "bart": "Bart Simpson",
    "elsa": "Elsa",
    "yoda": "Yoda",
    "gollum": "Gollum",
    "gandalf": "Gandalf",
    "dumbledore": "Albus Dumbledore",
    "wonder woman": "Wonder Woman",
    "batman": "Batman",
    "superman": "Superman",
    "spiderman": "Spider-Man",
    "spider-man": "Spider-Man",
}

# Celebrity nickname mappings (nickname -> canonical name)
CELEBRITY_NICKNAMES: Dict[str, str] = {
    # Music
    "queen bey": "Beyonce",
    "the king": "Elvis Presley",
    "the king of pop": "Michael Jackson",
    "the queen of pop": "Madonna",
    "the material girl": "Madonna",
    "slim shady": "Eminem",
    "diddy": "P. Diddy",
    "puff daddy": "P. Diddy",
    "snoop": "Snoop Dogg",
    "dre": "Dr. Dre",
    "yeezy": "Kanye West",
    "ye": "Kanye West",
    "hov": "Jay-Z",
    "j-lo": "Jennifer Lopez",
    "jlo": "Jennifer Lopez",

    # Sports
    "his airness": "Michael Jordan",
    "air jordan": "Michael Jordan",
    "the greatest": "Muhammad Ali",
    "the champ": "Muhammad Ali",
    "king james": "LeBron James",
    "the black mamba": "Kobe Bryant",
    "the diesel": "Shaquille O'Neal",
    "goat": "Michael Jordan",  # Context-dependent

    # Historical
    "honest abe": "Abraham Lincoln",
    "the iron lady": "Margaret Thatcher",
    "tricky dick": "Richard Nixon",

    # Actors
    "the governator": "Arnold Schwarzenegger",
    "arnie": "Arnold Schwarzenegger",
}


# Common confusions to disambiguate
# Key: (confused answer, trigger keywords), Value: correct answer
CONFUSION_DISAMBIGUATIONS: List[Tuple[str, List[str], str]] = [
    # Beyonce/Queen Bey confusion
    ("honey", ["queen bey", "beyonce", "singer", "destiny's child", "jay-z", "lemonade",
               "crazy in love", "single ladies", "halo", "formation"], "Beyonce"),
    ("bee", ["queen bey", "beyonce", "singer", "destiny's child"], "Beyonce"),
    ("queen bee", ["singer", "pop star", "houston"], "Beyonce"),

    # Common wordplay traps
    ("cell", ["prison", "jail", "phone", "mobile", "call"], None),  # Context-dependent
    ("bar", ["drink", "pub", "lawyer", "chocolate", "gold"], None),  # Context-dependent

    # Sports confusions
    ("football", ["soccer", "world cup", "fifa"], "FIFA World Cup"),
    ("soccer", ["world cup", "fifa", "international"], "FIFA World Cup"),
]


# Tournament/organization prefixes that should be included
PREFIX_PATTERNS: List[Tuple[str, str]] = [
    # Format: (partial answer, full canonical answer)
    ("world cup", "FIFA World Cup"),
    ("super bowl", "Super Bowl"),
    ("world series", "World Series"),
    ("olympics", "Olympic Games"),
    ("academy awards", "Academy Awards"),
    ("oscars", "Academy Awards"),
    ("grammy", "Grammy Awards"),
    ("grammys", "Grammy Awards"),
    ("emmy", "Emmy Awards"),
    ("emmys", "Emmy Awards"),
    ("tony awards", "Tony Awards"),
    ("tonys", "Tony Awards"),
    ("stanley cup", "Stanley Cup"),
    ("kentucky derby", "Kentucky Derby"),
    ("wimbledon", "Wimbledon"),
    ("masters", "The Masters"),
    ("march madness", "March Madness"),
    ("final four", "Final Four"),
]


# Abbreviation expansions for matching
ABBREVIATION_EXPANSIONS: Dict[str, List[str]] = {
    "mt.": ["mount", "mountain"],
    "mt": ["mount", "mountain"],
    "st.": ["saint", "street"],
    "st": ["saint", "street"],
    "dr.": ["doctor", "drive"],
    "dr": ["doctor", "drive"],
    "jr.": ["junior"],
    "jr": ["junior"],
    "sr.": ["senior"],
    "sr": ["senior"],
    "mr.": ["mister"],
    "mr": ["mister"],
    "mrs.": ["missus", "misses"],
    "mrs": ["missus", "misses"],
    "ms.": ["miss", "ms"],
    "ft.": ["fort", "feet"],
    "ft": ["fort", "feet"],
    "vs.": ["versus"],
    "vs": ["versus"],
    "&": ["and"],
}


def normalize_for_matching(text: str) -> str:
    """
    Normalize text for fuzzy matching.

    - Normalize Unicode (BEYONCÉ -> BEYONCE)
    - Lowercase
    - Remove punctuation except spaces
    - Remove common prefixes (the, a, an)
    - Collapse multiple spaces
    """
    if not text:
        return ""

    # First normalize Unicode to handle accented characters
    normalized = normalize_unicode(text)

    normalized = normalized.lower().strip()

    # Remove punctuation except spaces
    normalized = re.sub(r"[^\w\s]", "", normalized)

    # Remove common prefixes
    prefixes = ["the ", "a ", "an "]
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]

    # Collapse multiple spaces
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def expand_abbreviations(text: str) -> str:
    """
    Expand common abbreviations for better matching.

    Args:
        text: Input text with potential abbreviations

    Returns:
        Text with abbreviations expanded
    """
    result = text.lower()

    for abbrev, expansions in ABBREVIATION_EXPANSIONS.items():
        # Match abbreviation as whole word
        pattern = rf"\b{re.escape(abbrev)}\b"
        if re.search(pattern, result, re.IGNORECASE):
            # Use first expansion
            result = re.sub(pattern, expansions[0], result, flags=re.IGNORECASE)

    return result


def get_first_name_expansion(name: str) -> Optional[str]:
    """
    Expand first-name-only to full canonical name.

    Args:
        name: Potentially first-name-only answer

    Returns:
        Full canonical name if found, None otherwise
    """
    normalized = normalize_for_matching(name)

    # Check first-name expansions first
    if normalized in FIRST_NAME_EXPANSIONS:
        return FIRST_NAME_EXPANSIONS[normalized]

    # Check celebrity nicknames
    if normalized in CELEBRITY_NICKNAMES:
        return CELEBRITY_NICKNAMES[normalized]

    # Check for partial nickname matches (e.g., "queen bey" in "she's called queen bey")
    for nickname, canonical in CELEBRITY_NICKNAMES.items():
        if nickname in normalized:
            return canonical

    return None


def get_prefix_canonical(answer: str) -> Optional[str]:
    """
    Get canonical form for tournament/organization names.

    Args:
        answer: Potentially partial answer

    Returns:
        Full canonical form if found, None otherwise
    """
    normalized = normalize_for_matching(answer)

    for partial, canonical in PREFIX_PATTERNS:
        if partial in normalized or normalized in partial:
            return canonical

    return None


def disambiguate_confusion(
    answer: str,
    clue_context: str
) -> Optional[str]:
    """
    Check if answer is a common confusion and return correct answer.

    Args:
        answer: Predicted answer that might be confused
        clue_context: All clues concatenated for context

    Returns:
        Correct disambiguated answer if confusion detected, None otherwise
    """
    normalized_answer = normalize_for_matching(answer)
    normalized_context = clue_context.lower()

    for confused, triggers, correct in CONFUSION_DISAMBIGUATIONS:
        if normalized_answer == confused or confused in normalized_answer:
            # Check if trigger keywords are present in clues
            trigger_matches = sum(1 for t in triggers if t in normalized_context)

            if trigger_matches >= 2 and correct:
                logger.info(f"Disambiguation: '{answer}' -> '{correct}' (triggers: {trigger_matches})")
                return correct

    return None


def fuzzy_match_score(s1: str, s2: str) -> float:
    """
    Calculate fuzzy match score between two strings.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score 0.0 to 1.0
    """
    n1 = normalize_for_matching(s1)
    n2 = normalize_for_matching(s2)

    if not n1 or not n2:
        return 0.0

    # Exact match after normalization
    if n1 == n2:
        return 1.0

    # Check abbreviation expansion match
    e1 = expand_abbreviations(n1)
    e2 = expand_abbreviations(n2)
    if e1 == e2:
        return 0.98

    # Check if one contains the other (partial match)
    if n1 in n2 or n2 in n1:
        return 0.9

    # Check first-name expansion
    exp1 = get_first_name_expansion(n1)
    exp2 = get_first_name_expansion(n2)
    if exp1 and normalize_for_matching(exp1) == n2:
        return 0.95
    if exp2 and normalize_for_matching(exp2) == n1:
        return 0.95

    # Sequence matcher for fuzzy matching
    return SequenceMatcher(None, n1, n2).ratio()


def answers_match(
    predicted: str,
    correct: str,
    threshold: float = 0.85
) -> bool:
    """
    Determine if predicted answer matches correct answer.

    Handles:
    - Case insensitivity
    - Common prefixes (the, a, an)
    - Abbreviations (Mt. -> Mount, St. -> Saint)
    - First-name expansions (Oprah -> Oprah Winfrey)
    - Partial matches for long names

    Args:
        predicted: Model's predicted answer
        correct: Known correct answer
        threshold: Minimum similarity score to consider a match

    Returns:
        True if answers match, False otherwise
    """
    score = fuzzy_match_score(predicted, correct)
    return score >= threshold


def canonicalize_answer(
    answer: str,
    clue_context: Optional[str] = None,
    entity_registry = None
) -> str:
    """
    Convert answer to canonical form.

    Applies in order:
    1. Disambiguation check (if context provided)
    2. First-name expansion
    3. Prefix canonical form
    4. Entity registry lookup (if provided)

    Args:
        answer: Raw answer to canonicalize
        clue_context: Optional concatenated clue text for disambiguation
        entity_registry: Optional EntityRegistry for alias lookup

    Returns:
        Canonical form of answer
    """
    if not answer:
        return answer

    # Step 1: Check for common confusions
    if clue_context:
        disambiguated = disambiguate_confusion(answer, clue_context)
        if disambiguated:
            return disambiguated

    # Step 2: Try first-name expansion
    expanded = get_first_name_expansion(answer)
    if expanded:
        return expanded

    # Step 3: Try prefix canonical form
    prefix_form = get_prefix_canonical(answer)
    if prefix_form:
        return prefix_form

    # Step 4: Try entity registry lookup
    if entity_registry:
        try:
            canonical = entity_registry.get_canonical_spelling(answer)
            if canonical:
                return canonical
        except Exception as e:
            logger.warning(f"Entity registry lookup failed: {e}")

    # Return original if no canonicalization found
    return answer


def rank_answer_candidates(
    candidates: List[str],
    clue_context: str,
    entity_registry = None
) -> List[Tuple[str, float]]:
    """
    Rank and deduplicate answer candidates.

    Groups similar answers and returns ranked list with scores.

    Args:
        candidates: List of candidate answers from agents
        clue_context: Concatenated clue text
        entity_registry: Optional entity registry

    Returns:
        List of (canonical_answer, score) tuples, sorted by score descending
    """
    # Canonicalize all candidates
    canonicalized = []
    for candidate in candidates:
        canonical = canonicalize_answer(candidate, clue_context, entity_registry)
        canonicalized.append((candidate, canonical))

    # Group by canonical form
    groups: Dict[str, List[str]] = {}
    for original, canonical in canonicalized:
        normalized = normalize_for_matching(canonical)
        if normalized not in groups:
            groups[normalized] = []
        groups[normalized].append(canonical)

    # Score each group by frequency and preference for canonical forms
    ranked = []
    for normalized, versions in groups.items():
        # Use most common version as representative
        from collections import Counter
        most_common = Counter(versions).most_common(1)[0][0]

        # Score based on frequency
        score = len(versions) / len(candidates)

        ranked.append((most_common, score))

    # Sort by score descending
    ranked.sort(key=lambda x: x[1], reverse=True)

    return ranked


# Riddle pattern detection for abstract clues
RIDDLE_PATTERNS: List[Tuple[str, str, float]] = [
    # Format: (pattern, category_hint, confidence_boost)
    (r"what (has|have|am i)", "riddle", 0.1),
    (r"i (am|have|can)", "riddle", 0.1),
    (r"without (me|this)", "riddle", 0.1),
    (r"the more.*the (less|more)", "riddle", 0.15),
    (r"(black|white|hot|cold) (and|yet|but) (black|white|hot|cold)", "contrast", 0.1),
    (r"can('t| not) (be seen|see|touch|hold)", "abstract", 0.1),
    (r"everywhere (and|but) nowhere", "abstract", 0.15),
]


def detect_riddle_pattern(clue: str) -> Optional[Tuple[str, float]]:
    """
    Detect if clue uses riddle patterns.

    Args:
        clue: Single clue text

    Returns:
        (pattern_type, confidence_adjustment) if riddle pattern detected, None otherwise
    """
    normalized = clue.lower()

    for pattern, pattern_type, boost in RIDDLE_PATTERNS:
        if re.search(pattern, normalized):
            return (pattern_type, boost)

    return None


def analyze_clue_abstractness(clues: List[str]) -> Dict[str, any]:
    """
    Analyze how abstract/riddle-like the clue set is.

    Args:
        clues: List of clue texts

    Returns:
        Analysis dict with abstractness score and detected patterns
    """
    riddle_count = 0
    detected_patterns = []
    total_boost = 0.0

    for clue in clues:
        result = detect_riddle_pattern(clue)
        if result:
            pattern_type, boost = result
            riddle_count += 1
            detected_patterns.append(pattern_type)
            total_boost += boost

    abstractness_score = riddle_count / len(clues) if clues else 0

    return {
        "abstractness_score": abstractness_score,
        "riddle_count": riddle_count,
        "patterns": detected_patterns,
        "confidence_adjustment": min(total_boost, 0.3),  # Cap at 30%
        "is_abstract": abstractness_score >= 0.4
    }
