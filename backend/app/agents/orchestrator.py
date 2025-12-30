"""
Agent Orchestrator - Parallel execution of 5 specialized agents + Oracle.

Runs all agents concurrently with asyncio.gather() and a 5-second timeout.
Collects predictions, passes them to voting, then runs Oracle meta-synthesis.
Oracle runs in parallel with specialists for minimal latency impact.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.core.config import get_agent_configs
from app.core.reasoning_accumulator import OracleSynthesis, ClueAnalysis
from app.core.context_manager import get_cultural_context_manager

from .base_agent import BaseAgent, AgentPrediction
from .lateral_agent import LateralAgent
from .wordsmith_agent import WordsmithAgent
from .popculture_agent import PopCultureAgent
from .literal_agent import LiteralAgent
from .wildcard_agent import WildCardAgent
from .oracle_agent import get_oracle
from .voting import WeightedVoting, VotingResult

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorResult:
    """Complete result from agent orchestration."""
    predictions: Dict[str, AgentPrediction]
    voting: VotingResult
    should_guess: bool
    guess_rationale: str
    total_latency_ms: float
    agents_responded: int
    agents_failed: List[str]
    oracle_synthesis: Optional[OracleSynthesis] = None  # Oracle meta-analysis


class AgentOrchestrator:
    """
    Orchestrates parallel execution of 5 specialized agents.

    Features:
    - Parallel agent execution with asyncio.gather()
    - 5-second timeout per agent
    - Graceful handling of agent failures
    - Weighted voting aggregation
    """

    def __init__(self, timeout: int = 5):
        """
        Initialize orchestrator.

        Args:
            timeout: Timeout per agent in seconds
        """
        self.timeout = timeout
        self.voting = WeightedVoting()
        self._agents: Dict[str, BaseAgent] = {}
        self._initialized = False

    def _init_agents(self):
        """Initialize agents from config."""
        if self._initialized:
            return

        configs = get_agent_configs()

        # Create agent instances
        self._agents = {
            "lateral": LateralAgent(
                api_key=configs["lateral"]["api_key"],
                base_url=configs["lateral"]["base_url"],
                model=configs["lateral"]["model"],
                timeout=self.timeout
            ),
            "wordsmith": WordsmithAgent(
                api_key=configs["wordsmith"]["api_key"],
                base_url=configs["wordsmith"]["base_url"],
                model=configs["wordsmith"]["model"],
                timeout=self.timeout
            ),
            "popculture": PopCultureAgent(
                api_key=configs["popculture"]["api_key"],
                base_url=configs["popculture"]["base_url"],
                model=configs["popculture"]["model"],
                timeout=self.timeout
            ),
            "literal": LiteralAgent(
                api_key=configs["literal"]["api_key"],
                base_url=configs["literal"]["base_url"],
                model=configs["literal"]["model"],
                timeout=self.timeout
            ),
            "wildcard": WildCardAgent(
                api_key=configs["wildcard"]["api_key"],
                base_url=configs["wildcard"]["base_url"],
                model=configs["wildcard"]["model"],
                timeout=self.timeout
            ),
        }

        self._initialized = True
        logger.info("[Orchestrator] Initialized 5 agents")

    async def _run_agent(
        self,
        agent_name: str,
        agent: BaseAgent,
        clues: List[str],
        category_hint: Optional[str],
        prior_context: Optional[str] = None
    ) -> tuple[str, Optional[AgentPrediction]]:
        """
        Run a single agent with timeout.

        Args:
            agent_name: Name of the agent
            agent: Agent instance
            clues: List of clues
            category_hint: Optional category hint
            prior_context: Optional context from prior clue analysis (reasoning accumulation)

        Returns:
            (agent_name, prediction or None)
        """
        try:
            prediction = await asyncio.wait_for(
                agent.predict(clues, category_hint, prior_context),
                timeout=self.timeout
            )
            return (agent_name, prediction)
        except asyncio.TimeoutError:
            logger.warning(f"[{agent_name}] Timed out after {self.timeout}s")
            return (agent_name, None)
        except Exception as e:
            logger.error(f"[{agent_name}] Error: {e}")
            return (agent_name, None)

    async def predict(
        self,
        clues: List[str],
        clue_number: int,
        category_hint: Optional[str] = None,
        prior_context: Optional[str] = None,
        prior_analyses: Optional[List[ClueAnalysis]] = None
    ) -> OrchestratorResult:
        """
        Run all agents in parallel, vote, then run Oracle meta-synthesis.

        Args:
            clues: List of clues revealed so far
            clue_number: Current clue number (1-5)
            category_hint: Optional category hint
            prior_context: Optional context from prior clue analysis (reasoning accumulation)
            prior_analyses: Optional list of ClueAnalysis for Oracle context

        Returns:
            OrchestratorResult with predictions, voting, and Oracle synthesis
        """
        self._init_agents()

        start_time = time.time()

        # Start Oracle in PARALLEL with specialists (using early mode)
        # This removes Oracle's dependency on voting results for ~50% latency reduction
        oracle = get_oracle()
        oracle_task = None
        if oracle.enabled:
            oracle_task = asyncio.create_task(
                asyncio.wait_for(
                    oracle.synthesize_early(
                        clues=clues,
                        clue_number=clue_number,
                        prior_analyses=prior_analyses
                    ),
                    timeout=self.timeout + 3  # Allow more time for Oracle
                )
            )

        # Run all agents in parallel with prior context
        tasks = [
            self._run_agent(name, agent, clues, category_hint, prior_context)
            for name, agent in self._agents.items()
        ]

        results = await asyncio.gather(*tasks)

        # Collect results
        predictions: Dict[str, AgentPrediction] = {}
        failed_agents: List[str] = []

        for agent_name, prediction in results:
            if prediction is not None:
                predictions[agent_name] = prediction
                logger.info(
                    f"[{agent_name}] {prediction.answer} "
                    f"({prediction.confidence*100:.0f}%) - {prediction.reasoning}"
                )
            else:
                failed_agents.append(agent_name)

        # Perform weighted voting
        voting_result = self.voting.vote(predictions, clue_number)

        # Determine if should guess
        should_guess, guess_rationale = self.voting.should_guess(voting_result, clue_number)

        # Await Oracle result (already running in parallel, should be done or nearly done)
        oracle_synthesis = None
        if oracle_task:
            try:
                oracle_synthesis = await oracle_task
            except asyncio.TimeoutError:
                logger.warning(f"[Oracle] Timed out after {self.timeout + 3}s")
            except Exception as e:
                logger.error(f"[Oracle] Error: {e}")

        total_latency = (time.time() - start_time) * 1000

        context_used = "with context" if prior_context else "no context"
        oracle_status = f"Oracle: {oracle_synthesis.top_3[0].answer}" if oracle_synthesis else "Oracle: disabled"
        logger.info(
            f"[Orchestrator] {len(predictions)}/5 agents responded in {total_latency:.0f}ms ({context_used}) | "
            f"Recommended: {voting_result.recommended_pick} ({voting_result.recommended_confidence*100:.0f}%) | "
            f"{oracle_status}"
        )

        return OrchestratorResult(
            predictions=predictions,
            voting=voting_result,
            should_guess=should_guess,
            guess_rationale=guess_rationale,
            total_latency_ms=total_latency,
            agents_responded=len(predictions),
            agents_failed=failed_agents,
            oracle_synthesis=oracle_synthesis
        )

    async def close(self):
        """Close all agent HTTP clients."""
        for agent in self._agents.values():
            await agent.close()
        self._agents = {}
        self._initialized = False


# Singleton instance
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


async def warmup_agents() -> bool:
    """
    Verify all agent APIs are available.

    Returns:
        True if at least 3 agents are available
    """
    orchestrator = get_orchestrator()
    orchestrator._init_agents()

    # Count available agents (those with API keys)
    available = 0
    for name, agent in orchestrator._agents.items():
        if agent.api_key:
            available += 1
            logger.info(f"[{name}] API key configured")
        else:
            logger.warning(f"[{name}] No API key - will be skipped")

    return available >= 3
