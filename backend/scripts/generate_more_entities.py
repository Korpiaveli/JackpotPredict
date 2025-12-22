#!/usr/bin/env python3
"""
Generate additional high-probability trivia entities.

This script creates a curated list of entities that are likely to appear
in Netflix trivia games, based on pop culture relevance and polysemy potential.
"""

import json
from typing import List, Dict

# High-probability trivia categories
ADDITIONAL_ENTITIES = [
    # Movies (iconic, recent blockbusters)
    {"name": "The Shawshank Redemption", "category": "thing"},
    {"name": "The Godfather", "category": "thing"},
    {"name": "Pulp Fiction", "category": "thing"},
    {"name": "Forrest Gump", "category": "thing"},
    {"name": "The Matrix", "category": "thing"},
    {"name": "Inception", "category": "thing"},
    {"name": "The Dark Knight", "category": "thing"},
    {"name": "Avatar", "category": "thing"},
    {"name": "Avengers Endgame", "category": "thing"},
    {"name": "Black Panther", "category": "thing"},
    {"name": "Jurassic Park", "category": "thing"},
    {"name": "E.T.", "category": "thing"},
    {"name": "Jaws", "category": "thing"},
    {"name": "Rocky", "category": "thing"},
    {"name": "The Wizard of Oz", "category": "thing"},
    {"name": "Casablanca", "category": "thing"},
    {"name": "Gone with the Wind", "category": "thing"},
    {"name": "The Sound of Music", "category": "thing"},

    # TV Shows (iconic, high cultural impact)
    {"name": "Friends", "category": "thing"},
    {"name": "The Office", "category": "thing"},
    {"name": "Breaking Bad", "category": "thing"},
    {"name": "Game of Thrones", "category": "thing"},
    {"name": "The Simpsons", "category": "thing"},
    {"name": "Seinfeld", "category": "thing"},
    {"name": "Stranger Things", "category": "thing"},
    {"name": "The Crown", "category": "thing"},
    {"name": "The Sopranos", "category": "thing"},
    {"name": "The Wire", "category": "thing"},
    {"name": "Mad Men", "category": "thing"},
    {"name": "Lost", "category": "thing"},
    {"name": "The West Wing", "category": "thing"},
    {"name": "Parks and Recreation", "category": "thing"},
    {"name": "30 Rock", "category": "thing"},
    {"name": "Arrested Development", "category": "thing"},
    {"name": "Frasier", "category": "thing"},
    {"name": "Cheers", "category": "thing"},

    # Celebrities (A-list, high recognition)
    {"name": "Brad Pitt", "category": "person"},
    {"name": "Leonardo DiCaprio", "category": "person"},
    {"name": "Meryl Streep", "category": "person"},
    {"name": "Denzel Washington", "category": "person"},
    {"name": "Jennifer Aniston", "category": "person"},
    {"name": "Will Smith", "category": "person"},
    {"name": "Dwayne Johnson", "category": "person"},
    {"name": "Scarlett Johansson", "category": "person"},
    {"name": "Robert Downey Jr", "category": "person"},
    {"name": "Chris Hemsworth", "category": "person"},
    {"name": "Zendaya", "category": "person"},
    {"name": "Timothee Chalamet", "category": "person"},
    {"name": "Emma Stone", "category": "person"},
    {"name": "Ryan Gosling", "category": "person"},
    {"name": "Margot Robbie", "category": "person"},
    {"name": "Lady Gaga", "category": "person"},
    {"name": "Drake", "category": "person"},
    {"name": "Adele", "category": "person"},
    {"name": "Ed Sheeran", "category": "person"},
    {"name": "Ariana Grande", "category": "person"},
    {"name": "Billie Eilish", "category": "person"},
    {"name": "The Weeknd", "category": "person"},
    {"name": "Kanye West", "category": "person"},
    {"name": "Jay-Z", "category": "person"},
    {"name": "Rihanna", "category": "person"},

    # Sports Figures
    {"name": "Serena Williams", "category": "person"},
    {"name": "Roger Federer", "category": "person"},
    {"name": "Cristiano Ronaldo", "category": "person"},
    {"name": "Lionel Messi", "category": "person"},
    {"name": "Usain Bolt", "category": "person"},
    {"name": "Simone Biles", "category": "person"},
    {"name": "Tiger Woods", "category": "person"},
    {"name": "Steph Curry", "category": "person"},
    {"name": "Patrick Mahomes", "category": "person"},
    {"name": "Shohei Ohtani", "category": "person"},
    {"name": "Caitlin Clark", "category": "person"},

    # Historical Figures (widely known)
    {"name": "Abraham Lincoln", "category": "person"},
    {"name": "George Washington", "category": "person"},
    {"name": "Martin Luther King Jr", "category": "person"},
    {"name": "Albert Einstein", "category": "person"},
    {"name": "Nelson Mandela", "category": "person"},
    {"name": "Mahatma Gandhi", "category": "person"},
    {"name": "Winston Churchill", "category": "person"},
    {"name": "Queen Elizabeth II", "category": "person"},
    {"name": "Princess Diana", "category": "person"},
    {"name": "Rosa Parks", "category": "person"},

    # Brands/Companies (iconic)
    {"name": "Facebook", "category": "thing"},
    {"name": "Instagram", "category": "thing"},
    {"name": "Twitter", "category": "thing"},
    {"name": "TikTok", "category": "thing"},
    {"name": "YouTube", "category": "thing"},
    {"name": "Tesla", "category": "thing"},
    {"name": "iPhone", "category": "thing"},
    {"name": "PlayStation", "category": "thing"},
    {"name": "Xbox", "category": "thing"},
    {"name": "Nintendo", "category": "thing"},
    {"name": "LEGO", "category": "thing"},
    {"name": "Mattel", "category": "thing"},
    {"name": "Hot Wheels", "category": "thing"},
    {"name": "Nerf", "category": "thing"},
    {"name": "Rubik's Cube", "category": "thing"},

    # Foods (iconic American/global)
    {"name": "Taco", "category": "thing"},
    {"name": "Sushi", "category": "thing"},
    {"name": "Ramen", "category": "thing"},
    {"name": "Pasta", "category": "thing"},
    {"name": "Sandwich", "category": "thing"},
    {"name": "Burrito", "category": "thing"},
    {"name": "Nachos", "category": "thing"},
    {"name": "Wings", "category": "thing"},
    {"name": "BBQ Ribs", "category": "thing"},
    {"name": "Fried Chicken", "category": "thing"},
    {"name": "Cheesecake", "category": "thing"},
    {"name": "Brownie", "category": "thing"},
    {"name": "Cupcake", "category": "thing"},
    {"name": "Pancakes", "category": "thing"},
    {"name": "Waffles", "category": "thing"},
    {"name": "Bacon", "category": "thing"},
    {"name": "Avocado", "category": "thing"},
    {"name": "Kale", "category": "thing"},

    # Landmarks (world-famous)
    {"name": "Taj Mahal", "category": "place"},
    {"name": "Colosseum", "category": "place"},
    {"name": "Machu Picchu", "category": "place"},
    {"name": "Stonehenge", "category": "place"},
    {"name": "Sydney Opera House", "category": "place"},
    {"name": "Burj Khalifa", "category": "place"},
    {"name": "Empire State Building", "category": "place"},
    {"name": "White House", "category": "place"},
    {"name": "Buckingham Palace", "category": "place"},
    {"name": "Louvre", "category": "place"},
    {"name": "Vatican", "category": "place"},
    {"name": "Kremlin", "category": "place"},
    {"name": "Forbidden City", "category": "place"},
    {"name": "Angkor Wat", "category": "place"},
    {"name": "Pyramids of Giza", "category": "place"},
    {"name": "Sphinx", "category": "place"},
    {"name": "Petra", "category": "place"},
    {"name": "Acropolis", "category": "place"},
    {"name": "Niagara Falls", "category": "place"},
    {"name": "Victoria Falls", "category": "place"},
    {"name": "Yellowstone", "category": "place"},
    {"name": "Yosemite", "category": "place"},
    {"name": "Everest", "category": "place"},

    # Cities (major global)
    {"name": "New York", "category": "place"},
    {"name": "Los Angeles", "category": "place"},
    {"name": "Chicago", "category": "place"},
    {"name": "Las Vegas", "category": "place"},
    {"name": "Miami", "category": "place"},
    {"name": "London", "category": "place"},
    {"name": "Paris", "category": "place"},
    {"name": "Rome", "category": "place"},
    {"name": "Tokyo", "category": "place"},
    {"name": "Beijing", "category": "place"},
    {"name": "Dubai", "category": "place"},
    {"name": "Sydney", "category": "place"},
    {"name": "Rio de Janeiro", "category": "place"},
    {"name": "Barcelona", "category": "place"},
    {"name": "Amsterdam", "category": "place"},
    {"name": "Venice", "category": "place"},
    {"name": "Prague", "category": "place"},
    {"name": "Athens", "category": "place"},
    {"name": "Istanbul", "category": "place"},
    {"name": "Cairo", "category": "place"},

    # Sports & Games
    {"name": "Super Bowl", "category": "thing"},
    {"name": "World Cup", "category": "thing"},
    {"name": "Olympics", "category": "thing"},
    {"name": "March Madness", "category": "thing"},
    {"name": "World Series", "category": "thing"},
    {"name": "NBA Finals", "category": "thing"},
    {"name": "Stanley Cup", "category": "thing"},
    {"name": "Wimbledon", "category": "thing"},
    {"name": "Masters", "category": "thing"},
    {"name": "Kentucky Derby", "category": "thing"},
    {"name": "Daytona 500", "category": "thing"},
    {"name": "Tour de France", "category": "thing"},

    # Additional Board Games & Toys
    {"name": "Uno", "category": "thing"},
    {"name": "Cards Against Humanity", "category": "thing"},
    {"name": "Exploding Kittens", "category": "thing"},
    {"name": "Candy Land", "category": "thing"},
    {"name": "Chutes and Ladders", "category": "thing"},
    {"name": "Operation", "category": "thing"},
    {"name": "Mouse Trap", "category": "thing"},
    {"name": "Twister", "category": "thing"},
    {"name": "Pictionary", "category": "thing"},
    {"name": "Charades", "category": "thing"},
    {"name": "Taboo", "category": "thing"},
    {"name": "Boggle", "category": "thing"},
    {"name": "Yahtzee", "category": "thing"},
    {"name": "Dominoes", "category": "thing"},
    {"name": "Poker", "category": "thing"},
    {"name": "Blackjack", "category": "thing"},
    {"name": "Roulette", "category": "thing"},
    {"name": "Bingo", "category": "thing"},

    # Musical Instruments
    {"name": "Guitar", "category": "thing"},
    {"name": "Drums", "category": "thing"},
    {"name": "Violin", "category": "thing"},
    {"name": "Trumpet", "category": "thing"},
    {"name": "Saxophone", "category": "thing"},
    {"name": "Flute", "category": "thing"},
    {"name": "Harp", "category": "thing"},
    {"name": "Accordion", "category": "thing"},

    # Household Items (high polysemy potential)
    {"name": "Blender", "category": "thing"},
    {"name": "Toaster", "category": "thing"},
    {"name": "Oven", "category": "thing"},
    {"name": "Stove", "category": "thing"},
    {"name": "Dishwasher", "category": "thing"},
    {"name": "Vacuum", "category": "thing"},
    {"name": "Broom", "category": "thing"},
    {"name": "Mop", "category": "thing"},
    {"name": "Bucket", "category": "thing"},
    {"name": "Hammer", "category": "thing"},
    {"name": "Drill", "category": "thing"},
    {"name": "Saw", "category": "thing"},
    {"name": "Wrench", "category": "thing"},
    {"name": "Screwdriver", "category": "thing"},
    {"name": "Ladder", "category": "thing"},

    # Transportation
    {"name": "Bicycle", "category": "thing"},  # Note: already in DB, but keeping for completeness
    {"name": "Skateboard", "category": "thing"},
    {"name": "Scooter", "category": "thing"},
    {"name": "Motorcycle", "category": "thing"},
    {"name": "Submarine", "category": "thing"},
    {"name": "Helicopter", "category": "thing"},
    {"name": "Airplane", "category": "thing"},
    {"name": "Rocket", "category": "thing"},
    {"name": "Train", "category": "thing"},
    {"name": "Trolley", "category": "thing"},
    {"name": "Cable Car", "category": "thing"},

    # Animals (iconic)
    {"name": "Panda", "category": "thing"},
    {"name": "Penguin", "category": "thing"},
    {"name": "Dolphin", "category": "thing"},
    {"name": "Whale", "category": "thing"},
    {"name": "Shark", "category": "thing"},
    {"name": "Octopus", "category": "thing"},
    {"name": "Giraffe", "category": "thing"},
    {"name": "Zebra", "category": "thing"},
    {"name": "Rhino", "category": "thing"},
    {"name": "Hippo", "category": "thing"},
    {"name": "Koala", "category": "thing"},
    {"name": "Kangaroo", "category": "thing"},
    {"name": "Sloth", "category": "thing"},
    {"name": "Flamingo", "category": "thing"},
    {"name": "Peacock", "category": "thing"},
    {"name": "Owl", "category": "thing"},
    {"name": "Parrot", "category": "thing"},
    {"name": "Toucan", "category": "thing"},

    # Clothing & Accessories
    {"name": "Jeans", "category": "thing"},
    {"name": "Sneakers", "category": "thing"},
    {"name": "Sunglasses", "category": "thing"},
    {"name": "Hat", "category": "thing"},
    {"name": "Scarf", "category": "thing"},
    {"name": "Tie", "category": "thing"},
    {"name": "Belt", "category": "thing"},
    {"name": "Watch", "category": "thing"},
    {"name": "Ring", "category": "thing"},  # Note: already in DB
    {"name": "Necklace", "category": "thing"},
    {"name": "Earrings", "category": "thing"},
    {"name": "Bracelet", "category": "thing"},
]


def generate_entities_file():
    """Generate additional entities JSON file."""
    print(f"Generating {len(ADDITIONAL_ENTITIES)} additional entities...")

    # Create entity objects with default values
    entities = []
    for ent in ADDITIONAL_ENTITIES:
        entity = {
            "canonical_name": ent["name"],
            "category": ent["category"],
            "aliases": [],
            "polysemy_triggers": [],
            "clue_associations": [],
            "recency_score": 0.5,  # Default medium recency
            "source": "curated_trivia_list"
        }
        entities.append(entity)

    # Save to file
    output_file = "app/data/additional_entities.json"
    with open(output_file, "w") as f:
        json.dump(entities, f, indent=2)

    print(f"[OK] Saved {len(entities)} entities to {output_file}")
    print(f"\nCategory breakdown:")
    category_counts = {}
    for ent in entities:
        cat = ent["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")

    print(f"\nNext step: Run annotate_entities.py to generate AI annotations")

    return entities


if __name__ == "__main__":
    generate_entities_file()
