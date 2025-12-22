#!/usr/bin/env python3
"""Quick test of confidence bug fix."""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.entity_registry import EntityRegistry
from app.core.clue_analyzer import ClueAnalyzer
from app.core.jackpot_predict import JackpotPredict

def main():
    print("Testing confidence fix...\n")

    # Initialize components
    registry = EntityRegistry()
    analyzer = ClueAnalyzer()
    predictor = JackpotPredict(registry, analyzer)

    print(f"Entity count: {len(registry._get_all_entities())}\n")

    # Test with first clue from Monopoly puzzle
    clue = "Savors many flavors"
    print(f"Clue 1: {clue}")

    response = predictor.add_clue(clue)

    print(f"\nTop 3 Predictions:")
    for pred in response.predictions:
        print(f"  {pred.rank}. {pred.answer} - {pred.confidence:.1f}%")
        if pred.confidence > 100 or pred.confidence < 0:
            print(f"     ERROR: Confidence out of range!")
            return 1

    print(f"\nSuccess! All confidences in 0-100% range")
    return 0

if __name__ == "__main__":
    sys.exit(main())
