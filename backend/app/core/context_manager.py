"""
Context Manager - Dynamic few-shot example selection for Best Guess Live.

This module provides historical game context to the LLM through intelligently
selected examples that match the current game's category or demonstrate
key reasoning patterns.
"""

import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HistoricalGame:
    """Single historical game record."""
    category: str
    clues: List[str]
    answer: str
    clue_solved_at: int
    key_insight: str


class HistoricalDataManager:
    """
    Dynamic few-shot example selector from historical game data.

    Loads past games and selects relevant examples to inject into the
    LLM system prompt, teaching it the specific reasoning patterns
    needed for Best Guess Live trivia.
    """

    DEFAULT_HISTORY_PATH = Path(__file__).parent.parent / "data" / "history.json"

    def __init__(self, history_path: Optional[str] = None):
        """
        Initialize with historical game data.

        Args:
            history_path: Path to history.json (uses default if None)
        """
        self.history_path = Path(history_path) if history_path else self.DEFAULT_HISTORY_PATH
        self.games: List[HistoricalGame] = []
        self._load_history()

    def _load_history(self):
        """Load historical game data from JSON file."""
        try:
            if not self.history_path.exists():
                logger.warning(f"History file not found: {self.history_path}")
                return

            with open(self.history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for game in data:
                self.games.append(HistoricalGame(
                    category=game.get('category', 'thing'),
                    clues=game.get('clues', []),
                    answer=game.get('answer', ''),
                    clue_solved_at=game.get('clue_solved_at', 3),
                    key_insight=game.get('key_insight', '')
                ))

            logger.info(f"Loaded {len(self.games)} historical games from {self.history_path}")

        except Exception as e:
            logger.error(f"Error loading history: {e}")

    def get_dynamic_prompt(
        self,
        current_category: Optional[str] = None,
        num_examples: int = 3
    ) -> str:
        """
        Select relevant examples for few-shot learning.

        Prioritizes examples matching the current category, falling back
        to high-quality general examples that demonstrate key reasoning.

        Args:
            current_category: Optional category hint (e.g., "person", "place", "thing")
            num_examples: Number of examples to include (default: 3)

        Returns:
            Formatted string of examples for system prompt injection.
        """
        if not self.games:
            return self._get_fallback_examples()

        selected: List[HistoricalGame] = []

        # Normalize category
        if current_category:
            current_category = current_category.lower().strip()

        # Strategy 1: Find category matches
        if current_category:
            category_matches = [g for g in self.games if g.category.lower() == current_category]
            if category_matches:
                # Select games that were solved early (clue 1-2) as they show best patterns
                early_solves = sorted(category_matches, key=lambda g: g.clue_solved_at)
                selected.extend(early_solves[:min(2, len(early_solves))])

        # Strategy 2: Add wordplay/polysemy examples (these teach lateral thinking)
        wordplay_examples = [
            g for g in self.games
            if any(keyword in g.key_insight.lower() for keyword in [
                'double meaning', 'wordplay', 'triple meaning', 'multiple meanings'
            ])
        ]
        for game in wordplay_examples:
            if game not in selected and len(selected) < num_examples:
                selected.append(game)

        # Strategy 3: Fill remaining with diverse high-quality examples
        remaining_slots = num_examples - len(selected)
        if remaining_slots > 0:
            # Get games with good insights that aren't already selected
            candidates = [g for g in self.games if g not in selected and g.key_insight]

            # Prefer diverse categories
            categories_used = {g.category for g in selected}
            diverse_candidates = [g for g in candidates if g.category not in categories_used]

            if diverse_candidates:
                random.shuffle(diverse_candidates)
                selected.extend(diverse_candidates[:remaining_slots])
            elif candidates:
                random.shuffle(candidates)
                selected.extend(candidates[:remaining_slots])

        return self._format_examples(selected)

    def _format_examples(self, games: List[HistoricalGame]) -> str:
        """Format selected games as prompt examples."""
        if not games:
            return self._get_fallback_examples()

        lines = ["EXAMPLES FROM PAST GAMES:", ""]

        for i, game in enumerate(games, 1):
            category_label = game.category.upper()
            clues_formatted = "', '".join(game.clues[:3])  # First 3 clues only

            lines.append(f"Example {i} ({category_label}):")
            lines.append(f"  Clues: '{clues_formatted}'")
            lines.append(f"  Answer: {game.answer}")
            lines.append(f"  Key insight: {game.key_insight}")
            lines.append("")

        return "\n".join(lines)

    def _get_fallback_examples(self) -> str:
        """Provide hardcoded examples if no history available."""
        return """EXAMPLES FROM PAST GAMES:

Example 1 (PERSON):
  Clues: 'Her family is extremely hospitable', 'Named after a romantic city'
  Answer: Paris Hilton
  Key insight: 'hospitable' -> Hilton Hotels -> Paris Hilton (wordplay on hotel industry)

Example 2 (THING):
  Clues: 'A hostile takeover', 'Jail time can be dicey'
  Answer: Monopoly
  Key insight: 'hostile takeover' is business term used in the board game; 'dicey' refers to dice

Example 3 (THING):
  Clues: 'A river runs through it', 'Prime delivery', 'Alexa's parent'
  Answer: Amazon
  Key insight: Double meaning - both the river AND the company; 'Prime' is their service
"""

    def add_game_result(
        self,
        category: str,
        clues: List[str],
        answer: str,
        solved_at_clue: int,
        key_insight: str = ""
    ) -> bool:
        """
        Add new game result to history (for learning over time).

        Args:
            category: Entity category (person/place/thing)
            clues: List of clue texts
            answer: Correct answer
            solved_at_clue: Clue number when solved (1-5)
            key_insight: Optional insight about the solution

        Returns:
            True if successfully saved
        """
        try:
            new_game = HistoricalGame(
                category=category.lower(),
                clues=clues,
                answer=answer,
                clue_solved_at=solved_at_clue,
                key_insight=key_insight
            )
            self.games.append(new_game)

            # Save to file
            self._save_history()
            logger.info(f"Added new game to history: {answer}")
            return True

        except Exception as e:
            logger.error(f"Error adding game to history: {e}")
            return False

    def _save_history(self):
        """Save current history to JSON file."""
        try:
            data = [
                {
                    'category': g.category,
                    'clues': g.clues,
                    'answer': g.answer,
                    'clue_solved_at': g.clue_solved_at,
                    'key_insight': g.key_insight
                }
                for g in self.games
            ]

            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error saving history: {e}")

    def get_stats(self) -> Dict:
        """Get statistics about historical data."""
        if not self.games:
            return {'total_games': 0}

        category_counts = {}
        solve_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

        for game in self.games:
            cat = game.category.lower()
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if 1 <= game.clue_solved_at <= 5:
                solve_distribution[game.clue_solved_at] += 1

        return {
            'total_games': len(self.games),
            'by_category': category_counts,
            'solve_distribution': solve_distribution,
            'avg_solve_clue': sum(g.clue_solved_at for g in self.games) / len(self.games)
        }


# Singleton instance
_context_manager: Optional[HistoricalDataManager] = None


def get_context_manager() -> HistoricalDataManager:
    """Get or create the context manager singleton."""
    global _context_manager
    if _context_manager is None:
        _context_manager = HistoricalDataManager()
    return _context_manager


# =============================================================================
# CULTURAL CONTEXT MANAGER (MOA Optimization v3)
# Provides adversarial counter-reasoning context for Oracle
# =============================================================================

import re
from datetime import datetime


@dataclass
class CulturalMatch:
    """A detected cultural reference match."""
    keyword: str
    answer: str
    source: str
    confidence: float  # 0.0 to 1.0


@dataclass
class HistoricalPuzzleMatch:
    """A similar historical puzzle match."""
    date: str
    answer: str
    similarity_score: float
    matching_patterns: List[str]
    key_clue: str


class CulturalContextManager:
    """
    Provides cultural, temporal, and historical context for Oracle analysis.

    Uses in-memory caching for <10ms lookup latency.
    Enables adversarial counter-reasoning by detecting misdirection patterns.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize context manager with data files.

        Args:
            data_dir: Directory containing cultural_references.json and
                     historical_puzzles.json. Defaults to app/data/.
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"

        self.data_dir = data_dir

        # Load and cache data
        self._cultural_refs: Dict = {}
        self._historical_puzzles: Dict = {}
        self._quote_keywords: Dict[str, Dict] = {}  # keyword -> quote info
        self._pattern_keywords: Dict[str, Dict] = {}  # keyword -> pattern info

        self._load_data()

    def _load_data(self) -> None:
        """Load cultural references and historical puzzles into memory."""
        # Load cultural references
        cultural_path = self.data_dir / "cultural_references.json"
        if cultural_path.exists():
            try:
                with open(cultural_path, 'r', encoding='utf-8') as f:
                    self._cultural_refs = json.load(f)

                # Build keyword lookup indexes for fast matching
                for quote, info in self._cultural_refs.get("quotes", {}).items():
                    for keyword in info.get("keywords", []):
                        self._quote_keywords[keyword.lower()] = {
                            "quote": quote,
                            **info
                        }

                for pattern_name, info in self._cultural_refs.get("wordplay_patterns", {}).items():
                    for keyword in info.get("keywords", []):
                        self._pattern_keywords[keyword.lower()] = {
                            "pattern": pattern_name,
                            **info
                        }

                logger.info(f"[CulturalContext] Loaded {len(self._cultural_refs.get('quotes', {}))} quotes, "
                           f"{len(self._cultural_refs.get('wordplay_patterns', {}))} patterns")
            except Exception as e:
                logger.error(f"[CulturalContext] Error loading cultural references: {e}")

        # Load historical puzzles
        historical_path = self.data_dir / "historical_puzzles.json"
        if historical_path.exists():
            try:
                with open(historical_path, 'r', encoding='utf-8') as f:
                    self._historical_puzzles = json.load(f)

                puzzle_count = len(self._historical_puzzles.get("puzzles", []))
                logger.info(f"[CulturalContext] Loaded {puzzle_count} historical puzzles")
            except Exception as e:
                logger.error(f"[CulturalContext] Error loading historical puzzles: {e}")

    def detect_cultural_references(self, clues: List[str]) -> List[CulturalMatch]:
        """
        Detect cultural references (quotes, catchphrases) in clues.

        Args:
            clues: List of clues to analyze

        Returns:
            List of CulturalMatch objects with detected references
        """
        matches = []
        clue_text = " ".join(clues).lower()

        # Check for quote keywords
        for keyword, info in self._quote_keywords.items():
            if keyword in clue_text:
                # Higher confidence if keyword appears in later clues (4-5)
                clue_idx = next(
                    (i for i, c in enumerate(clues) if keyword in c.lower()),
                    0
                )
                confidence = 0.6 + (clue_idx * 0.1)  # 0.6-0.9 based on clue number

                matches.append(CulturalMatch(
                    keyword=keyword,
                    answer=info["answer"],
                    source=info.get("source", "Unknown"),
                    confidence=min(confidence, 0.95)
                ))

        # Check for pattern keywords
        for keyword, info in self._pattern_keywords.items():
            if keyword in clue_text:
                clue_idx = next(
                    (i for i, c in enumerate(clues) if keyword in c.lower()),
                    0
                )
                confidence = 0.5 + (clue_idx * 0.1)

                matches.append(CulturalMatch(
                    keyword=keyword,
                    answer=info["answer"],
                    source=info.get("pattern_type", "wordplay"),
                    confidence=min(confidence, 0.85)
                ))

        # Deduplicate by answer, keeping highest confidence
        answer_matches: Dict[str, CulturalMatch] = {}
        for match in matches:
            if match.answer not in answer_matches or match.confidence > answer_matches[match.answer].confidence:
                answer_matches[match.answer] = match

        return sorted(answer_matches.values(), key=lambda m: m.confidence, reverse=True)

    def find_similar_puzzles(self, clues: List[str], top_k: int = 3) -> List[HistoricalPuzzleMatch]:
        """
        Find similar historical puzzles based on clue patterns.

        Args:
            clues: List of clues to match against
            top_k: Number of top matches to return

        Returns:
            List of HistoricalPuzzleMatch objects
        """
        matches = []
        clue_text = " ".join(clues).lower()
        clue_words = set(re.findall(r'\w+', clue_text))

        for puzzle in self._historical_puzzles.get("puzzles", []):
            puzzle_clues = puzzle.get("clues", [])
            puzzle_text = " ".join(puzzle_clues).lower()
            puzzle_words = set(re.findall(r'\w+', puzzle_text))

            # Calculate Jaccard-like similarity
            intersection = len(clue_words & puzzle_words)
            union = len(clue_words | puzzle_words)

            if union > 0:
                similarity = intersection / union

                # Boost if patterns match
                matching_patterns = []
                for pattern in puzzle.get("patterns", []):
                    if pattern.lower() in clue_text:
                        matching_patterns.append(pattern)
                        similarity += 0.1

                if similarity > 0.15:  # Threshold for relevance
                    matches.append(HistoricalPuzzleMatch(
                        date=puzzle.get("date", "Unknown"),
                        answer=puzzle.get("answer", "Unknown"),
                        similarity_score=min(similarity, 1.0),
                        matching_patterns=matching_patterns,
                        key_clue=puzzle_clues[-1] if puzzle_clues else ""
                    ))

        # Sort by similarity and return top_k
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches[:top_k]

    def get_temporal_context(self) -> str:
        """
        Get temporal context (date, holidays, special events).

        Returns:
            String with temporal context for injection
        """
        now = datetime.now()
        context_parts = []

        context_parts.append(f"Today: {now.strftime('%A, %B %d, %Y')}")

        # Check for holidays/special dates
        month_day = (now.month, now.day)
        holidays = {
            (1, 1): "New Year's Day",
            (2, 14): "Valentine's Day",
            (3, 17): "St. Patrick's Day",
            (4, 1): "April Fools' Day",
            (7, 4): "Independence Day (USA)",
            (10, 31): "Halloween",
            (11, 11): "Veterans Day",
            (12, 24): "Christmas Eve",
            (12, 25): "Christmas Day",
            (12, 31): "New Year's Eve",
        }

        if month_day in holidays:
            context_parts.append(f"Holiday: {holidays[month_day]}")

        # Check for December (holiday season)
        if now.month == 12:
            context_parts.append("Season: Holiday season - expect Christmas/winter themed answers")

        return " | ".join(context_parts)

    def get_category_priors(self) -> Dict[str, float]:
        """
        Get category priors from historical data.

        Returns:
            Dict mapping category to probability (e.g., {"thing": 0.65})
        """
        return self._cultural_refs.get("category_priors", {
            "thing": 0.65,
            "person": 0.20,
            "place": 0.15
        })

    def get_clue_strategy(self, clue_number: int) -> str:
        """
        Get strategy guidance for specific clue number.

        Args:
            clue_number: Current clue number (1-5)

        Returns:
            Strategy string for the clue
        """
        strategies = self._cultural_refs.get("clue_number_strategy", {})
        return strategies.get(str(clue_number), "Analyze carefully for patterns")

    def build_context_injection(
        self,
        clues: List[str],
        clue_number: int,
        include_similar: bool = True
    ) -> str:
        """
        Build complete context injection string for Oracle.

        Args:
            clues: List of clues revealed so far
            clue_number: Current clue number (1-5)
            include_similar: Whether to include similar historical puzzles

        Returns:
            Formatted context string for injection into Oracle prompt
        """
        sections = []

        # 1. Temporal context
        temporal = self.get_temporal_context()
        sections.append(f"[TEMPORAL] {temporal}")

        # 2. Clue strategy
        strategy = self.get_clue_strategy(clue_number)
        sections.append(f"[STRATEGY] Clue {clue_number}: {strategy}")

        # 3. Cultural reference detection
        cultural_matches = self.detect_cultural_references(clues)
        if cultural_matches:
            cultural_strs = [
                f"'{m.keyword}' -> {m.answer} ({m.source}, {int(m.confidence*100)}%)"
                for m in cultural_matches[:3]
            ]
            sections.append(f"[CULTURAL REFERENCES DETECTED] {' | '.join(cultural_strs)}")

        # 4. Similar historical puzzles (optional, for pattern matching)
        if include_similar and clue_number >= 3:
            similar = self.find_similar_puzzles(clues, top_k=2)
            if similar:
                similar_strs = [
                    f"{m.answer} ({m.date}, {int(m.similarity_score*100)}% match)"
                    for m in similar
                ]
                sections.append(f"[SIMILAR PAST PUZZLES] {' | '.join(similar_strs)}")

        # 5. Category priors reminder
        priors = self.get_category_priors()
        prior_str = f"THING {int(priors.get('thing', 0.65)*100)}% | PERSON {int(priors.get('person', 0.20)*100)}% | PLACE {int(priors.get('place', 0.15)*100)}%"
        sections.append(f"[CATEGORY PRIORS] {prior_str}")

        return "\n".join(sections)


# Singleton instance for CulturalContextManager
_cultural_context_manager: Optional[CulturalContextManager] = None


def get_cultural_context_manager() -> CulturalContextManager:
    """Get or create singleton CulturalContextManager instance."""
    global _cultural_context_manager
    if _cultural_context_manager is None:
        _cultural_context_manager = CulturalContextManager()
    return _cultural_context_manager


# System prompt template with placeholder for dynamic examples
BEST_GUESS_PROMPT = """You are a competitive trivia expert playing "Best Guess Live."
Your goal is to identify the answer based on a sequence of vague clues.

{dynamic_examples}

RULES:
1. Clues start VERY vague (Clue 1) and get more specific (Clue 5 is nearly a giveaway).
2. Output "WAIT" if confidence is < 40% - it's better to wait for more clues.
3. Look for lateral thinking and wordplay:
   - "hospitable" -> Hilton Hotels -> Paris Hilton
   - "hostile takeover" -> Monopoly (board game business term)
   - "dicey" -> dice -> board games
   - Double meanings: "Subway" could be trains OR sandwiches
4. Categories are: PERSON, PLACE, or THING (brands, games, shows, food all count as THING).
5. Consider ALL clues together - they build on each other.

FORMAT YOUR RESPONSE EXACTLY AS:
Reasoning: [Brief step-by-step logic, max 2 sentences]
GUESS: [Your single answer OR "WAIT"]
CONFIDENCE: [0-100%]
"""


def build_system_prompt(category_hint: Optional[str] = None) -> str:
    """
    Build complete system prompt with dynamic few-shot examples.

    Args:
        category_hint: Optional category to bias example selection

    Returns:
        Complete system prompt string
    """
    manager = get_context_manager()
    examples = manager.get_dynamic_prompt(current_category=category_hint)
    return BEST_GUESS_PROMPT.format(dynamic_examples=examples)
