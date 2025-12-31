"""
Entity Generator - Generate annotated entities using LLM.

Generates trivia-worthy entities with polysemy triggers, clue associations, and aliases.
"""

import json
import httpx
import time
import argparse
from pathlib import Path
from typing import List, Dict

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:latest"

CATEGORIES = {
    "thing": [
        "famous brands", "board games", "video games", "movies", "TV shows",
        "foods", "beverages", "sports equipment", "musical instruments",
        "vehicles", "household items", "toys", "books", "songs", "albums",
        "inventions", "technologies", "apps", "websites", "social media platforms",
        "clothing brands", "fast food chains", "candy", "snacks", "desserts",
        "awards", "holidays", "fictional characters", "superheroes", "cartoon characters"
    ],
    "place": [
        "world landmarks", "famous buildings", "monuments", "national parks",
        "cities", "countries", "islands", "mountains", "rivers", "lakes",
        "bridges", "towers", "stadiums", "museums", "theme parks",
        "historical sites", "UNESCO sites", "beaches", "deserts", "forests"
    ],
    "person": [
        "athletes", "musicians", "actors", "directors", "authors",
        "scientists", "inventors", "politicians", "business leaders", "artists",
        "comedians", "TV hosts", "social media influencers", "chefs",
        "historical figures", "royalty", "astronauts", "activists"
    ]
}

PROMPT_TEMPLATE = '''Generate 10 famous {category_type} that would make good trivia answers for a guessing game.
Focus on: {subcategory}

For each entity, provide:
1. name: The canonical name
2. category: "{category_type}"
3. polysemy_triggers: 3-5 words/phrases that could hint at this answer through wordplay
4. clue_associations: 3-5 cryptic clue phrases that could describe this
5. aliases: 1-3 alternative names or nicknames

Return ONLY valid JSON array, no other text:
[
  {{
    "name": "Example Name",
    "category": "{category_type}",
    "polysemy_triggers": ["word1", "word2", "word3"],
    "clue_associations": ["cryptic phrase 1", "cryptic phrase 2"],
    "aliases": ["nickname1"]
  }}
]

Make sure entities are:
- Well-known to general audiences
- Distinct from each other
- Have interesting wordplay potential
- NOT duplicates of common entities like "Eiffel Tower", "Statue of Liberty", "Star Wars"

Return ONLY the JSON array.'''


def generate_entities_batch(category: str, subcategory: str) -> List[Dict]:
    """Generate a batch of entities for a category/subcategory."""
    prompt = PROMPT_TEMPLATE.format(
        category_type=category,
        subcategory=subcategory
    )

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 2000,
                    }
                }
            )

            if response.status_code != 200:
                print(f"  [ERROR] Ollama returned {response.status_code}")
                return []

            result = response.json()
            text = result.get("response", "")

            # Find JSON array in response
            start = text.find('[')
            end = text.rfind(']') + 1

            if start == -1 or end == 0:
                print(f"  [ERROR] No JSON array found in response")
                return []

            json_str = text[start:end]
            entities = json.loads(json_str)

            # Validate and clean entities
            valid_entities = []
            for entity in entities:
                if isinstance(entity, dict) and "name" in entity:
                    # Ensure required fields
                    entity.setdefault("category", category)
                    entity.setdefault("polysemy_triggers", [])
                    entity.setdefault("clue_associations", [])
                    entity.setdefault("aliases", [])
                    entity["source"] = "generated"
                    entity["annotated"] = True
                    valid_entities.append(entity)

            return valid_entities

    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON decode error: {e}")
        return []
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []


def load_existing_entities(filepath: Path) -> set:
    """Load existing entity names to avoid duplicates."""
    existing = set()
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                for entity in data:
                    existing.add(entity.get("name", "").lower())
            elif isinstance(data, dict) and "entities" in data:
                for entity in data["entities"]:
                    existing.add(entity.get("name", "").lower())
    return existing


def main():
    parser = argparse.ArgumentParser(description="Generate annotated entities")
    parser.add_argument("--target", type=int, default=2500, help="Target total entities")
    parser.add_argument("--output", type=Path, default=Path("data/generated_entities.json"))
    parser.add_argument("--existing", type=Path, nargs="+", help="Existing entity files to check for duplicates")

    args = parser.parse_args()

    # Load existing entities
    existing_names = set()
    if args.existing:
        for filepath in args.existing:
            existing_names.update(load_existing_entities(filepath))

    print(f"Found {len(existing_names)} existing entities to avoid duplicates")

    # Calculate how many to generate
    current_count = len(existing_names)
    to_generate = args.target - current_count

    if to_generate <= 0:
        print(f"Already have {current_count} entities, target is {args.target}")
        return

    print(f"Need to generate ~{to_generate} entities to reach {args.target}")
    print("=" * 60)

    all_generated = []

    # Generate entities by category and subcategory
    for category, subcategories in CATEGORIES.items():
        print(f"\n[{category.upper()}]")

        for subcategory in subcategories:
            if len(all_generated) + current_count >= args.target:
                break

            print(f"  Generating: {subcategory}...", end=" ", flush=True)

            entities = generate_entities_batch(category, subcategory)

            # Filter out duplicates
            new_entities = []
            for entity in entities:
                name_lower = entity["name"].lower()
                if name_lower not in existing_names:
                    existing_names.add(name_lower)
                    new_entities.append(entity)

            all_generated.extend(new_entities)
            print(f"{len(new_entities)} new entities")

            # Small delay to avoid overwhelming Ollama
            time.sleep(0.5)

    # Save generated entities
    print("\n" + "=" * 60)
    print(f"Total generated: {len(all_generated)} entities")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(all_generated, f, indent=2, ensure_ascii=False)

    print(f"Saved to: {args.output}")

    # Category breakdown
    print("\nCategory breakdown:")
    for cat in ["thing", "place", "person"]:
        count = sum(1 for e in all_generated if e.get("category") == cat)
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
