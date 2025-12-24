"""
JackpotPredict Agents - Mixture of Agents (MoA) architecture.

5 specialized agents for trivia prediction:
- Lateral: Multi-hop associative reasoning (GPT-4o-mini)
- Wordsmith: Puns, wordplay, homophones (GPT-4o-mini)
- PopCulture: Netflix/trending bias (Gemini Flash)
- Literal: Trap detection, face-value (Llama 3.3 70B via Groq)
- WildCard: Paradox, creative leaps (GPT-4o-mini, temp=0.9)
"""

from .base_agent import BaseAgent, AgentPrediction
from .lateral_agent import LateralAgent
from .wordsmith_agent import WordsmithAgent
from .popculture_agent import PopCultureAgent
from .literal_agent import LiteralAgent
from .wildcard_agent import WildCardAgent
from .orchestrator import AgentOrchestrator
from .voting import WeightedVoting

__all__ = [
    "BaseAgent",
    "AgentPrediction",
    "LateralAgent",
    "WordsmithAgent",
    "PopCultureAgent",
    "LiteralAgent",
    "WildCardAgent",
    "AgentOrchestrator",
    "WeightedVoting",
]
