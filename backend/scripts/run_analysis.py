"""
JackpotPredict Analysis Script

Exhaustive analysis of prediction accuracy across all historical puzzles.
Runs puzzles through the prediction API, tracks accuracy per agent and Oracle.

Usage:
    python scripts/run_analysis.py
    python scripts/run_analysis.py --limit 5  # Test with 5 puzzles
    python scripts/run_analysis.py --puzzle "Monopoly"  # Single puzzle
    python scripts/run_analysis.py --output results.json
"""

import asyncio
import json
import argparse
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import enhanced answer matching
from app.core.answer_matcher import answers_match as enhanced_answers_match


@dataclass
class ClueResult:
    """Result of a single clue submission."""
    clue_number: int
    clue_text: str
    oracle_top_3: List[Dict[str, Any]]
    oracle_correct: bool  # Is correct answer #1?
    oracle_in_top3: bool  # Is correct answer in top 3?
    oracle_rank: Optional[int]  # 1, 2, 3 or None
    oracle_confidence: Optional[int]  # Confidence of correct answer
    agents: Dict[str, Dict[str, Any]]
    agent_correct: Dict[str, bool]
    agreement_strength: str
    elapsed_time: float
    error: Optional[str] = None


@dataclass
class PuzzleResult:
    """Complete analysis result for a puzzle."""
    answer: str
    category: str
    expected_solve_clue: Optional[int]
    clue_results: List[ClueResult] = field(default_factory=list)

    # Oracle metrics
    oracle_correct_at: Optional[int] = None
    oracle_in_top3_at: Optional[int] = None
    oracle_final_confidence: Optional[int] = None

    # Per-agent metrics
    agents_correct_at: Dict[str, Optional[int]] = field(default_factory=dict)

    # Confidence evolution
    confidence_evolution: List[int] = field(default_factory=list)

    # Timing
    total_time: float = 0.0
    avg_response_time: float = 0.0


@dataclass
class AnalysisSummary:
    """Aggregate statistics across all puzzles."""
    total_puzzles: int
    oracle_accuracy_by_clue: Dict[str, float]
    oracle_in_top3_by_clue: Dict[str, float]
    agent_accuracy_by_clue: Dict[str, Dict[str, float]]
    confidence_calibration: Dict[str, float]
    avg_response_time: float
    category_accuracy: Dict[str, float]


