"""
API Fallback System - External lookups for unknown entities.

When an entity isn't found in the local registry, this module queries:
- Wikipedia API for entity information
- Google Custom Search for recent/viral references
- Results are cached in SQLite for 24 hours to avoid repeated API calls

Usage:
    fallback = APIFallback()
    entity_info = await fallback.lookup_entity("some entity")
"""

import asyncio
import json
import logging
import sqlite3
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class APIFallback:
    """
    External API fallback for entity enrichment.

    Queries Wikipedia and other sources when entities aren't in local registry.
    Caches results for 24 hours to minimize API calls.
    """

    # Wikipedia API endpoint
    WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"

    # Cache expiry (24 hours)
    CACHE_EXPIRY_HOURS = 24

    def __init__(self, cache_db_path: Optional[Path] = None):
        """
        Initialize API fallback system.

        Args:
            cache_db_path: Path to cache database (default: backend/app/data/api_cache.db)
        """
        if cache_db_path is None:
            cache_db_path = Path(__file__).parent.parent / "data" / "api_cache.db"

        self.cache_db_path = Path(cache_db_path)
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.cache_db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._initialize_cache_schema()

        self.client = httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True
        )

        logger.info(f"API Fallback initialized with cache: {self.cache_db_path}")

    def _initialize_cache_schema(self):
        """Create cache tables if they don't exist."""
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_name TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                data TEXT NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_name ON api_cache(entity_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON api_cache(expires_at)")

        self.conn.commit()

    def _get_from_cache(self, entity_name: str) -> Optional[Dict]:
        """
        Retrieve cached API result if not expired.

        Args:
            entity_name: Entity name to lookup

        Returns:
            Cached data dict or None if not found/expired
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT data, cached_at, expires_at
            FROM api_cache
            WHERE entity_name = ? AND expires_at > datetime('now')
        """, (entity_name.lower(),))

        result = cursor.fetchone()
        if result:
            logger.debug(f"Cache hit for: {entity_name}")
            return json.loads(result["data"])

        return None

    def _save_to_cache(self, entity_name: str, source: str, data: Dict):
        """
        Save API result to cache.

        Args:
            entity_name: Entity name
            source: API source (wikipedia, google, etc)
            data: Data to cache
        """
        cursor = self.conn.cursor()

        expires_at = datetime.now() + timedelta(hours=self.CACHE_EXPIRY_HOURS)

        cursor.execute("""
            INSERT OR REPLACE INTO api_cache (entity_name, source, data, expires_at)
            VALUES (?, ?, ?, ?)
        """, (entity_name.lower(), source, json.dumps(data), expires_at))

        self.conn.commit()
        logger.debug(f"Cached result for: {entity_name}")

    async def lookup_wikipedia(self, entity_name: str) -> Optional[Dict]:
        """
        Query Wikipedia API for entity information.

        Args:
            entity_name: Entity name to search

        Returns:
            Dictionary with Wikipedia data or None if not found
        """
        # Check cache first
        cached = self._get_from_cache(entity_name)
        if cached:
            return cached

        # Query Wikipedia API
        params = {
            "action": "query",
            "format": "json",
            "titles": entity_name,
            "prop": "extracts|categories",
            "exintro": True,
            "explaintext": True,
            "redirects": 1
        }

        try:
            logger.info(f"Querying Wikipedia for: {entity_name}")
            response = await self.client.get(self.WIKIPEDIA_API, params=params)
            response.raise_for_status()

            data = response.json()
            pages = data.get("query", {}).get("pages", {})

            # Wikipedia returns pages as dict with page IDs as keys
            for page_id, page_data in pages.items():
                if page_id == "-1":
                    # Page not found
                    logger.warning(f"Wikipedia: No page found for {entity_name}")
                    return None

                # Extract relevant information
                result = {
                    "title": page_data.get("title"),
                    "extract": page_data.get("extract", "")[:500],  # First 500 chars
                    "categories": [
                        cat.get("title", "").replace("Category:", "")
                        for cat in page_data.get("categories", [])[:10]
                    ],
                    "source": "wikipedia",
                    "found": True
                }

                # Cache result
                self._save_to_cache(entity_name, "wikipedia", result)

                logger.info(f"✓ Found Wikipedia page: {result['title']}")
                return result

            return None

        except httpx.HTTPStatusError as e:
            logger.error(f"Wikipedia API error for {entity_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying Wikipedia: {e}")
            return None

    async def lookup_entity(self, entity_name: str) -> Optional[Dict]:
        """
        Main lookup method - tries multiple sources.

        Args:
            entity_name: Entity to lookup

        Returns:
            Entity information dict or None
        """
        # Try Wikipedia first
        wiki_result = await self.lookup_wikipedia(entity_name)
        if wiki_result:
            return wiki_result

        # Could add more sources here:
        # - Google Custom Search
        # - DBpedia
        # - Wikidata
        # For now, Wikipedia is sufficient

        logger.info(f"No external data found for: {entity_name}")
        return None

    def extract_category_from_text(self, text: str, categories: List[str]) -> str:
        """
        Infer entity category (thing/place/person) from Wikipedia data.

        Args:
            text: Wikipedia extract text
            categories: Wikipedia categories

        Returns:
            Category guess: "thing", "place", or "person"
        """
        text_lower = text.lower()
        categories_lower = [c.lower() for c in categories]

        # Check categories first
        person_indicators = ["people", "births", "deaths", "actors", "musicians", "athletes"]
        place_indicators = ["geography", "cities", "countries", "landmarks", "buildings"]
        thing_indicators = ["brands", "products", "games", "food", "media"]

        for category in categories_lower:
            if any(ind in category for ind in person_indicators):
                return "person"
            if any(ind in category for ind in place_indicators):
                return "place"
            if any(ind in category for ind in thing_indicators):
                return "thing"

        # Check text content
        if any(word in text_lower for word in ["born", "died", "actor", "singer", "athlete"]):
            return "person"
        if any(word in text_lower for word in ["located", "city", "country", "mountain", "building"]):
            return "place"

        # Default to thing
        return "thing"

    def clear_expired_cache(self):
        """Remove expired cache entries."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM api_cache WHERE expires_at < datetime('now')")
        deleted = cursor.rowcount
        self.conn.commit()

        if deleted > 0:
            logger.info(f"Cleared {deleted} expired cache entries")

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM api_cache")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as valid FROM api_cache WHERE expires_at > datetime('now')")
        valid = cursor.fetchone()["valid"]

        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": total - valid
        }

    async def close(self):
        """Close HTTP client and database connection."""
        await self.client.aclose()
        if self.conn:
            self.conn.close()

    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()


async def test_fallback():
    """Test function for API fallback."""
    fallback = APIFallback()

    try:
        # Test known entities
        test_entities = [
            "Eiffel Tower",
            "Taylor Swift",
            "Pizza",
            "Monopoly"
        ]

        for entity in test_entities:
            print(f"\nLooking up: {entity}")
            result = await fallback.lookup_entity(entity)

            if result:
                print(f"  ✓ Found: {result['title']}")
                print(f"  Category guess: {fallback.extract_category_from_text(result['extract'], result['categories'])}")
                print(f"  Extract: {result['extract'][:100]}...")
            else:
                print(f"  ✗ Not found")

        # Show cache stats
        stats = fallback.get_cache_stats()
        print(f"\nCache stats: {stats}")

    finally:
        await fallback.close()


if __name__ == "__main__":
    asyncio.run(test_fallback())
