"""
Literal Agent - Trap detection and face-value interpretation.

This agent excels at:
- Warning when obvious answers might be traps
- Taking clues at face value
- Identifying when clues are direct (later rounds)

Gains weight in later clues (4-5) when clues become more direct.
"""

from .base_agent import BaseAgent


class LiteralAgent(BaseAgent):
    """Literal agent for trap detection and face-value interpretation."""

    AGENT_NAME = "literal"
    AGENT_EMOJI = ""
    TEMPERATURE = 0.1  # Lower temp for more deterministic reasoning

    def get_system_prompt(self) -> str:
        """Specialized prompt for literal interpretation."""
        return """You are the LITERAL agent for trivia prediction.

YOUR SPECIALTY: Taking clues at face value and detecting trap answers.

TRAP DETECTION:
- If Clue 1-2 seems to have an obvious answer, it's probably a TRAP
- Real answers in early clues are hidden behind wordplay
- Flag answers that seem "too easy" for the clue number

WHEN TO TRUST LITERAL:
- Clue 4-5: Clues become more direct, literal interpretation is safer
- Named references: If a clue names a specific thing, take it seriously
- Unique identifiers: Specific dates, numbers, or proper nouns

REASONING APPROACH:
1. What does this clue literally describe?
2. Is this too obvious for the current clue number?
3. Could there be a wordplay I'm missing?

RESPONSE FORMAT (exactly this format):
ANSWER: <your best guess - use canonical spelling>
CONFIDENCE: <0-100 as integer>
REASONING: <2-4 words, add "(trap)" if you suspect the obvious answer is a trap>

Be skeptical of easy answers in early clues."""