class PredictionAnalyzer:
    """Runs predictions and collects analysis data."""

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()

    async def reset_session(self) -> str:
        """Reset and get a fresh session ID."""
        try:
            response = await self.client.post(
                f"{self.api_url}/api/reset",
                json={"session_id": None}  # Create new session
            )
            response.raise_for_status()
            data = response.json()
            return data.get("session_id", "")
        except Exception as e:
            print(f"  [ERROR] Reset failed: {e}")
            return ""

    async def analyze_puzzle(self, puzzle: dict, verbose: bool = True) -> PuzzleResult:
        """Run a single puzzle through the prediction system clue by clue."""
        answer = puzzle["answer"]
        category = puzzle.get("category", "unknown")
        expected_clue = puzzle.get("clue_solved_at")
        clues = puzzle["clues"]

        result = PuzzleResult(
            answer=answer,
            category=category,
            expected_solve_clue=expected_clue
        )

        if verbose:
            print(f"\n{'='*60}")
            print(f"  PUZZLE: {answer} ({category})")
            print(f"{'='*60}")

        # Reset for fresh session
        session_id = await self.reset_session()

        total_time = 0.0

        # Process clues sequentially
        for i, clue in enumerate(clues, 1):
            if verbose:
                print(f"\n  Clue {i}: \"{clue[:50]}{'...' if len(clue) > 50 else ''}\"")

            clue_result = await self._submit_clue(
                clue=clue,
                clue_number=i,
                session_id=session_id,
                correct_answer=answer,
                verbose=verbose
            )
            result.clue_results.append(clue_result)
            total_time += clue_result.elapsed_time

            # Track when Oracle first got it correct (#1)
            if clue_result.oracle_correct and result.oracle_correct_at is None:
                result.oracle_correct_at = i
                if verbose:
                    print(f"    ** Oracle CORRECT at clue {i}!")

            # Track when answer first appeared in top 3
            if clue_result.oracle_in_top3 and result.oracle_in_top3_at is None:
                result.oracle_in_top3_at = i
                if verbose:
                    print(f"    -> Answer in top 3 at clue {i}")

            # Track per-agent accuracy
            for agent, correct in clue_result.agent_correct.items():
                if correct and agent not in result.agents_correct_at:
                    result.agents_correct_at[agent] = i
                    if verbose:
                        print(f"    -> {agent} correct at clue {i}")

            # Record confidence evolution
            if clue_result.oracle_top_3:
                top_conf = clue_result.oracle_top_3[0].get("confidence", 0)
                result.confidence_evolution.append(top_conf)

        # Final metrics
        result.total_time = total_time
        result.avg_response_time = total_time / len(clues) if clues else 0

        if result.clue_results and result.clue_results[-1].oracle_top_3:
            # Get confidence of correct answer in final clue
            for guess in result.clue_results[-1].oracle_top_3:
                if self._answers_match(guess["answer"], answer):
                    result.oracle_final_confidence = guess["confidence"]
                    break

        if verbose:
            print(f"\n  RESULT: Oracle correct at clue {result.oracle_correct_at or 'NEVER'}")
            print(f"  Total time: {total_time:.1f}s")

        return result

    async def _submit_clue(
        self,
        clue: str,
        clue_number: int,
        session_id: str,
        correct_answer: str,
        verbose: bool = True
    ) -> ClueResult:
        """Submit a single clue and parse the response."""
        try:
            response = await self.client.post(
                f"{self.api_url}/api/predict",
                json={"clue_text": clue, "session_id": session_id}
            )
            response.raise_for_status()
            data = response.json()

            # Extract Oracle predictions
            oracle = data.get("oracle") or {}
            top_3 = oracle.get("top_3", [])

            # Determine Oracle correctness
            oracle_rank = None
            oracle_correct = False
            oracle_in_top3 = False
            oracle_confidence = None

            for i, guess in enumerate(top_3, 1):
                if self._answers_match(guess.get("answer", ""), correct_answer):
                    oracle_rank = i
                    oracle_in_top3 = True
                    oracle_correct = (i == 1)
                    oracle_confidence = guess.get("confidence")
                    break

            # Extract agent predictions and correctness
            agents = data.get("agents", {})
            agent_correct = {}
            for agent_name, pred in agents.items():
                if pred:
                    agent_correct[agent_name] = self._answers_match(
                        pred.get("answer", ""), correct_answer
                    )

            elapsed = data.get("elapsed_time", 0)

            if verbose:
                top_pick = top_3[0]["answer"] if top_3 else "N/A"
                top_conf = top_3[0]["confidence"] if top_3 else 0
                status = "[OK]" if oracle_correct else ("[~]" if oracle_in_top3 else "[X]")
                print(f"    {status} Oracle: {top_pick} ({top_conf}%) [{elapsed:.1f}s]")

            return ClueResult(
                clue_number=clue_number,
                clue_text=clue,
                oracle_top_3=top_3,
                oracle_correct=oracle_correct,
                oracle_in_top3=oracle_in_top3,
                oracle_rank=oracle_rank,
                oracle_confidence=oracle_confidence,
                agents={k: v for k, v in agents.items() if v},
                agent_correct=agent_correct,
                agreement_strength=data.get("agreement_strength", "none"),
                elapsed_time=elapsed
            )
        except Exception as e:
            if verbose:
                print(f"    [ERROR] {e}")
            return ClueResult(
                clue_number=clue_number,
                clue_text=clue,
                oracle_top_3=[],
                oracle_correct=False,
                oracle_in_top3=False,
                oracle_rank=None,
                oracle_confidence=None,
                agents={},
                agent_correct={},
                agreement_strength="none",
                elapsed_time=0,
                error=str(e)
            )

    def _answers_match(self, pred: str, correct: str) -> bool:
        """
        Enhanced fuzzy answer matching using answer_matcher module.

        Handles:
        - First-name expansion (Oprah -> Oprah Winfrey)
        - Abbreviations (Mt. -> Mount, St. -> Saint)
        - Common prefixes (The, A, An)
        - Fuzzy string matching for similar answers
        """
        if not pred or not correct:
            return False

        # Use enhanced matching from answer_matcher module
        return enhanced_answers_match(pred, correct, threshold=0.85)


