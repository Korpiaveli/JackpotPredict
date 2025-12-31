"""
Entity Generator V2 - Generate more annotated entities using LLM.

Extended subcategories for more variety.
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
        # Entertainment
        "classic movies from 1980s-2000s", "animated movies", "horror movies", "comedy movies",
        "action movies", "sci-fi movies", "romantic comedies", "documentary films",
        "sitcoms", "drama TV series", "reality TV shows", "game shows",
        "anime series", "Netflix originals", "HBO shows", "streaming series",
        # Games
        "classic arcade games", "Nintendo games", "PlayStation games", "mobile games",
        "card games", "casino games", "party games", "strategy games",
        # Music
        "rock bands", "pop stars albums", "hip hop albums", "country songs",
        "80s hits", "90s hits", "2000s hits", "one-hit wonders",
        # Food & Drink
        "breakfast cereals", "ice cream brands", "pizza chains", "coffee brands",
        "soft drinks", "energy drinks", "beer brands", "wine varieties",
        "chocolate brands", "chip brands", "cookie brands", "gum brands",
        # Products
        "car brands", "motorcycle brands", "phone brands", "laptop brands",
        "sneaker brands", "watch brands", "perfume brands", "makeup brands",
        "cleaning products", "household appliances", "power tools", "kitchen gadgets",
        # Other Things
        "sports leagues", "awards shows", "magazines", "newspapers",
        "comic book series", "board game classics", "children's toys from 90s",
        "famous artworks", "famous sculptures", "famous photographs"
    ],
    "place": [
        # Cities
        "European capital cities", "Asian megacities", "South American cities",
        "US state capitals", "famous resort towns", "historic European cities",
        # Natural
        "waterfalls", "volcanoes", "caves", "canyons", "coral reefs",
        "glaciers", "rainforests", "savannas", "archipelagos", "fjords",
        # Man-made
        "ancient ruins", "castles", "palaces", "cathedrals", "mosques",
        "temples", "skyscrapers", "opera houses", "libraries", "universities",
        # Entertainment
        "famous casinos", "famous hotels", "famous restaurants", "famous bars",
        "concert venues", "sports arenas", "race tracks", "golf courses",
        # Historical
        "battlefields", "colonial sites", "ancient wonders", "pilgrimage sites"
    ],
    "person": [
        # Sports
        "NFL quarterbacks", "NBA players", "soccer legends", "tennis champions",
        "golf legends", "boxing champions", "Olympic gold medalists", "F1 drivers",
        "baseball Hall of Famers", "hockey legends", "WWE wrestlers",
        # Entertainment
        "Oscar winners", "Grammy winners", "Broadway stars", "stand-up comedians",
        "talk show hosts", "news anchors", "voice actors", "child actors grown up",
        "reality TV stars", "YouTube stars", "TikTok stars",
        # Music
        "rock legends", "pop icons", "hip hop artists", "country stars",
        "classical composers", "jazz musicians", "DJs", "band frontmen",
        # Other
        "tech billionaires", "fashion designers", "celebrity chefs",
        "famous authors", "famous painters", "famous architects",
        "Nobel Prize winners", "world leaders current", "world leaders historical",
        "famous explorers", "famous philosophers", "famous mathematicians"
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
                    entity["source"] = "generated"
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
    parser = argparse.ArgumentParser(description="Generate annotated entities V2")
    parser.add_argument("--target", type=int, default=2500, help="Target total entities")
    parser.add_argument("--output", type=Path, default=Path("data/generated_entities_v2.json"))
    parser.add_argument("--existing", type=Path, nargs="+", help="Existing entity files")

    args = parser.parse_args()

    # Load existing entities
    existing_names = set()
    if args.existing:
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
