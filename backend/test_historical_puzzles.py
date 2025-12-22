#!/usr/bin/env python3
"""
Test suite for historical JackpotPredict puzzles.

Tests the system against known trivia puzzles to validate prediction accuracy.
"""

import requests
import json
from typing import List, Dict
from dataclasses import dataclass

API_URL = "http://localhost:8000/api"


@dataclass
class PuzzleTest:
    """Test case for a historical puzzle."""
    name: str
    clues: List[str]
    answer: str
    target_clue: int  # Clue number by which answer should appear in Top 3
    min_confidence: float  # Minimum confidence expected at target clue


# Historical puzzles from PRD and game footage
PUZZLES = [
    PuzzleTest(
        name="Monopoly",
        clues=[
            "Savors many flavors",
            "Round and round",
            "A hostile takeover",
            "Trespassing will cost you",
            "Jail time can be dicey"
        ],
        answer="Monopoly",
        target_clue=3,
        min_confidence=75.0
    ),
    PuzzleTest(
        name="Paris Hilton",
        clues=[
            "Back to the basics",
            "Loud with the crowd",
            "A sensation and a destination",
            "Her family is extremely hospitable",
            "Named after a romantic city? That's hot."
        ],
        answer="Paris Hilton",
        target_clue=4,
        min_confidence=75.0
    ),
    PuzzleTest(
        name="Mt. Rushmore",
        clues=[
            "Natural but not natural",
            "Presidential faces",
            "South Dakota landmark",
            "Carved in granite",
            "Four founding fathers"
        ],
        answer="Mt. Rushmore",
        target_clue=2,
        min_confidence=75.0
    ),
    PuzzleTest(
        name="Eiffel Tower",
        clues=[
            "Named after Eiffel",
            "Iron lady of Paris",
            "Built for an exposition",
            "World's most visited paid monument",
            "1000 feet of French engineering"
        ],
        answer="Eiffel Tower",
        target_clue=1,  # Should get it immediately on first clue!
        min_confidence=75.0
    ),
]


