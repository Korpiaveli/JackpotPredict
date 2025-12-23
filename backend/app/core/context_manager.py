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
