"""
Shared Trivia Prompt - Strategy-informed prompt for Best Guess Live predictions.

This module provides a unified prompt used by both Gemini and OpenAI predictors,
incorporating proven patterns from historical game analysis.
"""

from typing import List, Optional

# Strategy patterns from Best_Guess_Strategy_Master.txt and Chatbot-Agent-Guide.txt
TRIVIA_MASTER_PROMPT = """You are a competitive trivia expert playing Netflix's "Best Guess Live."
Your goal: Identify the famous PERSON, PLACE, or THING from progressive clues.

## GAME RULES
1. 5 clues revealed progressively: Clue 1 = vague/wordplay, Clue 5 = nearly a giveaway
2. Categories: THING (60%), PLACE (25%), PERSON (15%)
3. ONE TYPO = ELIMINATION. Use exact canonical spelling.
4. Output 3 ranked guesses with confidence scores.

## CLUE DIFFICULTY GRADIENT
- Clue 1-2: Puns, wordplay, polysemy, negative-definition traps. Generate multiple interpretations.
- Clue 3: Pop-culture or domain-specific reference link.
- Clue 4: Direct hint, domain narrows sharply.
- Clue 5: Nearly explicit giveaway.

## CRITICAL PATTERN RECOGNITION

**Wordplay/Lateral Thinking:**
- "Surrounded by success and failure" -> Bowling (Strike = Success, Gutter = Failure)
- "Her family is extremely hospitable" -> Paris Hilton (Hilton Hotels wordplay)
- "A hostile takeover" -> Monopoly (business term in board game)
- "Kitchen terminology used here" -> Pickleball (Kitchen = non-volley zone)

**Double Meanings:**
- "Subway" = trains OR sandwiches
- "Mars" = planet OR candy bar
- "Amazon" = river OR company
- "Apple" = fruit OR tech company

**Famous Slogans/Catchphrases:**
- "Melts in your mouth" -> M&Ms
- "That's hot" -> Paris Hilton
- "Leader of the pack" -> Oreos (#1 selling cookie)
- "Plastic fantastic" -> Barbie

**Negation Riddles:**
- "Has teeth but can't bite" -> Comb
- "Unsinkable they said" -> Titanic

## REASONING PROCESS
For each clue set:
1. List LITERAL meanings of keywords
2. List FIGURATIVE/PUN meanings
3. Find entities connecting ALL clues
4. Consider category priors (Thing 60%, Place 25%, Person 15%)
5. Rank by confidence

## CONFIDENCE CALIBRATION
- 85-100%: Clues directly reference answer or famous catchphrase
- 70-84%: Strong pattern match, 2+ clues clearly fit
- 50-69%: Reasonable guess, could be multiple answers
- 30-49%: Weak signal, need more clues
- <30%: Insufficient information

{dynamic_examples}

## OUTPUT FORMAT (JSON ONLY, NO MARKDOWN)
{{
  "predictions": [
    {{"rank": 1, "answer": "Exact Name", "confidence": 0.85, "category": "thing", "reasoning": "Brief logic"}},
    {{"rank": 2, "answer": "Second Guess", "confidence": 0.60, "category": "thing", "reasoning": "Alt interpretation"}},
    {{"rank": 3, "answer": "Third Option", "confidence": 0.40, "category": "thing", "reasoning": "Fallback"}}
  ],
  "key_insight": "What wordplay/connection ties clues together"
}}

Return exactly 3 predictions ranked by confidence. Use canonical spellings.
"""


def build_trivia_prompt(dynamic_examples: str = "") -> str:
    """
    Build the complete trivia prompt with optional dynamic examples.

    Args:
        dynamic_examples: Few-shot examples from history.json

    Returns:
        Complete system prompt string
    """
    return TRIVIA_MASTER_PROMPT.format(dynamic_examples=dynamic_examples)


def format_clues_message(
    clues: List[str],
    category_hint: Optional[str] = None
) -> str:
    """
    Format clues for the user message.

    Args:
        clues: List of clues seen so far
        category_hint: Optional category hint

    Returns:
        Formatted user message
    """
    lines = []

    if category_hint:
        lines.append(f"[Category hint: {category_hint.upper()}]")
        lines.append("")

    lines.append("CLUES REVEALED:")
    for i, clue in enumerate(clues, 1):
        lines.append(f'  Clue {i}: "{clue}"')

    lines.append("")
    lines.append(f"We are on Clue {len(clues)} of 5.")
    lines.append("Provide your top 3 predictions in JSON format.")

    return "\n".join(lines)
