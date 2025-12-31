"""
Database Population Script - Load annotated entities into EntityRegistry.

Usage:
    python scripts/populate_db.py --input data/annotated_entities.json
"""

import sys
import json
import logging
from pathlib import Path
import argparse
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.entity_registry import EntityRegistry, Entity, EntityCategory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def populate_database(
    input_file: Path,
    db_path: Optional[Path] = None,
    skip_existing: bool = True
):
    """
    Populate EntityRegistry database from annotated JSON file.

    Args:
        input_file: Path to annotated entities JSON
        db_path: Optional custom database path
        skip_existing: Skip entities that already exist in database
    """
    # Load annotated entities
    logger.info(f"Loading entities from {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Handle both list format and dict with "entities" key
        if isinstance(data, list):
            entities = data
        else:
            entities = data.get("entities", data)

    logger.info(f"Found {len(entities)} entities to import")

    # Initialize registry
    registry = EntityRegistry(db_path)
    logger.info(f"Database initialized at {registry.db_path}")

    # Import entities
    added = 0
    skipped = 0
    failed = 0

    for entity_data in entities:
        try:
            name = entity_data["name"]
            category_str = entity_data["category"]

            # Map category string to enum
            category = EntityCategory(category_str)

            # Get metadata (with defaults for non-annotated)
            polysemy_triggers = entity_data.get("polysemy_triggers", [])
            clue_associations = entity_data.get("clue_associations", [])
            aliases = entity_data.get("aliases", [])

            # Calculate recency score (default 0.5, can be manually adjusted)
            recency_score = entity_data.get("recency_score", 0.5)

            # Create Entity object
            entity = Entity(
                canonical_name=name,
                aliases=aliases,
                category=category,
                polysemy_triggers=polysemy_triggers,
                clue_associations=clue_associations,
                recency_score=recency_score
            )

            # Check if exists
            if skip_existing:
                existing = registry.get_canonical_spelling(name)
                if existing:
                    logger.debug(f"Skipping existing: {name}")
                    skipped += 1
                    continue

            # Add to registry
            registry.add_entity(entity)
            added += 1

            if added % 50 == 0:
                logger.info(f"Progress: {added} entities added")

        except ValueError as e:
            if "already exists" in str(e):
                skipped += 1
            else:
                logger.error(f"Failed to add {entity_data.get('name', 'unknown')}: {e}")
                failed += 1
        except Exception as e:
            logger.error(f"Unexpected error for {entity_data.get('name', 'unknown')}: {e}")
            failed += 1

    # Summary
    logger.info("="*60)
    logger.info("DATABASE POPULATION COMPLETE")
    logger.info("="*60)
    logger.info(f"Total entities processed: {len(entities)}")
    logger.info(f"Successfully added: {added}")
    logger.info(f"Skipped (already exist): {skipped}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total in database: {registry.get_entity_count()}")
    logger.info("="*60)

    # Print category breakdown
    logger.info("\nCategory Breakdown:")
    for category in EntityCategory:
        count = registry.get_entity_count(category)
        logger.info(f"  {category.value.capitalize()}: {count}")

    registry.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Populate entity database")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input JSON file with annotated entities"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Custom database path (default: backend/app/data/entities.db)"
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing entities instead of skipping"
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"❌ Input file not found: {args.input}")
        return

    populate_database(
        input_file=args.input,
        db_path=args.db,
        skip_existing=not args.replace
    )

    print("\n✅ Database population complete!")


if __name__ == "__main__":
    from typing import Optional
    main()
