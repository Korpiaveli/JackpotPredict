"""
Spelling Validator - Critical validation for exact-match submissions.

This module ensures all answer predictions match exact spelling requirements.
ONE TYPO = ELIMINATION - this is the highest-risk failure mode.
"""

import re
from typing import Optional, Tuple, List
from dataclasses import dataclass
import logging

from Levenshtein import distance as levenshtein_distance

from .entity_registry import EntityRegistry

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of spelling validation.

    Attributes:
        is_valid: True if answer meets all requirements
        formatted_answer: Correctly formatted answer (if valid)
        error_message: Explanation if invalid
        suggestion: Suggested correction (if applicable)
        issues: List of specific validation issues found
    """
    is_valid: bool
    formatted_answer: Optional[str]
    error_message: Optional[str]
    suggestion: Optional[str]
    issues: List[str]


class SpellingValidator:
    """
    Exact-match spelling validation with fuzzy matching for suggestions.

    Validates that answers meet Netflix Best Guess Live requirements:
    - Exact spelling (case-insensitive but character-perfect)
    - Full names required ("Paris Hilton" not "Paris")
    - No abbreviations ("International Olympic Committee" not "IOC")
    - No extra articles unless part of official name
    """

    # Common abbreviations to reject
    ABBREVIATIONS = {
        "IOC": "International Olympic Committee",
        "UN": "United Nations",
        "US": "United States",
        "UK": "United Kingdom",
        "NBA": "National Basketball Association",
        "NFL": "National Football League",
        "MLB": "Major League Baseball",
        "NHL": "National Hockey League",
        "FBI": "Federal Bureau of Investigation",
        "CIA": "Central Intelligence Agency",
        "NASA": "National Aeronautics and Space Administration",
        "SCOTUS": "Supreme Court of the United States",
    }

    # Articles to strip (unless part of official name)
    ARTICLES = ["the", "a", "an"]

    # Levenshtein distance threshold for fuzzy matching
    FUZZY_THRESHOLD = 2  # Max 2 character differences

    def __init__(self, entity_registry: EntityRegistry):
        """
        Initialize SpellingValidator.

        Args:
            entity_registry: EntityRegistry for canonical name lookup
        """
        self.registry = entity_registry

    def validate(self, answer: str) -> ValidationResult:
        """
        Validate answer against all spelling requirements.

        Args:
            answer: Answer string to validate

        Returns:
            ValidationResult with validation status and details
        """
        issues = []
        answer_clean = answer.strip()

        # 1. Check for empty answer
        if not answer_clean:
            return ValidationResult(
                is_valid=False,
                formatted_answer=None,
                error_message="Answer cannot be empty",
                suggestion=None,
                issues=["empty_answer"]
            )

        # 2. Check for abbreviations
        if answer_clean.upper() in self.ABBREVIATIONS:
            full_name = self.ABBREVIATIONS[answer_clean.upper()]
            return ValidationResult(
                is_valid=False,
                formatted_answer=None,
                error_message=f"Abbreviations not allowed. Use full name.",
                suggestion=full_name,
                issues=["abbreviation"]
            )

        # 3. Get canonical spelling from registry
        canonical = self.registry.get_canonical_spelling(answer_clean)

        if canonical:
            # Exact match found (case-insensitive)
            # 4. Check for partial name (if canonical has multiple words)
            if self._is_partial_name(answer_clean, canonical):
                return ValidationResult(
                    is_valid=False,
                    formatted_answer=None,
                    error_message="Partial names not allowed. Use full name.",
                    suggestion=canonical,
                    issues=["partial_name"]
                )

            # 5. Success! Answer is valid
            return ValidationResult(
                is_valid=True,
                formatted_answer=canonical,
                error_message=None,
                suggestion=None,
                issues=[]
            )

        # 6. No exact match - try fuzzy matching for suggestions
        fuzzy_match, distance = self._find_fuzzy_match(answer_clean)

        if fuzzy_match:
            return ValidationResult(
                is_valid=False,
                formatted_answer=None,
                error_message=f"Spelling error detected (distance: {distance})",
                suggestion=fuzzy_match,
                issues=["spelling_error"]
            )

        # 7. No match at all - answer not in registry
        return ValidationResult(
            is_valid=False,
            formatted_answer=None,
            error_message="Answer not found in entity registry",
            suggestion=None,
            issues=["not_found"]
        )

    def _is_partial_name(self, user_input: str, canonical: str) -> bool:
        """
        Check if user input is a partial name (e.g., "Paris" vs "Paris Hilton").

        Args:
            user_input: User's answer
            canonical: Canonical full name

        Returns:
            True if user_input is a substring of canonical but not full match
        """
        user_lower = user_input.lower().strip()
        canonical_lower = canonical.lower().strip()

        # If identical (case-insensitive), not partial
        if user_lower == canonical_lower:
            return False

        # Split into words
        user_words = user_lower.split()
        canonical_words = canonical_lower.split()

        # If canonical has multiple words and user only has one
        if len(canonical_words) > 1 and len(user_words) == 1:
            # Check if user word appears in canonical
            if user_words[0] in canonical_words:
                return True

        # If user has fewer words but all match beginning/end of canonical
        if len(user_words) < len(canonical_words):
            # Check if user words are a subset
            if all(word in canonical_words for word in user_words):
                return True

        return False

    def _find_fuzzy_match(
        self,
        answer: str,
        max_distance: int = None
    ) -> Tuple[Optional[str], int]:
        """
        Find closest matching entity name using Levenshtein distance.

        Args:
            answer: Answer to match
            max_distance: Maximum allowed edit distance (default: FUZZY_THRESHOLD)

        Returns:
            (best_match, distance) tuple, or (None, -1) if no close match
        """
        if max_distance is None:
            max_distance = self.FUZZY_THRESHOLD

        answer_lower = answer.lower().strip()

        # Get all entities from registry
        # Note: This is potentially slow for 10K+ entities, but necessary for accuracy
        # In production, could optimize with BK-tree or similar structure
        all_entities = self.registry._get_all_entities()

        best_match = None
        best_distance = float('inf')

        for entity in all_entities:
            # Check canonical name
            dist = levenshtein_distance(answer_lower, entity.canonical_name.lower())
            if dist < best_distance:
                best_distance = dist
                best_match = entity.canonical_name

            # Also check aliases
            for alias in entity.aliases:
                dist = levenshtein_distance(answer_lower, alias.lower())
                if dist < best_distance:
                    best_distance = dist
                    best_match = entity.canonical_name  # Always return canonical

        # Only return if distance is within threshold
        if best_distance <= max_distance:
            return best_match, int(best_distance)

        return None, -1

    def batch_validate(self, answers: List[str]) -> List[ValidationResult]:
        """
        Validate multiple answers efficiently.

        Args:
            answers: List of answer strings

        Returns:
            List of ValidationResult objects (same order as input)
        """
        return [self.validate(answer) for answer in answers]

    def get_canonical_or_suggest(self, answer: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Convenience method: Get canonical spelling or suggestion.

        Args:
            answer: Answer to validate

        Returns:
            (is_valid, canonical_or_suggestion, error_message) tuple
        """
        result = self.validate(answer)

        if result.is_valid:
            return True, result.formatted_answer, None
        else:
            return False, result.suggestion, result.error_message

    def strip_articles(self, answer: str) -> str:
        """
        Remove leading articles ("the", "a", "an") unless part of official name.

        Args:
            answer: Answer string

        Returns:
            Answer with article stripped (if appropriate)
        """
        words = answer.split()

        if words and words[0].lower() in self.ARTICLES:
            # Check if canonical name includes the article
            canonical = self.registry.get_canonical_spelling(answer)
            if canonical and canonical.lower().startswith(words[0].lower()):
                # Article is part of official name, keep it
                return answer
            else:
                # Strip article
                return " ".join(words[1:])

        return answer

    def suggest_full_name(self, partial_name: str) -> List[str]:
        """
        Suggest full names matching a partial input.

        Useful for autocomplete/suggestions during gameplay.

        Args:
            partial_name: Partial name (e.g., "Paris")

        Returns:
            List of canonical full names matching the partial
        """
        partial_lower = partial_name.lower().strip()
        suggestions = []

        # Get all entities
        all_entities = self.registry._get_all_entities()

        for entity in all_entities:
            # Check if partial matches any word in canonical name
            canonical_words = entity.canonical_name.lower().split()
            if any(word.startswith(partial_lower) for word in canonical_words):
                suggestions.append(entity.canonical_name)

            # Also check aliases
            for alias in entity.aliases:
                if alias.lower().startswith(partial_lower):
                    suggestions.append(entity.canonical_name)
                    break

        # Remove duplicates and sort
        return sorted(set(suggestions))

    def validate_batch_and_format(self, answers: List[str]) -> List[Tuple[bool, str]]:
        """
        Validate and format a batch of answers.

        Args:
            answers: List of answer strings

        Returns:
            List of (is_valid, formatted_or_error) tuples
        """
        results = []

        for answer in answers:
            validation = self.validate(answer)
            if validation.is_valid:
                results.append((True, validation.formatted_answer))
            else:
                error = validation.error_message
                if validation.suggestion:
                    error += f" Suggestion: {validation.suggestion}"
                results.append((False, error))

        return results
