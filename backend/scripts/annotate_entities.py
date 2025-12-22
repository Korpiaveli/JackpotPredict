"""
AI Entity Annotator - Generate polysemy triggers and clue associations using Claude API.

This script uses Claude to automatically generate rich metadata for entities:
- Polysemy triggers (dual meanings)
- Clue associations (likely game show clue patterns)
- Aliases (alternative names)

Usage:
    python scripts/annotate_entities.py --input data/scraped_entities.json --output data/annotated_entities.json
"""

import asyncio
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
import argparse
from datetime import datetime
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EntityAnnotator:
    """
    AI-powered entity annotation using Claude API.

    Generates:
    - polysemy_triggers: Words with dual meanings related to entity
    - clue_associations: Common trivia clue patterns
    - aliases: Alternative names/spellings
    """

    ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

    # Annotation prompt template
    ANNOTATION_PROMPT = """You are a trivia game expert helping to annotate entities for a game show prediction system.

For the entity "{entity_name}" (category: {category}), generate:

1. **Polysemy Triggers** (5 items): Words or phrases with dual meanings that could be used in cryptic clues. Think puns and wordplay.
   - Example for "Paris Hilton": ["romantic city", "hotel chain", "basic", "simple life"]
   - Example for "Monopoly": ["flavors/editions", "market control", "property game", "go around"]

2. **Clue Associations** (5-7 items): Common phrases or patterns that might appear in trivia clues about this entity.
   - Example for "Paris Hilton": ["hospitality", "reality TV", "2000s icon", "DJ", "that's hot"]
   - Example for "Bowling": ["strikes", "gutters", "pins", "ten pins", "success and failure"]

3. **Aliases** (3-5 items): Alternative names, nicknames, or spellings.
   - Example for "Mt. Rushmore": ["Mount Rushmore", "Rushmore"]
   - Example for "M&M's": ["M&Ms", "M and Ms", "Eminem candy"]

Respond ONLY with valid JSON in this exact format:
{{
  "polysemy_triggers": ["item1", "item2", "item3", "item4", "item5"],
  "clue_associations": ["item1", "item2", "item3", "item4", "item5"],
  "aliases": ["item1", "item2", "item3"]
}}

Focus on what would make GOOD TRIVIA CLUES - think wordplay, puns, and cultural references."""

    def __init__(self, api_key: Optional[str] = None, rate_limit: float = 0.2):
        """
        Initialize annotator with Claude API.

        Args:
            api_key: Anthropic API key (or from ANTHROPIC_API_KEY env var)
            rate_limit: Requests per second (default 0.2 = 5 req/sec, well under limit)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment or constructor")

        self.client = httpx.AsyncClient(
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            timeout=60.0
        )

        self.rate_limit = rate_limit
        self.last_request_time = 0

    async def _rate_limit_wait(self):
        """Enforce rate limiting."""
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.rate_limit

        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)

        self.last_request_time = time.time()

    async def annotate_entity(
        self,
        entity_name: str,
        category: str
    ) -> Optional[Dict]:
        """
        Generate annotations for a single entity using Claude API.

        Args:
            entity_name: Name of the entity
            category: Entity category (thing/place/person)

        Returns:
            Dictionary with polysemy_triggers, clue_associations, aliases
        """
        await self._rate_limit_wait()

        # Build prompt
        prompt = self.ANNOTATION_PROMPT.format(
            entity_name=entity_name,
            category=category
        )

        # Call Claude API
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        try:
            logger.info(f"Annotating: {entity_name}")
            response = await self.client.post(self.ANTHROPIC_API_URL, json=payload)
            response.raise_for_status()

            data = response.json()
            content = data["content"][0]["text"]

            # Parse JSON from response
            # Sometimes Claude wraps in markdown code blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            annotations = json.loads(content)

            # Validate structure
            required_keys = ["polysemy_triggers", "clue_associations", "aliases"]
            if not all(key in annotations for key in required_keys):
                logger.warning(f"Invalid annotation structure for {entity_name}")
                return None

            logger.info(f"✓ Annotated: {entity_name}")
            return annotations

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error for {entity_name}: {e}")
            logger.debug(f"Response content: {content}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"API error for {entity_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {entity_name}: {e}")
            return None

    async def annotate_batch(
        self,
        entities: List[Dict],
        max_concurrent: int = 3
    ) -> List[Dict]:
        """
        Annotate multiple entities with concurrency control.

        Args:
            entities: List of entity dicts with 'name' and 'category'
            max_concurrent: Maximum concurrent API calls

        Returns:
            List of annotated entities
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        annotated_entities = []

        async def annotate_with_semaphore(entity: Dict) -> Dict:
            async with semaphore:
                annotations = await self.annotate_entity(
                    entity["name"],
                    entity["category"]
                )

                if annotations:
                    return {
                        **entity,
                        "polysemy_triggers": annotations["polysemy_triggers"],
                        "clue_associations": annotations["clue_associations"],
                        "aliases": annotations["aliases"],
                        "annotated": True
                    }
                else:
                    # Failed annotation - return with defaults
                    return {
                        **entity,
                        "polysemy_triggers": [],
                        "clue_associations": [],
                        "aliases": [],
                        "annotated": False
                    }

        # Create tasks for all entities
        tasks = [annotate_with_semaphore(entity) for entity in entities]

        # Execute with progress tracking
        for i, task in enumerate(asyncio.as_completed(tasks), 1):
            result = await task
            annotated_entities.append(result)

            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(entities)} entities annotated")

        return annotated_entities

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def main():
    """Main entry point for annotator."""
    parser = argparse.ArgumentParser(description="Annotate entities with AI")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input JSON file with scraped entities"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output JSON file for annotated entities"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of entities to annotate (for testing)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip entities that are already annotated"
    )

    args = parser.parse_args()

    # Load input entities
    if not args.input.exists():
        print(f"❌ Input file not found: {args.input}")
        return

    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)
        entities = data.get("entities", data)  # Handle both formats

    logger.info(f"Loaded {len(entities)} entities from {args.input}")

    # Filter if limit specified
    if args.limit:
        entities = entities[:args.limit]
        logger.info(f"Limited to {args.limit} entities")

    # Filter out already annotated if skip_existing
    if args.skip_existing:
        entities = [e for e in entities if not e.get("annotated", False)]
        logger.info(f"Skipping already annotated, {len(entities)} remaining")

    # Initialize annotator
    try:
        annotator = EntityAnnotator()
    except ValueError as e:
        print(f"❌ {e}")
        print("Set ANTHROPIC_API_KEY environment variable or use .env file")
        return

    try:
        # Annotate entities
        print(f"\n🤖 Starting AI annotation with Claude API...")
        print(f"Entities to annotate: {len(entities)}")
        print(f"Estimated time: ~{len(entities) * 5} seconds (with rate limiting)\n")

        annotated = await annotator.annotate_batch(entities, max_concurrent=3)

        # Save results
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "annotated_at": datetime.now().isoformat(),
                    "total_entities": len(annotated),
                    "successfully_annotated": sum(1 for e in annotated if e.get("annotated", False))
                },
                "entities": annotated
            }, f, indent=2)

        successful = sum(1 for e in annotated if e.get("annotated", False))
        print(f"\n✅ Annotation complete!")
        print(f"Successfully annotated: {successful}/{len(annotated)}")
        print(f"Saved to: {args.output}")

    finally:
        await annotator.close()


if __name__ == "__main__":
    asyncio.run(main())
