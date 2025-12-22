"""
Clue Analyzer - NLP-powered polysemy detection and semantic analysis.

This module analyzes trivia clues to detect dual meanings, metaphors, and
category signals using spaCy for production-grade NLP processing.
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
import logging

import spacy
from spacy.tokens import Doc, Token

from .entity_registry import EntityCategory

logger = logging.getLogger(__name__)


class ClueType(str, Enum):
    """
    Clue type based on the Apploff Framework 5-stage pattern.

    Each clue number corresponds to a predictable technique:
    1. Polysemy Trap - Puns using word's secondary meaning
    2. Functional/Attribute - Vague action or characteristic
    3. Pop Culture Pivot - Media/celebrity reference
    4. Direct Hint - Factual or contextual clue
    5. Giveaway - Near-explicit answer reveal
    """
    POLYSEMY = "polysemy"          # Clue 1
    FUNCTIONAL = "functional"      # Clue 2
    POP_CULTURE = "pop_culture"    # Clue 3
    DIRECT_HINT = "direct_hint"    # Clue 4
    GIVEAWAY = "giveaway"          # Clue 5


@dataclass
class ClueAnalysis:
    """
    Result of clue NLP analysis.

    Attributes:
        clue_text: Original clue string
        clue_number: Position in sequence (1-5)
        clue_type: Classified type based on position
        keywords: Extracted important keywords
        polysemous_words: Words with multiple meanings detected
        category_signals: Indicators of Thing/Place/Person
        category_probs: Updated category probabilities
        metaphors: Detected figurative language patterns
        negation_patterns: "Has X but can't Y" style patterns
    """
    clue_text: str
    clue_number: int
    clue_type: ClueType
    keywords: List[str]
    polysemous_words: Dict[str, List[str]]  # word -> possible meanings
    category_signals: Dict[EntityCategory, List[str]]
    category_probs: Dict[EntityCategory, float]
    metaphors: List[str]
    negation_patterns: List[Tuple[str, str]]  # (has, cannot) pairs


class ClueAnalyzer:
    """
    Advanced NLP-powered clue analysis engine.

    Uses spaCy for part-of-speech tagging, dependency parsing, and
    named entity recognition to extract semantic features from clues.
    """

    # Polysemy dictionary - common words with multiple meanings
    POLYSEMY_MAP = {
        "current": ["electricity", "water flow", "present time", "trending"],
        "court": ["basketball court", "legal court", "royal court", "courting/dating"],
        "base": ["foundation", "military base", "baseball base", "basic/simple", "alkaline"],
        "bank": ["financial institution", "river bank", "bank shot", "memory bank"],
        "rock": ["stone", "music genre", "to shake", "diamond/gem"],
        "spring": ["season", "water source", "coil", "to jump"],
        "wave": ["ocean wave", "greeting gesture", "frequency", "to signal"],
        "pitcher": ["baseball player", "water container"],
        "bat": ["baseball bat", "flying mammal"],
        "ring": ["jewelry", "boxing ring", "phone ring", "to circle"],
        "nail": ["fingernail", "metal fastener", "to succeed perfectly"],
        "light": ["illumination", "not heavy", "to ignite"],
        "hard": ["difficult", "solid", "forceful"],
        "party": ["celebration", "political party", "group of people"],
        "suit": ["clothing", "lawsuit", "card suit", "to fit"],
        "jam": ["fruit preserve", "traffic jam", "music session", "to stick"],
        "hot": ["high temperature", "spicy", "trendy", "attractive"],
        "cool": ["low temperature", "calm", "trendy", "acceptable"],
        "sharp": ["pointed", "intelligent", "musical note", "clear/distinct"],
        "flat": ["level surface", "apartment", "deflated", "musical note"],
        "key": ["door key", "musical key", "answer/solution", "important"],
        "basic": ["simple/fundamental", "alkaline chemistry", "boring/mainstream"],
        "capital": ["city", "uppercase letter", "financial resources", "excellent"],
        "charge": ["electrical charge", "to accuse", "to attack", "cost/price"],
        "crane": ["bird", "lifting machine", "to stretch neck"],
        "duck": ["waterfowl", "to dodge", "to lower head"],
        "club": ["weapon", "social group", "playing card suit", "nightclub"],
        "cross": ["religious symbol", "to traverse", "angry", "hybrid"],
        "spell": ["magic incantation", "period of time", "to write letters"],
        "saw": ["cutting tool", "past tense of see", "saying/proverb"],
        "mean": ["average", "unkind", "to signify"],
        "state": ["condition", "US state", "country", "to declare"],
    }

    # Negative definition patterns
    NEGATION_PATTERNS = [
        r"has (\w+) but (?:can't|cannot|doesn't|does not) (\w+)",
        r"has (\w+) but no (\w+)",
        r"(\w+) without (\w+)",
        r"not a (\w+) but",
    ]

    # Category signal words
    CATEGORY_SIGNALS = {
        EntityCategory.PERSON: {
            "pronouns": ["he", "she", "they", "her", "his", "their", "him", "them"],
            "verbs": ["born", "said", "thinks", "believes", "played", "starred", "sang"],
            "nouns": ["celebrity", "actor", "singer", "athlete", "person", "character",
                     "star", "icon", "family", "parent", "child"],
        },
        EntityCategory.PLACE: {
            "prepositions": ["in", "at", "to", "from"],
            "verbs": ["located", "found", "visit", "travel", "built"],
            "nouns": ["city", "country", "landmark", "building", "location", "destination",
                     "monument", "tower", "mountain", "island", "coast"],
            "adjectives": ["geographic", "famous", "historic", "ancient"],
        },
        EntityCategory.THING: {
            "determiners": ["a", "an", "the"],
            "verbs": ["made", "created", "invented", "used", "played", "eaten", "contains"],
            "nouns": ["game", "food", "brand", "product", "object", "item", "tool",
                     "toy", "vehicle", "device", "invention"],
        },
    }

    def __init__(self, model_name: str = "en_core_web_lg"):
        """
        Initialize ClueAnalyzer with spaCy model.

        Args:
            model_name: spaCy model to load (default: en_core_web_lg for best accuracy)
        """
        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"Loaded spaCy model: {model_name}")
        except OSError:
            logger.warning(f"Model {model_name} not found. Run: python -m spacy download {model_name}")
            raise

    def analyze(
        self,
        clue_text: str,
        clue_number: int,
        previous_category_probs: Optional[Dict[EntityCategory, float]] = None
    ) -> ClueAnalysis:
        """
        Perform comprehensive NLP analysis on a clue.

        Args:
            clue_text: The clue text to analyze
            clue_number: Clue position (1-5) for type classification
            previous_category_probs: Category probabilities from previous clues

        Returns:
            ClueAnalysis object with all extracted features
        """
        # Initialize default category priors (60/25/15 distribution)
        if previous_category_probs is None:
            previous_category_probs = {
                EntityCategory.THING: 0.60,
                EntityCategory.PLACE: 0.25,
                EntityCategory.PERSON: 0.15,
            }

        # Parse with spaCy
        doc = self.nlp(clue_text)

        # Classify clue type based on position
        clue_type = self._classify_clue_type(clue_number)

        # Extract keywords (nouns, verbs, adjectives)
        keywords = self._extract_keywords(doc)

        # Detect polysemous words
        polysemous_words = self._detect_polysemy(doc, keywords)

        # Extract category signals
        category_signals = self._extract_category_signals(doc)

        # Update category probabilities
        category_probs = self._update_category_probs(
            previous_category_probs,
            category_signals,
            doc
        )

        # Detect metaphors (figurative language)
        metaphors = self._detect_metaphors(doc)

        # Extract negation patterns
        negation_patterns = self._extract_negation_patterns(clue_text)

        return ClueAnalysis(
            clue_text=clue_text,
            clue_number=clue_number,
            clue_type=clue_type,
            keywords=keywords,
            polysemous_words=polysemous_words,
            category_signals=category_signals,
            category_probs=category_probs,
            metaphors=metaphors,
            negation_patterns=negation_patterns
        )

    def _classify_clue_type(self, clue_number: int) -> ClueType:
        """
        Classify clue type based on position (Apploff Framework).

        Args:
            clue_number: Position in sequence (1-5)

        Returns:
            ClueType enum value
        """
        mapping = {
            1: ClueType.POLYSEMY,
            2: ClueType.FUNCTIONAL,
            3: ClueType.POP_CULTURE,
            4: ClueType.DIRECT_HINT,
            5: ClueType.GIVEAWAY,
        }
        return mapping.get(clue_number, ClueType.DIRECT_HINT)

    def _extract_keywords(self, doc: Doc) -> List[str]:
        """
        Extract important keywords using POS tagging.

        Focuses on nouns, verbs, and adjectives as they carry the most semantic weight.

        Args:
            doc: spaCy Doc object

        Returns:
            List of keyword strings (lemmatized)
        """
        keywords = []

        for token in doc:
            # Skip stop words and punctuation
            if token.is_stop or token.is_punct:
                continue

            # Extract nouns, verbs, adjectives
            if token.pos_ in ["NOUN", "PROPN", "VERB", "ADJ"]:
                # Keep both lemma AND original form for better matching
                # (e.g., "flavors" matches "flavors/editions", but "flavor" doesn't)
                keywords.append(token.lemma_.lower())
                if token.text.lower() != token.lemma_.lower():
                    keywords.append(token.text.lower())

        return keywords

    def _detect_polysemy(
        self,
        doc: Doc,
        keywords: List[str]
    ) -> Dict[str, List[str]]:
        """
        Detect words with multiple meanings using polysemy map.

        Args:
            doc: spaCy Doc object
            keywords: Extracted keywords

        Returns:
            Dictionary mapping polysemous words to their possible meanings
        """
        polysemous = {}

        for token in doc:
            word = token.text.lower()

            # Check if word is in polysemy map
            if word in self.POLYSEMY_MAP:
                polysemous[word] = self.POLYSEMY_MAP[word]

        return polysemous

    def _extract_category_signals(self, doc: Doc) -> Dict[EntityCategory, List[str]]:
        """
        Extract linguistic signals indicating entity category.

        Args:
            doc: spaCy Doc object

        Returns:
            Dictionary mapping categories to detected signal words
        """
        signals = {
            EntityCategory.PERSON: [],
            EntityCategory.PLACE: [],
            EntityCategory.THING: [],
        }

        for token in doc:
            word_lower = token.text.lower()
            pos = token.pos_

            # Check each category's signal words
            for category, signal_sets in self.CATEGORY_SIGNALS.items():
                # Check pronouns (PERSON)
                if "pronouns" in signal_sets and word_lower in signal_sets["pronouns"]:
                    signals[category].append(word_lower)

                # Check verbs
                if "verbs" in signal_sets and pos == "VERB":
                    if token.lemma_.lower() in signal_sets["verbs"]:
                        signals[category].append(token.lemma_.lower())

                # Check nouns
                if "nouns" in signal_sets and pos in ["NOUN", "PROPN"]:
                    if word_lower in signal_sets["nouns"]:
                        signals[category].append(word_lower)

                # Check adjectives
                if "adjectives" in signal_sets and pos == "ADJ":
                    if word_lower in signal_sets["adjectives"]:
                        signals[category].append(word_lower)

                # Check prepositions (PLACE)
                if "prepositions" in signal_sets and pos == "ADP":
                    if word_lower in signal_sets["prepositions"]:
                        signals[category].append(word_lower)

        return signals

    def _update_category_probs(
        self,
        prior_probs: Dict[EntityCategory, float],
        signals: Dict[EntityCategory, List[str]],
        doc: Doc
    ) -> Dict[EntityCategory, float]:
        """
        Update category probabilities based on linguistic signals (Bayesian update).

        Args:
            prior_probs: Previous category probabilities
            signals: Detected category signals
            doc: spaCy Doc object for additional context

        Returns:
            Updated probability distribution over categories
        """
        # Start with priors
        updated_probs = prior_probs.copy()

        # Count signals for each category
        signal_counts = {cat: len(sigs) for cat, sigs in signals.items()}
        total_signals = sum(signal_counts.values())

        if total_signals == 0:
            # No signals detected, keep priors
            return updated_probs

        # Apply Bayesian update: P(category|signals) ∝ P(signals|category) × P(category)
        for category in EntityCategory:
            signal_strength = signal_counts[category] / total_signals
            # Weighted update (0.7 prior + 0.3 signal evidence)
            updated_probs[category] = 0.7 * prior_probs[category] + 0.3 * signal_strength

        # Normalize to sum to 1.0
        total = sum(updated_probs.values())
        if total > 0:
            updated_probs = {cat: prob / total for cat, prob in updated_probs.items()}

        return updated_probs

    def _detect_metaphors(self, doc: Doc) -> List[str]:
        """
        Detect potential metaphorical language patterns.

        Uses dependency parsing to find abstract verb-object relationships.

        Args:
            doc: spaCy Doc object

        Returns:
            List of detected metaphor patterns
        """
        metaphors = []

        for token in doc:
            # Look for abstract verbs with concrete objects (or vice versa)
            if token.dep_ in ["ROOT", "dobj", "pobj"]:
                # Simple heuristic: flag potential figurative language
                if token.pos_ == "VERB":
                    for child in token.children:
                        if child.dep_ == "dobj":
                            metaphors.append(f"{token.text} {child.text}")

        return metaphors

    def _extract_negation_patterns(self, clue_text: str) -> List[Tuple[str, str]]:
        """
        Extract "has X but can't Y" style negation patterns.

        These are common in trivia clues (e.g., "has teeth but can't bite" = comb).

        Args:
            clue_text: Original clue text

        Returns:
            List of (positive_attribute, negative_action) tuples
        """
        patterns = []

        for pattern in self.NEGATION_PATTERNS:
            matches = re.finditer(pattern, clue_text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    patterns.append((match.group(1), match.group(2)))

        return patterns
