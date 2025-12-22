#!/usr/bin/env python3
"""Test the Monopoly puzzle end-to-end via API."""

import requests
import json

API_URL = "http://localhost:8000/api"

def test_monopoly_puzzle():
    """Test the Monopoly puzzle through the API."""

    clues = [
        "Savors many flavors",
        "Round and round",
        "A hostile takeover",
        "Trespassing will cost you",
        "Jail time can be dicey"
    ]

    print("=" * 60)
    print("MONOPOLY PUZZLE - END-TO-END API TEST")
    print("=" * 60)

    session_id = None

    for i, clue in enumerate(clues, 1):
        print(f"\n{'='*60}")
        print(f"CLUE {i}: {clue}")
        print('='*60)

        # Submit clue
        payload = {"clue_text": clue}
        if session_id:
            payload["session_id"] = session_id

        response = requests.post(f"{API_URL}/predict", json=payload)
        response.raise_for_status()

        data = response.json()
        session_id = data["session_id"]

        # Display predictions
        print(f"\nTop 3 Predictions:")
        for pred in data["predictions"]:
            print(f"  {pred['rank']}. {pred['answer']} - {pred['confidence']:.1f}%")
            print(f"     {pred['reasoning']}")

        # Display guess recommendation
        rec = data["guess_recommendation"]
        if rec["should_guess"]:
            print(f"\n  RECOMMENDATION: GUESS NOW!")
            print(f"  {rec['rationale']}")
        else:
            print(f"\n  Continue to next clue (confidence below {rec['confidence_threshold']*100}%)")

        # Check if Monopoly is in top 3
        answers = [p["answer"] for p in data["predictions"]]
        if "Monopoly" in answers:
            rank = answers.index("Monopoly") + 1
            conf = data["predictions"][rank-1]["confidence"]
            print(f"\n  [FOUND] Monopoly is #{rank} with {conf:.1f}% confidence")

            if rank == 1 and conf >= 75 and i >= 3:
                print(f"\n  SUCCESS! Monopoly predicted correctly by Clue {i}")
                break

    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print('='*60)

if __name__ == "__main__":
    test_monopoly_puzzle()
