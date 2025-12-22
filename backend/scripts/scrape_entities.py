"""
Entity Scraper - Web scraping for pop culture entities.

Scrapes entities from multiple sources:
- IMDb (movies, TV shows)
- Wikipedia (landmarks, celebrities, brands)
- Manual curated lists (board games, food brands, viral memes)

Usage:
    python scripts/scrape_entities.py --source all --output data/scraped_entities.json
"""

import asyncio
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
import argparse
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EntityScraper:
    """
    Multi-source entity scraper with rate limiting and error handling.
    """

    # User agent to avoid blocking
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # Rate limiting (requests per second)
    RATE_LIMIT = 1.0  # 1 request per second

    def __init__(self):
        """Initialize scraper with HTTP client."""
        self.client = httpx.AsyncClient(
            headers={"User-Agent": self.USER_AGENT},
            timeout=30.0,
            follow_redirects=True
        )
        self.last_request_time = 0

    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.RATE_LIMIT

        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)

        self.last_request_time = time.time()

    async def scrape_wikipedia_landmarks(self, limit: int = 100) -> List[Dict]:
        """
        Scrape famous landmarks from Wikipedia.

        Args:
            limit: Maximum number of landmarks to scrape

        Returns:
            List of entity dictionaries
        """
        logger.info("Scraping Wikipedia landmarks...")

        # Wikipedia list of landmarks
        url = "https://en.wikipedia.org/wiki/List_of_landmarks"

        await self._rate_limit()

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            entities = []

            # Find all links in tables (landmarks are typically in tables)
            for table in soup.find_all('table', class_='wikitable'):
                for row in table.find_all('tr')[1:]:  # Skip header
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        # First cell usually contains landmark name
                        link = cells[0].find('a')
                        if link and link.get('title'):
                            name = link.get('title')
                            entities.append({
                                "name": name,
                                "category": "place",
                                "source": "wikipedia_landmarks"
                            })

                    if len(entities) >= limit:
                        break

                if len(entities) >= limit:
                    break

            logger.info(f"Scraped {len(entities)} landmarks from Wikipedia")
            return entities[:limit]

        except Exception as e:
            logger.error(f"Error scraping Wikipedia landmarks: {e}")
            return []

    def get_manual_curated_entities(self) -> List[Dict]:
        """
        Return manually curated high-probability trivia entities.

        Returns:
            List of entity dictionaries
        """
        logger.info("Loading manually curated entities...")

        entities = [
            # Board Games & Games
            {"name": "Monopoly", "category": "thing", "source": "manual"},
            {"name": "Scrabble", "category": "thing", "source": "manual"},
            {"name": "Chess", "category": "thing", "source": "manual"},
            {"name": "Checkers", "category": "thing", "source": "manual"},
            {"name": "Clue", "category": "thing", "source": "manual"},
            {"name": "Risk", "category": "thing", "source": "manual"},
            {"name": "Trivial Pursuit", "category": "thing", "source": "manual"},
            {"name": "Jenga", "category": "thing", "source": "manual"},
            {"name": "Connect Four", "category": "thing", "source": "manual"},
            {"name": "Battleship", "category": "thing", "source": "manual"},

            # Food & Snacks
            {"name": "Oreo", "category": "thing", "source": "manual"},
            {"name": "M&M's", "category": "thing", "source": "manual"},
            {"name": "Skittles", "category": "thing", "source": "manual"},
            {"name": "Pizza", "category": "thing", "source": "manual"},
            {"name": "Hamburger", "category": "thing", "source": "manual"},
            {"name": "Hot Dog", "category": "thing", "source": "manual"},
            {"name": "Birthday Cake", "category": "thing", "source": "manual"},
            {"name": "Ice Cream", "category": "thing", "source": "manual"},
            {"name": "Popcorn", "category": "thing", "source": "manual"},
            {"name": "S'mores", "category": "thing", "source": "manual"},
            {"name": "French Fries", "category": "thing", "source": "manual"},
            {"name": "Donut", "category": "thing", "source": "manual"},

            # Brands
            {"name": "Nike", "category": "thing", "source": "manual"},
            {"name": "Apple", "category": "thing", "source": "manual"},
            {"name": "Coca-Cola", "category": "thing", "source": "manual"},
            {"name": "McDonald's", "category": "thing", "source": "manual"},
            {"name": "Starbucks", "category": "thing", "source": "manual"},
            {"name": "Amazon", "category": "thing", "source": "manual"},
            {"name": "Google", "category": "thing", "source": "manual"},
            {"name": "Disney", "category": "thing", "source": "manual"},
            {"name": "Netflix", "category": "thing", "source": "manual"},

            # Sports & Activities
            {"name": "Bowling", "category": "thing", "source": "manual"},
            {"name": "Golf", "category": "thing", "source": "manual"},
            {"name": "Basketball", "category": "thing", "source": "manual"},
            {"name": "Football", "category": "thing", "source": "manual"},
            {"name": "Baseball", "category": "thing", "source": "manual"},
            {"name": "Tennis", "category": "thing", "source": "manual"},
            {"name": "Swimming", "category": "thing", "source": "manual"},
            {"name": "Pickleball", "category": "thing", "source": "manual"},

            # Famous Landmarks
            {"name": "Statue of Liberty", "category": "place", "source": "manual"},
            {"name": "Eiffel Tower", "category": "place", "source": "manual"},
            {"name": "Mt. Rushmore", "category": "place", "source": "manual"},
            {"name": "Grand Canyon", "category": "place", "source": "manual"},
            {"name": "Hollywood", "category": "place", "source": "manual"},
            {"name": "Times Square", "category": "place", "source": "manual"},
            {"name": "Golden Gate Bridge", "category": "place", "source": "manual"},
            {"name": "Big Ben", "category": "place", "source": "manual"},
            {"name": "Great Wall of China", "category": "place", "source": "manual"},

            # Classic Icons & Characters
            {"name": "Barbie", "category": "person", "source": "manual"},
            {"name": "Mickey Mouse", "category": "person", "source": "manual"},
            {"name": "Santa Claus", "category": "person", "source": "manual"},
            {"name": "Superman", "category": "person", "source": "manual"},
            {"name": "Batman", "category": "person", "source": "manual"},
            {"name": "Spider-Man", "category": "person", "source": "manual"},
            {"name": "Elsa", "category": "person", "source": "manual"},
            {"name": "Harry Potter", "category": "person", "source": "manual"},

            # Famous People (Contemporary)
            {"name": "Taylor Swift", "category": "person", "source": "manual"},
            {"name": "LeBron James", "category": "person", "source": "manual"},
            {"name": "Beyoncé", "category": "person", "source": "manual"},
            {"name": "Tom Cruise", "category": "person", "source": "manual"},
            {"name": "Oprah Winfrey", "category": "person", "source": "manual"},
            {"name": "Michael Jordan", "category": "person", "source": "manual"},
            {"name": "Paris Hilton", "category": "person", "source": "manual"},

            # Movies & Shows
            {"name": "Titanic", "category": "thing", "source": "manual"},
            {"name": "Star Wars", "category": "thing", "source": "manual"},
            {"name": "The Lion King", "category": "thing", "source": "manual"},
            {"name": "Frozen", "category": "thing", "source": "manual"},

            # Common Objects
            {"name": "Umbrella", "category": "thing", "source": "manual"},
            {"name": "Piano", "category": "thing", "source": "manual"},
            {"name": "Bicycle", "category": "thing", "source": "manual"},
            {"name": "Camera", "category": "thing", "source": "manual"},
            {"name": "Clock", "category": "thing", "source": "manual"},
            {"name": "Mirror", "category": "thing", "source": "manual"},
            {"name": "Candle", "category": "thing", "source": "manual"},
            {"name": "Book", "category": "thing", "source": "manual"},

            # Household Items
            {"name": "Toothbrush", "category": "thing", "source": "manual"},
            {"name": "Refrigerator", "category": "thing", "source": "manual"},
            {"name": "Television", "category": "thing", "source": "manual"},
            {"name": "Microwave", "category": "thing", "source": "manual"},

            # Animals (often used)
            {"name": "Elephant", "category": "thing", "source": "manual"},
            {"name": "Lion", "category": "thing", "source": "manual"},
            {"name": "Tiger", "category": "thing", "source": "manual"},
            {"name": "Eagle", "category": "thing", "source": "manual"},
        ]

        logger.info(f"Loaded {len(entities)} manually curated entities")
        return entities

    async def scrape_all(self, output_file: Optional[Path] = None) -> List[Dict]:
        """
        Scrape entities from all sources.

        Args:
            output_file: Optional path to save results

        Returns:
            Combined list of all scraped entities
        """
        all_entities = []

        # 1. Manual curated (highest quality)
        manual = self.get_manual_curated_entities()
        all_entities.extend(manual)

        # 2. Wikipedia landmarks (async)
        try:
            landmarks = await self.scrape_wikipedia_landmarks(limit=100)
            all_entities.extend(landmarks)
        except Exception as e:
            logger.error(f"Failed to scrape Wikipedia: {e}")

        # Deduplicate by name
        seen = set()
        unique_entities = []
        for entity in all_entities:
            name = entity["name"].lower()
            if name not in seen:
                seen.add(name)
                unique_entities.append(entity)

        logger.info(f"Total unique entities scraped: {len(unique_entities)}")

        # Save to file if specified
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "metadata": {
                        "scraped_at": datetime.now().isoformat(),
                        "total_entities": len(unique_entities),
                        "sources": ["manual", "wikipedia"]
                    },
                    "entities": unique_entities
                }, f, indent=2)
            logger.info(f"Saved entities to {output_file}")

        return unique_entities

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def main():
    """Main entry point for scraper."""
    parser = argparse.ArgumentParser(description="Scrape pop culture entities")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backend/app/data/scraped_entities.json"),
        help="Output JSON file path"
    )
    parser.add_argument(
        "--source",
        choices=["all", "manual", "wikipedia"],
        default="all",
        help="Data source to scrape"
    )

    args = parser.parse_args()

    scraper = EntityScraper()

    try:
        if args.source == "manual":
            entities = scraper.get_manual_curated_entities()
        else:
            entities = await scraper.scrape_all(args.output)

        print(f"\n✅ Scraping complete!")
        print(f"Total entities: {len(entities)}")
        print(f"Saved to: {args.output}")

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