def run_puzzle_test(puzzle: PuzzleTest) -> Dict:
    """
    Run a single puzzle test through the API.

    Args:
        puzzle: PuzzleTest configuration

    Returns:
        Dictionary with test results
    """
    print(f"\n{'='*70}")
    print(f"TESTING: {puzzle.name}")
    print(f"{'='*70}")

    session_id = None
    results = {
        "puzzle_name": puzzle.name,
        "expected_answer": puzzle.answer,
        "target_clue": puzzle.target_clue,
        "min_confidence": puzzle.min_confidence,
        "clue_results": [],
        "passed": False,
        "found_at_clue": None,
        "final_rank": None,
        "final_confidence": None
    }

    for i, clue in enumerate(puzzle.clues, 1):
        print(f"\n{'-'*70}")
        print(f"CLUE {i}: {clue}")
        print(f"{'-'*70}")

        # Submit clue
        payload = {"clue_text": clue}
        if session_id:
            payload["session_id"] = session_id
            print(f"[DEBUG] Using session_id: {session_id[:8]}...")
        else:
            print(f"[DEBUG] No session_id (first clue)")

        try:
            response = requests.post(f"{API_URL}/predict", json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            session_id = data["session_id"]

            # Display predictions
            print(f"\nTop 3 Predictions:")
            for pred in data["predictions"]:
                marker = " <- ANSWER!" if pred["answer"] == puzzle.answer else ""
                # API returns confidence as fraction (0-1), convert to percentage for display
                conf_pct = pred['confidence'] * 100
                print(f"  {pred['rank']}. {pred['answer']} - {conf_pct:.1f}%{marker}")
                print(f"     {pred['reasoning'][:80]}")

            # Check if answer is in top 3
            answers = [p["answer"] for p in data["predictions"]]
            found_in_top3 = puzzle.answer in answers

            clue_result = {
                "clue_number": i,
                "clue_text": clue,
                "top_3": answers,
                "answer_found": found_in_top3,
                "answer_rank": answers.index(puzzle.answer) + 1 if found_in_top3 else None,
                "answer_confidence": data["predictions"][answers.index(puzzle.answer)]["confidence"] * 100 if found_in_top3 else 0.0
            }
            results["clue_results"].append(clue_result)

            if found_in_top3:
                rank = answers.index(puzzle.answer) + 1
                conf = data["predictions"][rank-1]["confidence"] * 100  # Convert to percentage
                print(f"\n  [FOUND] {puzzle.answer} is #{rank} with {conf:.1f}% confidence")

                if results["found_at_clue"] is None:
                    results["found_at_clue"] = i

                results["final_rank"] = rank
                results["final_confidence"] = conf

                # Check if we've met success criteria
                if i >= puzzle.target_clue and rank <= 3 and conf >= puzzle.min_confidence:
                    print(f"\n  [SUCCESS] Answer found by Clue {puzzle.target_clue} with {conf:.1f}% confidence")
                    results["passed"] = True
            else:
                print(f"\n  [NOT FOUND] {puzzle.answer} not in Top 3")

        except Exception as e:
            print(f"\n  [ERROR] {str(e)}")
            clue_result = {
                "clue_number": i,
                "clue_text": clue,
                "error": str(e)
            }
            results["clue_results"].append(clue_result)

    return results


def run_all_tests():
    """Run all historical puzzle tests and generate report."""
    print("\n" + "="*70)
    print("JACKPOTPREDICT - HISTORICAL PUZZLE TEST SUITE")
    print("="*70)

    # Check API health
    try:
        health = requests.get(f"{API_URL}/health", timeout=5)
        health.raise_for_status()
        health_data = health.json()
        print(f"\n[OK] API Status: {health_data['status']}")
        print(f"[OK] Entities Loaded: {health_data['entity_count']}")
    except Exception as e:
        print(f"\n[FAIL] API Health Check Failed: {e}")
        print("Make sure the server is running: python -m uvicorn app.server:app --port 8000")
        return

    # Run all puzzle tests
    all_results = []
    for puzzle in PUZZLES:
        result = run_puzzle_test(puzzle)
        all_results.append(result)

    # Generate summary report
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for r in all_results if r["passed"])
    total = len(all_results)

    print(f"\nOverall: {passed}/{total} puzzles passed ({passed/total*100:.0f}%)")
    print("\nDetailed Results:")
    print(f"{'Puzzle':<20} {'Target Clue':<12} {'Found At':<10} {'Final Rank':<12} {'Confidence':<12} {'Status':<10}")
    print("-" * 70)

    for result in all_results:
        found_at = result["found_at_clue"] if result["found_at_clue"] else "N/A"
        final_rank = result["final_rank"] if result["final_rank"] else "N/A"
        final_conf = f"{result['final_confidence']:.1f}%" if result["final_confidence"] else "N/A"
        status = "[PASS]" if result["passed"] else "[FAIL]"

        print(f"{result['puzzle_name']:<20} {result['target_clue']:<12} {found_at:<10} {final_rank:<12} {final_conf:<12} {status:<10}")

    # Detailed failure analysis
    failures = [r for r in all_results if not r["passed"]]
    if failures:
        print("\n" + "="*70)
        print("FAILURE ANALYSIS")
        print("="*70)

        for result in failures:
            print(f"\n{result['puzzle_name']}:")
            if result["found_at_clue"]:
                print(f"  - Answer found at Clue {result['found_at_clue']} (target: Clue {result['target_clue']})")
                print(f"  - Final rank: #{result['final_rank']} (need: Top 3)")
                print(f"  - Final confidence: {result['final_confidence']:.1f}% (need: >{result['min_confidence']}%)")
            else:
                print(f"  - Answer NEVER appeared in Top 3")
                print(f"  - Check if '{result['expected_answer']}' exists in database")

    # Save detailed results
    with open("test_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n[OK] Detailed results saved to test_results.json")

    print("\n" + "="*70)
    print("TEST SUITE COMPLETE")
    print("="*70)

    return all_results


if __name__ == "__main__":
    run_all_tests()