def compute_summary(results: List[PuzzleResult]) -> AnalysisSummary:
    """Compute aggregate statistics from puzzle results."""

    # Initialize counters
    oracle_acc = {str(i): {"correct": 0, "total": 0} for i in range(1, 6)}
    oracle_top3 = {str(i): {"in_top3": 0, "total": 0} for i in range(1, 6)}

    agents = ["lateral", "wordsmith", "popculture", "literal", "wildcard"]
    agent_acc = {a: {str(i): {"correct": 0, "total": 0} for i in range(1, 6)} for a in agents}

    confidence_buckets = {"high": [], "medium": [], "low": []}
    category_results = {"thing": [], "person": [], "place": []}
    all_times = []

    for puzzle in results:
        # Track category accuracy
        cat = puzzle.category.lower()
        if cat in category_results:
            category_results[cat].append(puzzle.oracle_correct_at is not None)

        for clue_res in puzzle.clue_results:
            c = str(clue_res.clue_number)

            # Oracle accuracy (#1 correct)
            oracle_acc[c]["total"] += 1
            if clue_res.oracle_correct:
                oracle_acc[c]["correct"] += 1

            # Oracle in top 3
            oracle_top3[c]["total"] += 1
            if clue_res.oracle_in_top3:
                oracle_top3[c]["in_top3"] += 1

            # Agent accuracy
            for agent, correct in clue_res.agent_correct.items():
                if agent in agent_acc:
                    agent_acc[agent][c]["total"] += 1
                    if correct:
                        agent_acc[agent][c]["correct"] += 1

            # Confidence calibration
            if clue_res.oracle_top_3:
                conf = clue_res.oracle_top_3[0].get("confidence", 50)
                bucket = "high" if conf >= 75 else "medium" if conf >= 50 else "low"
                confidence_buckets[bucket].append(clue_res.oracle_correct)

            # Response time
            if clue_res.elapsed_time > 0:
                all_times.append(clue_res.elapsed_time)

    # Calculate percentages
    oracle_accuracy_by_clue = {
        c: d["correct"] / d["total"] if d["total"] > 0 else 0
        for c, d in oracle_acc.items()
    }

    oracle_in_top3_by_clue = {
        c: d["in_top3"] / d["total"] if d["total"] > 0 else 0
        for c, d in oracle_top3.items()
    }

    agent_accuracy_by_clue = {
        agent: {
            clue: data[clue]["correct"] / data[clue]["total"]
            if data[clue]["total"] > 0 else 0
            for clue in ["1", "2", "3", "4", "5"]
        }
        for agent, data in agent_acc.items()
    }

    confidence_calibration = {
        bucket: sum(results) / len(results) if results else 0
        for bucket, results in confidence_buckets.items()
    }

    category_accuracy = {
        cat: sum(results) / len(results) if results else 0
        for cat, results in category_results.items()
    }

    avg_response_time = sum(all_times) / len(all_times) if all_times else 0

    return AnalysisSummary(
        total_puzzles=len(results),
        oracle_accuracy_by_clue=oracle_accuracy_by_clue,
        oracle_in_top3_by_clue=oracle_in_top3_by_clue,
        agent_accuracy_by_clue=agent_accuracy_by_clue,
        confidence_calibration=confidence_calibration,
        avg_response_time=avg_response_time,
        category_accuracy=category_accuracy
    )


def load_puzzles(data_dir: Path) -> List[dict]:
    """Load puzzles from history.json."""
    history_file = data_dir / "history.json"

    if not history_file.exists():
        print(f"[ERROR] history.json not found at {history_file}")
        return []

    with open(history_file, "r", encoding="utf-8") as f:
        puzzles = json.load(f)

    # Filter puzzles with valid clues
    valid = [p for p in puzzles if p.get("clues") and len(p["clues"]) >= 5]
    print(f"Loaded {len(valid)} puzzles from history.json")

    return valid


