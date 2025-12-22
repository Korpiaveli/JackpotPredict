"""
JackpotPredict CLI - Command-line interface for testing the prediction engine.

Usage:
    python -m app.main

Enter clues one at a time to see real-time predictions.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.entity_registry import EntityRegistry, Entity, EntityCategory
from app.core.clue_analyzer import ClueAnalyzer
from app.core.jackpot_predict import JackpotPredict


def print_banner():
    """Print welcome banner."""
    print("=" * 70)
    print("🎰 JACKPOT PREDICT - AI Trivia Answer Prediction Engine")
    print("=" * 70)
    print("Real-time predictions for Netflix's Best Guess Live game show")
    print()


def print_predictions(response):
    """Pretty-print prediction results."""
    print(f"\n{'='*70}")
    print(f"  CLUE {response.clue_number} ANALYSIS")
    print(f"{'='*70}")
    print(f"  Processing time: {response.elapsed_time:.3f}s")
    print(f"  Session ID: {response.session_id}")
    print()

    print("  TOP 3 PREDICTIONS:")
    print(f"  {'-'*68}")

    medals = ["🥇", "🥈", "🥉"]
    for pred in response.predictions:
        medal = medals[pred.rank - 1] if pred.rank <= 3 else f"#{pred.rank}"
        confidence_bar = "█" * int(pred.confidence / 5)  # 20 chars max

        print(f"  {medal} {pred.rank}. {pred.answer.upper()}")
        print(f"     Confidence: {pred.confidence:.1f}% {confidence_bar}")
        print(f"     Category: {pred.category}")
        print(f"     Reasoning: {pred.reasoning}")
        print()

    if response.should_guess:
        print(f"  {'⚡'*30}")
        print(f"  ⚠️  RECOMMENDATION: GUESS NOW!")
        print(f"  Confidence threshold met for Clue {response.clue_number}")
        print(f"  {'⚡'*30}")

    print(f"{'='*70}\n")


def seed_test_entities(registry: EntityRegistry):
    """Seed registry with confirmed answers from PRD."""
    print("Seeding entity registry with confirmed answers...")

    test_entities = [
        Entity(
            canonical_name="Paris Hilton",
            aliases=["Paris", "Hilton"],
            category=EntityCategory.PERSON,
            polysemy_triggers=["romantic city", "hotel chain", "basic", "simple life"],
            clue_associations=["hospitality", "reality TV", "2000s icon", "DJ", "that's hot"],
            recency_score=0.7
        ),
        Entity(
            canonical_name="Monopoly",
            aliases=["Monopoly Game", "Monopoly Board Game"],
            category=EntityCategory.THING,
            polysemy_triggers=["flavors", "editions", "versions", "market control"],
            clue_associations=["board game", "property", "jail", "dice", "go around", "rent"],
            recency_score=0.9
        ),
        Entity(
            canonical_name="Mt. Rushmore",
            aliases=["Mount Rushmore", "Rushmore"],
            category=EntityCategory.PLACE,
            polysemy_triggers=["natural", "carved", "faces", "presidents"],
            clue_associations=["mountain", "South Dakota", "monument", "stone", "carved faces"],
            recency_score=0.8
        ),
        Entity(
            canonical_name="Bowling",
            aliases=["Ten Pin Bowling", "Bowling Game"],
            category=EntityCategory.THING,
            polysemy_triggers=["strikes", "gutters", "pins", "lanes"],
            clue_associations=["sport", "alley", "ball", "success and failure", "ten pins"],
            recency_score=0.75
        ),
        Entity(
            canonical_name="Oreo",
            aliases=["Oreo Cookie", "Oreos"],
            category=EntityCategory.THING,
            polysemy_triggers=["leader", "pack", "first", "cookies"],
            clue_associations=["cookie", "chocolate", "cream", "twist", "dunk", "first in pack"],
            recency_score=0.95
        ),
        Entity(
            canonical_name="Barbie",
            aliases=["Barbie Doll"],
            category=EntityCategory.PERSON,
            polysemy_triggers=["doll", "blonde", "fashion", "pink"],
            clue_associations=["doll", "Mattel", "blonde", "fashion", "Ken", "dream house"],
            recency_score=0.95
        ),
        Entity(
            canonical_name="Titanic",
            aliases=["RMS Titanic", "Titanic Ship"],
            category=EntityCategory.THING,
            polysemy_triggers=["sink", "iceberg", "ship", "movie"],
            clue_associations=["ship", "disaster", "iceberg", "Leonardo DiCaprio", "ups and downs"],
            recency_score=0.85
        ),
    ]

    for entity in test_entities:
        try:
            registry.add_entity(entity)
            print(f"  ✓ Added: {entity.canonical_name}")
        except ValueError as e:
            print(f"  ⚠ Skipped: {entity.canonical_name} (already exists)")

    print(f"Registry now contains {registry.get_entity_count()} entities\n")


def run_cli():
    """Main CLI loop."""
    print_banner()

    # Initialize components
    print("Initializing components...")
    print("  - Loading entity registry...")
    registry = EntityRegistry()

    print("  - Loading spaCy model (en_core_web_lg)...")
    try:
        analyzer = ClueAnalyzer()
    except OSError:
        print("\n❌ ERROR: spaCy model not found!")
        print("Please run: python -m spacy download en_core_web_lg")
        print("Or use a smaller model: python -m spacy download en_core_web_sm")
        return

    print("  - Initializing prediction engine...")
    predictor = JackpotPredict(registry, analyzer)

    # Seed test entities
    seed_test_entities(registry)

    print("✅ Initialization complete!\n")
    print("=" * 70)
    print("INSTRUCTIONS:")
    print("  - Enter clues one at a time (press Enter after each)")
    print("  - Type 'reset' to start a new puzzle")
    print("  - Type 'quit' or 'exit' to end")
    print("  - Type 'test' to run Monopoly test case")
    print("=" * 70)
    print()

    # Main input loop
    while True:
        try:
            clue_num = predictor.clue_count + 1
            prompt = f"Clue {clue_num}: "

            clue_text = input(prompt).strip()

            if not clue_text:
                print("⚠️  Empty clue, please enter text\n")
                continue

            # Handle commands
            if clue_text.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye! Good luck on Best Guess Live!")
                break

            elif clue_text.lower() == 'reset':
                predictor.reset()
                print("\n🔄 Session reset. Ready for new puzzle!\n")
                continue

            elif clue_text.lower() == 'test':
                print("\n🧪 Running Monopoly test case...\n")
                test_monopoly(predictor)
                predictor.reset()
                continue

            # Process clue
            response = predictor.add_clue(clue_text)
            print_predictions(response)

            # Check if puzzle complete
            if predictor.clue_count >= 5:
                print("🎯 Puzzle complete! 5 clues analyzed.")
                print("Type 'reset' to start a new puzzle.\n")

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


def test_monopoly(predictor: JackpotPredict):
    """Run the Monopoly test case from the PRD."""
    monopoly_clues = [
        "Savors many flavors",
        "Round and round",
        "A hostile takeover",
        "Trespassing will cost you",
        "Jail time can be dicey"
    ]

    print("Testing with Monopoly clues from PRD:")
    for i, clue in enumerate(monopoly_clues, 1):
        print(f"\n{'>'*70}")
        print(f"  Clue {i}: \"{clue}\"")
        print(f"{'>'*70}")

        response = predictor.add_clue(clue)
        print_predictions(response)

        # Check if Monopoly is #1 by Clue 3
        if i == 3:
            top_answer = response.predictions[0].answer
            if "Monopoly" in top_answer:
                print("  ✅ SUCCESS: Monopoly is #1 prediction by Clue 3!")
            else:
                print(f"  ⚠️  WARNING: Expected Monopoly, got {top_answer}")

    print("\n" + "="*70)
    print("  TEST COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_cli()
