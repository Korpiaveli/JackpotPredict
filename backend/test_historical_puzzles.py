#!/usr/bin/env python3
"""
Test suite for historical JackpotPredict puzzles.

Tests the system against known trivia puzzles to validate prediction accuracy.
"""

import requests
import json
import time
from typing import List, Dict
from dataclasses import dataclass

API_URL = "http://localhost:8000/api"

# Delay between API calls (seconds) to avoid rate limiting
API_DELAY = 0.5


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
    # Additional historical puzzles
    PuzzleTest(
        name="Star Wars",
        clues=[
            "A long time ago",
            "The force is strong",
            "Dark side vs light",
            "Darth Vader's saga",
            "May the force be with you"
        ],
        answer="Star Wars",
        target_clue=3,
        min_confidence=60.0
    ),
    PuzzleTest(
        name="Titanic",
        clues=[
            "Unsinkable they said",
            "An icy ending",
            "Jack and Rose",
            "Heart of the ocean",
            "King of the world"
        ],
        answer="Titanic",
        target_clue=3,
        min_confidence=60.0
    ),
    PuzzleTest(
        name="Michael Jordan",
        clues=[
            "Air time legend",
            "Six championship rings",
            "Number 23 forever",
            "Space Jam star",
            "His Airness from Chicago"
        ],
        answer="Michael Jordan",
        target_clue=3,
        min_confidence=60.0
    ),
    PuzzleTest(
        name="Google",
        clues=[
            "Started in a garage",
            "Don't be evil",
            "Search for anything",
            "The number one search engine",
            "Googol inspired its name"
        ],
        answer="Google",
        target_clue=3,
        min_confidence=60.0
    ),
    PuzzleTest(
        name="Statue of Liberty",
        clues=[
            "A gift from France",
            "Torch bearer",
            "Lady in the harbor",
            "Welcome to America",
            "Liberty enlightening the world"
        ],
        answer="Statue of Liberty",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Disney",
        clues=[
            "A magical kingdom",
            "Where dreams come true",
            "Started with a mouse",
            "The happiest place on Earth",
            "Walt's vision"
        ],
        answer="Disney",
        target_clue=3,
        min_confidence=60.0
    ),
    PuzzleTest(
        name="Golden Gate Bridge",
        clues=[
            "Not actually golden",
            "San Francisco icon",
            "International orange",
            "Spans the bay",
            "Art deco beauty"
        ],
        answer="Golden Gate Bridge",
        target_clue=2,
        min_confidence=70.0
    ),
    # ========== EXPANDED TEST SUITE ==========
    # Additional puzzles for comprehensive model comparison

    # PEOPLE - Celebrities
    PuzzleTest(
        name="Oprah Winfrey",
        clues=[
            "You get a car!",
            "The queen of daytime",
            "Book club sensation",
            "OWN network founder",
            "Chicago media mogul"
        ],
        answer="Oprah Winfrey",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Elvis Presley",
        clues=[
            "The King",
            "Hound dog howler",
            "Graceland resident",
            "Blue suede shoes",
            "Memphis legend"
        ],
        answer="Elvis Presley",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Albert Einstein",
        clues=[
            "Relatively famous",
            "E equals MC squared",
            "Wild hair genius",
            "Princeton professor",
            "Nobel Prize physicist"
        ],
        answer="Albert Einstein",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Beyonce",
        clues=[
            "Queen Bey",
            "Destiny's child",
            "Single ladies anthem",
            "Lemonade maker",
            "Houston superstar"
        ],
        answer="Beyonce",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Leonardo DiCaprio",
        clues=[
            "Finally got his Oscar",
            "King of the world (again)",
            "Wolf of Wall Street",
            "Environmental activist",
            "Dating models exclusively"
        ],
        answer="Leonardo DiCaprio",
        target_clue=3,
        min_confidence=60.0
    ),

    # PLACES - Famous Locations
    PuzzleTest(
        name="Grand Canyon",
        clues=[
            "A big hole in the ground",
            "Arizona wonder",
            "Colorado River carved it",
            "Mile deep marvel",
            "Red rock majesty"
        ],
        answer="Grand Canyon",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Las Vegas",
        clues=[
            "Sin City",
            "What happens here stays here",
            "Desert oasis of gambling",
            "The Strip",
            "Nevada neon lights"
        ],
        answer="Las Vegas",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Great Wall of China",
        clues=[
            "Visible from space? Not really",
            "Dragon's backbone",
            "Ancient defense system",
            "Thousands of miles long",
            "Ming Dynasty marvel"
        ],
        answer="Great Wall of China",
        target_clue=3,
        min_confidence=60.0
    ),
    PuzzleTest(
        name="Hollywood",
        clues=[
            "Tinseltown",
            "Where dreams are made",
            "Big white letters on a hill",
            "Movie magic central",
            "California's entertainment capital"
        ],
        answer="Hollywood",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Times Square",
        clues=[
            "New Year's Eve destination",
            "The crossroads of the world",
            "Bright lights big city",
            "Broadway's heart",
            "Manhattan's neon jungle"
        ],
        answer="Times Square",
        target_clue=2,
        min_confidence=70.0
    ),

    # THINGS - Products/Brands
    PuzzleTest(
        name="iPhone",
        clues=[
            "Revolutionized the smartphone",
            "One more thing",
            "Cupertino's cash cow",
            "Steve Jobs' legacy",
            "iOS runs on it"
        ],
        answer="iPhone",
        target_clue=3,
        min_confidence=60.0
    ),
    PuzzleTest(
        name="Coca-Cola",
        clues=[
            "The real thing",
            "Secret formula",
            "Santa's favorite drink",
            "Atlanta original",
            "Open happiness"
        ],
        answer="Coca-Cola",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Nike",
        clues=[
            "Just do it",
            "Swoosh symbol",
            "Air Jordan maker",
            "Greek goddess of victory",
            "Phil Knight's creation"
        ],
        answer="Nike",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="McDonald's",
        clues=[
            "Golden arches",
            "I'm lovin' it",
            "Happy Meals",
            "Big Mac birthplace",
            "Fast food empire"
        ],
        answer="McDonald's",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Tesla",
        clues=[
            "Electric dreams",
            "Elon's baby",
            "Not just a scientist's name",
            "Autopilot pioneer",
            "Cybertruck creator"
        ],
        answer="Tesla",
        target_clue=2,
        min_confidence=70.0
    ),

    # THINGS - Entertainment/Media
    PuzzleTest(
        name="Game of Thrones",
        clues=[
            "Winter is coming",
            "Iron throne seeker",
            "Dragons and direwolves",
            "Red wedding horror",
            "HBO fantasy epic"
        ],
        answer="Game of Thrones",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="The Beatles",
        clues=[
            "Fab Four",
            "British invasion leaders",
            "Abbey Road crossers",
            "Lennon and McCartney",
            "Yeah yeah yeah"
        ],
        answer="The Beatles",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Harry Potter",
        clues=[
            "The boy who lived",
            "Hogwarts student",
            "Lightning bolt scar",
            "Quidditch seeker",
            "J.K. Rowling's wizard"
        ],
        answer="Harry Potter",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Super Bowl",
        clues=[
            "Big game Sunday",
            "Halftime show spectacular",
            "Expensive commercials",
            "Lombardi Trophy",
            "NFL championship"
        ],
        answer="Super Bowl",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Netflix",
        clues=[
            "And chill",
            "Red envelope origins",
            "Binge watching enabler",
            "Stranger Things home",
            "Streaming giant"
        ],
        answer="Netflix",
        target_clue=2,
        min_confidence=70.0
    ),

    # CHALLENGING - Wordplay/Semantic Heavy
    PuzzleTest(
        name="Amazon",
        clues=[
            "A river runs through it",
            "Rainforest and retail",
            "Prime delivery",
            "Jeff's everything store",
            "Alexa's parent"
        ],
        answer="Amazon",
        target_clue=3,
        min_confidence=60.0
    ),
    PuzzleTest(
        name="Apple",
        clues=[
            "Forbidden fruit",
            "Think different",
            "One byte at a time",
            "Cupertino campus",
            "Steve's garage startup"
        ],
        answer="Apple",
        target_clue=3,
        min_confidence=60.0
    ),
    PuzzleTest(
        name="Subway",
        clues=[
            "Underground transportation",
            "Five dollar footlong",
            "Eat fresh",
            "Sandwich artist",
            "Jared's former employer"
        ],
        answer="Subway",
        target_clue=3,
        min_confidence=60.0
    ),
    PuzzleTest(
        name="Mars",
        clues=[
            "The red planet",
            "Candy bar sweetness",
            "Bruno's surname",
            "Fourth from the sun",
            "Elon's destination"
        ],
        answer="Mars",
        target_clue=3,
        min_confidence=60.0
    ),
    PuzzleTest(
        name="Queen",
        clues=[
            "Bohemian Rhapsody rockers",
            "Royal title",
            "Freddie's band",
            "Chess piece",
            "We will rock you"
        ],
        answer="Queen",
        target_clue=2,
        min_confidence=70.0
    ),

    # HISTORICAL FIGURES
    PuzzleTest(
        name="Abraham Lincoln",
        clues=[
            "Honest Abe",
            "Freed the slaves",
            "Tall hat wearer",
            "Ford's Theatre tragedy",
            "16th President"
        ],
        answer="Abraham Lincoln",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Cleopatra",
        clues=[
            "Queen of the Nile",
            "Asp's victim",
            "Caesar's lover",
            "Egyptian ruler",
            "Mark Antony's romance"
        ],
        answer="Cleopatra",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Martin Luther King Jr.",
        clues=[
            "I have a dream",
            "Civil rights leader",
            "Nobel Peace Prize 1964",
            "March on Washington",
            "Atlanta's son"
        ],
        answer="Martin Luther King Jr.",
        target_clue=2,
        min_confidence=70.0
    ),

    # SPORTS
    PuzzleTest(
        name="Muhammad Ali",
        clues=[
            "Float like a butterfly",
            "The Greatest",
            "Cassius Clay transformed",
            "Rumble in the jungle",
            "Louisville Lip"
        ],
        answer="Muhammad Ali",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Olympics",
        clues=[
            "Five rings",
            "Go for gold",
            "Faster higher stronger",
            "Every four years",
            "Ancient Greece tradition"
        ],
        answer="Olympics",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="FIFA World Cup",
        clues=[
            "The beautiful game's biggest prize",
            "Every four years fever",
            "National teams compete",
            "Soccer's holy grail",
            "One billion viewers"
        ],
        answer="FIFA World Cup",
        target_clue=3,
        min_confidence=60.0
    ),

    # SCIENCE/TECHNOLOGY
    PuzzleTest(
        name="DNA",
        clues=[
            "Double helix",
            "Genetic blueprint",
            "Watson and Crick",
            "ATCG code",
            "Life's building blocks"
        ],
        answer="DNA",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Internet",
        clues=[
            "World wide web",
            "Information superhighway",
            "ARPANET evolved",
            "Cat videos home",
            "Global network"
        ],
        answer="Internet",
        target_clue=2,
        min_confidence=70.0
    ),

    # FOOD/DRINK
    PuzzleTest(
        name="Pizza",
        clues=[
            "Italian pie",
            "Cheese and tomato",
            "New York vs Chicago style",
            "Delivery in 30 minutes",
            "Pepperoni favorite"
        ],
        answer="Pizza",
        target_clue=2,
        min_confidence=70.0
    ),
    PuzzleTest(
        name="Starbucks",
        clues=[
            "Mermaid logo",
            "Grande venti tall",
            "Seattle coffee culture",
            "Pumpkin spice pusher",
            "Green apron baristas"
        ],
        answer="Starbucks",
        target_clue=2,
        min_confidence=70.0
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
            time.sleep(API_DELAY)  # Delay to avoid rate limiting
            response = requests.post(f"{API_URL}/predict", json=payload, timeout=30)
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
