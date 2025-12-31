"""
Entity Generator V3 - Generate remaining entities to reach 2500 target.

New subcategories not covered in v1/v2.
"""

import json
import httpx
import time
import argparse
from pathlib import Path
from typing import List, Dict

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:latest"

# New subcategories not covered in v1/v2
CATEGORIES = {
    "thing": [
        # Technology
        "social media platforms", "video game consoles", "streaming services", "search engines",
        "operating systems", "web browsers", "programming languages", "tech companies",
        # Literature & Publications
        "bestselling novels", "famous children's books", "comic book heroes", "famous poems",
        "literary awards", "famous book series", "autobiographies of celebrities",
        # Sports
        "famous sports teams", "sports equipment brands", "martial arts styles", "extreme sports",
        "famous sports stadiums", "sports car models", "racing events",
        # Cultural
        "famous musicals", "opera classics", "ballet performances", "circus acts",
        "magic tricks", "dance styles", "art movements", "fashion trends",
        # Everyday
        "fast food chains", "supermarket chains", "airline companies", "hotel chains",
        "credit card brands", "insurance companies", "shipping companies", "ride-share apps",
        # Historical
        "famous ships", "famous planes", "famous trains", "famous bridges",
        "famous inventions", "famous discoveries", "famous experiments"
    ],
    "place": [
        # Parks & Nature
        "national parks USA", "theme parks worldwide", "famous beaches", "famous islands",
        "famous lakes", "famous rivers", "famous deserts", "famous forests",
        # Architecture
        "famous towers", "famous bridges worldwide", "famous dams", "famous tunnels",
        "famous monuments", "famous memorials", "famous fountains", "famous gardens",
        # Cities Extended
        "African capital cities", "Australian cities", "Canadian cities", "Mexican cities",
        "Middle Eastern cities", "Caribbean islands", "Mediterranean destinations",
        # Special
        "UNESCO World Heritage sites", "famous airports", "famous train stations",
        "famous neighborhoods", "famous streets", "haunted locations", "filming locations"
    ],
    "person": [
        # Historical
        "US Presidents", "British royalty", "ancient emperors", "revolutionary leaders",
        "civil rights leaders", "feminist icons", "religious leaders", "military generals",
        # Science & Innovation
        "famous scientists", "famous inventors", "famous astronauts", "famous surgeons",
        "Nobel Prize winners in science", "famous psychologists", "famous economists",
        # Arts Extended
        "famous dancers", "famous photographers", "famous filmmakers", "famous playwrights",
        "famous poets", "famous sculptors", "famous fashion models", "famous cartoonists",
        # Modern
        "social media influencers", "podcasters", "streamers", "esports players",
        "business moguls", "hedge fund managers", "startup founders", "crypto pioneers"
    ]
}

PROMPT_TEMPLATE = '''Generate 10 famous {category_type} that would make good trivia answers.
Focus on: {subcategory}

For each entity, provide this EXACT JSON structure:
[
  {{
    "name": "Full Name Here",
    "category": "{category_type}",
    "polysemy_triggers": ["word that hints at answer", "another hint word", "wordplay term"],
    "clue_associations": ["cryptic clue phrase", "another clue hint", "descriptive phrase"],
    "aliases": ["nickname", "alternate name"]
  }}
]

Requirements:
- Names should be well-known to general audiences
- Polysemy_triggers should be 3-5 words that could hint at the answer through wordplay
- Clue_associations should be 3-5 cryptic phrases that describe the entity
- Aliases should be 1-3 common nicknames or alternate names
- Each entity must be unique and different

Return ONLY the JSON array, nothing else.'''


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
                        "temperature": 0.8,
                        "num_predict": 2500,
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
                print(f"  [ERROR] No JSON array found")
                return []

            json_str = text[start:end]
            entities = json.loads(json_str)

            # Validate and clean entities
            valid_entities = []
            for entity in entities:
                if isinstance(entity, dict) and "name" in entity:
                    entity.setdefault("category", category)
                    entity.setdefault("polysemy_triggers", [])
                    entity.setdefault("clue_associations", [])
                    entity.setdefault("aliases", [])
                    entity["source"] = "generated_v3"
                    entity["annotated"] = True
                    valid_entities.append(entity)

            return valid_entities

    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON: {str(e)[:50]}")
        return []
    except Exception as e:
        print(f"  [ERROR] {str(e)[:50]}")
        return []


def load_existing_entities(filepaths: List[Path]) -> set:
    """Load existing entity names to avoid duplicates."""
    existing = set()
    for filepath in filepaths:
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
    parser = argparse.ArgumentParser(description="Generate annotated entities V3")
    parser.add_argument("--target", type=int, default=2500, help="Target total entities")
    parser.add_argument("--output", type=Path, default=Path("app/data/generated_entities_v3.json"))
    parser.add_argument("--existing", type=Path, nargs="+", help="Existing entity files")

    args = parser.parse_args()

    # Default existing files
    if not args.existing:
        args.existing = [
            Path("app/data/annotated_entities.json"),
            Path("app/data/additional_entities.json"),
            Path("app/data/generated_entities.json"),
            Path("app/data/generated_entities_v2.json"),
        ]

    # Load existing entities
    existing_names = load_existing_entities(args.existing)

    current_count = len(existing_names)
    to_generate = args.target - current_count

    print(f"Found {current_count} existing entities")
    print(f"Need ~{to_generate} more to reach {args.target}")
    print("=" * 60)

    if to_generate <= 0:
        print("Target already reached!")
        return

    all_generated = []

    for category, subcategories in CATEGORIES.items():
        print(f"\n[{category.upper()}]")

        for subcategory in subcategories:
            if len(all_generated) + current_count >= args.target:
                break

            print(f"  {subcategory}...", end=" ", flush=True)

            entities = generate_entities_batch(category, subcategory)

            new_entities = []
            for entity in entities:
                name_lower = entity["name"].lower()
                if name_lower not in existing_names:
                    existing_names.add(name_lower)
                    new_entities.append(entity)

            all_generated.extend(new_entities)
            print(f"{len(new_entities)} new")

            time.sleep(0.3)

        if len(all_generated) + current_count >= args.target:
            break

    print("\n" + "=" * 60)
    print(f"Generated: {len(all_generated)} entities")
    print(f"Total will be: {current_count + len(all_generated)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(all_generated, f, indent=2, ensure_ascii=False)

    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
