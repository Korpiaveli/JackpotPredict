#!/usr/bin/env python3
"""Quick test - runs first 10 puzzles to validate accuracy."""

import requests
import json
import time
from typing import List, Dict
from dataclasses import dataclass

API_URL = "http://localhost:8000/api"
API_DELAY = 0.5

@dataclass
class PuzzleTest:
    name: str
    clues: List[str]
    answer: str
    target_clue: int
    min_confidence: float

# First 10 puzzles for quick test
PUZZLES = [
    PuzzleTest(
        name="Monopoly",
        clues=["Savors many flavors", "Round and round", "A hostile takeover", "Trespassing will cost you", "Jail time can be dicey"],
        answer="Monopoly", target_clue=3, min_confidence=75.0
    ),
    PuzzleTest(
        name="Paris Hilton",
        clues=["Back to the basics", "Loud with the crowd", "A sensation and a destination", "Her family is extremely hospitable", "Named after a romantic city? That's hot."],
        answer="Paris Hilton", target_clue=4, min_confidence=75.0
    ),
    PuzzleTest(
        name="Mt. Rushmore",
        clues=["Natural but not natural", "Presidential faces", "South Dakota landmark", "Carved in granite", "Four founding fathers"],
        answer="Mt. Rushmore", target_clue=2, min_confidence=75.0
    ),
    PuzzleTest(
        name="Eiffel Tower",
        clues=["Named after Eiffel", "Iron lady of Paris", "Built for an exposition", "World's most visited paid monument", "1000 feet of French engineering"],
        answer="Eiffel Tower", target_clue=1, min_confidence=75.0
    ),
    PuzzleTest(
        name="Star Wars",
        clues=["A long time ago", "The force is strong", "Dark side vs light", "Darth Vader's saga", "May the force be with you"],
        answer="Star Wars", target_clue=3, min_confidence=60.0
    ),
    PuzzleTest(
        name="Titanic",
        clues=["Unsinkable they said", "An icy ending", "Jack and Rose", "Heart of the ocean", "King of the world"],
        answer="Titanic", target_clue=3, min_confidence=60.0
    ),
    PuzzleTest(
        name="Coca-Cola",
        clues=["The real thing", "Secret formula", "Santa's favorite drink", "Atlanta original", "Open happiness"],
        answer="Coca-Cola", target_clue=2, min_confidence=70.0
    ),
    PuzzleTest(
        name="Nike",
        clues=["Just do it", "Swoosh symbol", "Air Jordan maker", "Greek goddess of victory", "Phil Knight's creation"],
        answer="Nike", target_clue=2, min_confidence=70.0
    ),
    PuzzleTest(
        name="McDonald's",
        clues=["Golden arches", "I'm lovin' it", "Happy Meals", "Big Mac birthplace", "Fast food empire"],
        answer="McDonald's", target_clue=2, min_confidence=70.0
    ),
    PuzzleTest(
        name="Amazon",
        clues=["A river runs through it", "Rainforest and retail", "Prime delivery", "Jeff's everything store", "Alexa's parent"],
        answer="Amazon", target_clue=3, min_confidence=60.0
    ),
]

def run_puzzle(puzzle: PuzzleTest) -> Dict:
    """Run a single puzzle test."""
    print(f"\n{'='*60}")
    print(f"TESTING: {puzzle.name}")
    print(f"{'='*60}")

    session_id = None
    found_at = None
    final_rank = None
    final_conf = None

    for i, clue in enumerate(puzzle.clues, 1):
        print(f"\nClue {i}: {clue}")

        payload = {"clue_text": clue}
        if session_id:
            payload["session_id"] = session_id

        try:
            time.sleep(API_DELAY)
            resp = requests.post(f"{API_URL}/predict", json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            session_id = data["session_id"]

            # Check if answer in top 3
            answers = [p["answer"] for p in data["predictions"]]
            if puzzle.answer in answers:
                rank = answers.index(puzzle.answer) + 1
                conf = data["predictions"][rank-1]["confidence"] * 100
                print(f"  -> {puzzle.answer} is #{rank} ({conf:.0f}%)")

                if found_at is None:
                    found_at = i
                final_rank = rank
                final_conf = conf
            else:
                print(f"  -> {puzzle.answer} NOT in top 3. Got: {answers[:2]}")

        except Exception as e:
            print(f"  -> ERROR: {e}")

    # Determine pass/fail
    passed = found_at is not None and found_at <= puzzle.target_clue and final_conf and final_conf >= puzzle.min_confidence

    return {
        "name": puzzle.name,
        "passed": passed,
        "found_at": found_at,
        "target": puzzle.target_clue,
        "final_rank": final_rank,
        "final_conf": final_conf
    }

def main():
    print("\n" + "="*60)
    print("JACKPOTPREDICT - QUICK TEST (10 puzzles)")
    print("="*60)

    # Health check
    try:
        health = requests.get(f"{API_URL}/health", timeout=5).json()
        print(f"\n[OK] API: {health['status']}, Entities: {health['entity_count']}")
    except Exception as e:
        print(f"\n[FAIL] API not available: {e}")
        return

    results = []
    for puzzle in PUZZLES:
        result = run_puzzle(puzzle)
        results.append(result)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed = sum(1 for r in results if r["passed"])
    print(f"\nPassed: {passed}/{len(results)} ({passed/len(results)*100:.0f}%)")

    print(f"\n{'Puzzle':<15} {'Found@':<8} {'Target':<8} {'Rank':<6} {'Conf':<8} {'Status'}")
    print("-"*55)
    for r in results:
        found = r["found_at"] or "-"
        rank = r["final_rank"] or "-"
        conf = f"{r['final_conf']:.0f}%" if r["final_conf"] else "-"
        status = "PASS" if r["passed"] else "FAIL"
        print(f"{r['name']:<15} {found:<8} {r['target']:<8} {rank:<6} {conf:<8} {status}")

if __name__ == "__main__":
    main()