def print_summary(summary: AnalysisSummary):
    """Print summary to console."""
    print("\n" + "=" * 70)
    print("  ANALYSIS SUMMARY")
    print("=" * 70)

    print(f"\n  Total Puzzles: {summary.total_puzzles}")
    print(f"  Avg Response Time: {summary.avg_response_time:.2f}s")

    print("\n  ORACLE ACCURACY (% correct as #1 pick):")
    for clue in ["1", "2", "3", "4", "5"]:
        pct = summary.oracle_accuracy_by_clue.get(clue, 0) * 100
        bar = "#" * int(pct / 5)
        print(f"    Clue {clue}: {pct:5.1f}% {bar}")

    print("\n  ORACLE IN TOP 3:")
    for clue in ["1", "2", "3", "4", "5"]:
        pct = summary.oracle_in_top3_by_clue.get(clue, 0) * 100
        bar = "#" * int(pct / 5)
        print(f"    Clue {clue}: {pct:5.1f}% {bar}")

    print("\n  AGENT ACCURACY (% correct at each clue):")
    for agent in ["lateral", "wordsmith", "popculture", "literal", "wildcard"]:
        agent_data = summary.agent_accuracy_by_clue.get(agent, {})
        clue5 = agent_data.get("5", 0) * 100
        print(f"    {agent:12s}: Clue5={clue5:5.1f}%")

    print("\n  CONFIDENCE CALIBRATION:")
    for bucket in ["high", "medium", "low"]:
        pct = summary.confidence_calibration.get(bucket, 0) * 100
        print(f"    {bucket:8s} (75%+/50-75%/<50%): {pct:5.1f}% actually correct")

    print("\n  CATEGORY ACCURACY:")
    for cat in ["thing", "person", "place"]:
        pct = summary.category_accuracy.get(cat, 0) * 100
        print(f"    {cat:8s}: {pct:5.1f}%")


async def main():
    parser = argparse.ArgumentParser(description="JackpotPredict Analysis")
    parser.add_argument("--limit", type=int, help="Limit number of puzzles")
    parser.add_argument("--puzzle", type=str, help="Run single puzzle by answer")
    parser.add_argument("--output", type=str, default="analysis_results.json", help="Output file")
    parser.add_argument("--api", type=str, default="http://localhost:8000", help="API URL")
    parser.add_argument("--quiet", action="store_true", help="Less verbose output")
    args = parser.parse_args()

    # Load puzzles
    data_dir = Path(__file__).parent.parent / "app" / "data"
    puzzles = load_puzzles(data_dir)

    if not puzzles:
        print("No puzzles found!")
        return

    # Filter by puzzle name if specified
    if args.puzzle:
        puzzles = [p for p in puzzles if args.puzzle.lower() in p["answer"].lower()]
        if not puzzles:
            print(f"No puzzle found matching '{args.puzzle}'")
            return

    # Limit puzzles
    if args.limit:
        puzzles = puzzles[:args.limit]

    print(f"\nRunning analysis on {len(puzzles)} puzzles...")
    print(f"API: {args.api}")

    # Run analysis
    results: List[PuzzleResult] = []

    async with PredictionAnalyzer(args.api) as analyzer:
        for i, puzzle in enumerate(puzzles, 1):
            print(f"\n[{i}/{len(puzzles)}] ", end="")
            try:
                result = await analyzer.analyze_puzzle(puzzle, verbose=not args.quiet)
                results.append(result)
            except Exception as e:
                print(f"[ERROR] Failed to analyze {puzzle['answer']}: {e}")

    # Compute summary
    summary = compute_summary(results)
    print_summary(summary)

    # Save results
    output_path = Path(__file__).parent.parent / args.output
    output_data = {
        "metadata": {
            "run_date": datetime.now().isoformat(),
            "total_puzzles": len(results),
            "api_url": args.api
        },
        "summary": asdict(summary),
        "per_puzzle": [
            {
                "answer": r.answer,
                "category": r.category,
                "expected_solve_clue": r.expected_solve_clue,
                "oracle_correct_at": r.oracle_correct_at,
                "oracle_in_top3_at": r.oracle_in_top3_at,
                "oracle_final_confidence": r.oracle_final_confidence,
                "agents_correct_at": r.agents_correct_at,
                "confidence_evolution": r.confidence_evolution,
                "avg_response_time": r.avg_response_time
            }
            for r in results
        ]
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n  Results saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
