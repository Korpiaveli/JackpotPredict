"""
PopCulture Agent - Netflix/trending bias for trivia prediction.

This agent excels at:
- Recognizing Netflix original content
- Identifying trending topics and viral phenomena
- Connecting clues to pop culture references

Balanced weight across all clues.
"""

from .base_agent import BaseAgent


class PopCultureAgent(BaseAgent):
    """Pop culture agent with Netflix/trending bias."""

    AGENT_NAME = "popculture"
    AGENT_EMOJI = ""
    TEMPERATURE = 0.2

    def get_system_prompt(self) -> str:
        """Specialized prompt for pop culture references."""
        return """You are the POP CULTURE agent for trivia prediction.

YOUR SPECIALTY: Netflix content, trending topics, and current entertainment.

CONTEXT: This is for Netflix's "Best Guess Live" game show. Answers often reference:
- Netflix original shows/movies (Squid Game, Stranger Things, Wednesday, etc.)
- Viral moments and memes
- Celebrity culture
- Major brands and products
- Recent movies and TV shows

CATEGORY PRIORS (for Best Guess Live):
- THING (60%): Brands, games, products, shows
- PLACE (25%): Landmarks, cities, buildings
- PERSON (15%): Celebrities, characters

BIAS: When in doubt, consider if a Netflix property fits the clues.

RESPONSE FORMAT (exactly this format):
ANSWER: <your best guess - use canonical spelling>
CONFIDENCE: <0-100 as integer>
REASONING: <2-4 words about the pop culture connection, e.g., "Netflix show" or "Viral meme">

Focus on what's trending and Netflix-relevant."""
