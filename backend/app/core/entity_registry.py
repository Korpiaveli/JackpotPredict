"""
Entity Registry - Core database for pop culture entities with semantic search.

This module manages the 10,000+ entity database with canonical spellings,
aliases, polysemy triggers, and clue associations for trivia prediction.
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)


class EntityCategory(str, Enum):
    """Entity category enumeration following 60/25/15 distribution."""
    THING = "thing"      # 60% - Objects, brands, games, food
    PLACE = "place"      # 25% - Landmarks, locations
    PERSON = "person"    # 15% - Celebrities, characters


@dataclass
class Entity:
    """
    Entity data model with all semantic metadata.

    Attributes:
        canonical_name: Exact spelling required for game submission
        aliases: Alternative names/spellings for matching
        category: thing/place/person classification
        polysemy_triggers: Words with dual meanings related to entity
        clue_associations: Common clue patterns/phrases
        recency_score: Cultural relevance (0-1, higher = more recent/viral)
    """
    canonical_name: str
    aliases: List[str]
    category: EntityCategory
    polysemy_triggers: List[str]
    clue_associations: List[str]
    recency_score: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "canonical_name": self.canonical_name,
            "aliases": self.aliases,
            "category": self.category.value,
            "polysemy_triggers": self.polysemy_triggers,
            "clue_associations": self.clue_associations,
            "recency_score": self.recency_score
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """Create Entity from dictionary."""
        return cls(
            canonical_name=data["canonical_name"],
            aliases=data["aliases"],
            category=EntityCategory(data["category"]),
            polysemy_triggers=data["polysemy_triggers"],
            clue_associations=data["clue_associations"],
            recency_score=data.get("recency_score", 0.5)
        )


class EntityRegistry:
    """
    High-performance entity database with semantic search capabilities.

    Uses SQLite for persistence and TF-IDF for keyword similarity matching.
    Optimized for <100ms query time on 10K+ entities.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize entity registry.

        Args:
            db_path: Path to SQLite database file. Defaults to backend/app/data/entities.db
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "entities.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._initialize_schema()
        self._vectorizer = None
        self._entity_cache = {}

        logger.info(f"EntityRegistry initialized with database: {self.db_path}")

    def _initialize_schema(self):
        """Create database tables and indexes if they don't exist."""
        cursor = self.conn.cursor()

        # Main entities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_name TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                recency_score REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Aliases table (many-to-one with entities)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL,
                alias TEXT NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
            )
        """)

        # Polysemy triggers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS polysemy_triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL,
                trigger TEXT NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
            )
        """)

        # Clue associations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clue_associations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL,
                association TEXT NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for fast lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_canonical_name ON entities(canonical_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON entities(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recency ON entities(recency_score DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_aliases ON aliases(alias)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_triggers ON polysemy_triggers(trigger)")

        # Full-text search index for clue associations
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS clue_associations_fts
            USING fts5(entity_id, association)
        """)

        self.conn.commit()
        logger.debug("Database schema initialized")

    def add_entity(self, entity: Entity) -> int:
        """
        Add entity to registry with validation.

        Args:
            entity: Entity object to add

        Returns:
            entity_id: Database ID of inserted entity

        Raises:
            ValueError: If canonical_name already exists
        """
        cursor = self.conn.cursor()

        try:
            # Insert main entity record
            cursor.execute("""
                INSERT INTO entities (canonical_name, category, recency_score)
                VALUES (?, ?, ?)
            """, (entity.canonical_name, entity.category.value, entity.recency_score))

            entity_id = cursor.lastrowid

            # Insert aliases
            for alias in entity.aliases:
                cursor.execute("""
                    INSERT INTO aliases (entity_id, alias) VALUES (?, ?)
                """, (entity_id, alias))

            # Insert polysemy triggers
            for trigger in entity.polysemy_triggers:
                cursor.execute("""
                    INSERT INTO polysemy_triggers (entity_id, trigger) VALUES (?, ?)
                """, (entity_id, trigger))

            # Insert clue associations
            for association in entity.clue_associations:
                cursor.execute("""
                    INSERT INTO clue_associations (entity_id, association) VALUES (?, ?)
                """, (entity_id, association))

                # Also add to FTS index
                cursor.execute("""
                    INSERT INTO clue_associations_fts (entity_id, association)
                    VALUES (?, ?)
                """, (entity_id, association))

            self.conn.commit()
            self._entity_cache[entity.canonical_name] = entity

            logger.debug(f"Added entity: {entity.canonical_name} (ID: {entity_id})")
            return entity_id

        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            raise ValueError(f"Entity '{entity.canonical_name}' already exists") from e

    def get_canonical_spelling(self, name: str) -> Optional[str]:
        """
        Get exact canonical spelling for an entity name or alias.

        Args:
            name: Entity name or alias (case-insensitive)

        Returns:
            Canonical name if found, None otherwise
        """
        cursor = self.conn.cursor()

        # First check exact match on canonical name
        cursor.execute("""
            SELECT canonical_name FROM entities
            WHERE LOWER(canonical_name) = LOWER(?)
        """, (name,))

        result = cursor.fetchone()
        if result:
            return result["canonical_name"]

        # Check aliases
        cursor.execute("""
            SELECT e.canonical_name
            FROM entities e
            JOIN aliases a ON e.id = a.entity_id
            WHERE LOWER(a.alias) = LOWER(?)
        """, (name,))

        result = cursor.fetchone()
        return result["canonical_name"] if result else None

    def search_by_keywords(
        self,
        keywords: List[str],
        category: Optional[EntityCategory] = None,
        top_k: int = 10,
        min_score: float = 0.1
    ) -> List[Tuple[Entity, float]]:
        """
        Search entities by keyword similarity using TF-IDF.

        Args:
            keywords: List of keywords from clue analysis
            category: Optional category filter
            top_k: Maximum number of results
            min_score: Minimum similarity score threshold

        Returns:
            List of (Entity, similarity_score) tuples, sorted by score descending
        """
        # Get all entities with optional category filter
        entities = self._get_all_entities(category)

        if not entities:
            return []

        # Build search corpus from entity metadata
        entity_texts = []
        for entity in entities:
            # Extract individual words from canonical name for better matching
            # e.g., "Eiffel Tower" -> adds both "Eiffel" and "Tower" as separate terms
            # This ensures "eiffel" query matches "Eiffel Tower" strongly
            name_words = entity.canonical_name.split()

            # Extract words from aliases too
            alias_words = []
            for alias in entity.aliases:
                alias_words.extend(alias.split())

            # Combine all searchable fields with name words emphasized
            text_parts = [
                entity.canonical_name,
                *name_words,  # Individual name components for better TF-IDF matching
                *entity.aliases,
                *alias_words,  # Individual alias components
                *entity.polysemy_triggers,
                *entity.clue_associations
            ]
            entity_texts.append(" ".join(text_parts))

        # Create query from keywords
        query = " ".join(keywords)

        # Compute TF-IDF similarity
        vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),  # Unigrams and bigrams
            max_features=5000
        )

        try:
            corpus = entity_texts + [query]
            tfidf_matrix = vectorizer.fit_transform(corpus)

            # Last vector is the query
            query_vec = tfidf_matrix[-1]
            entity_vecs = tfidf_matrix[:-1]

            # Compute cosine similarity
            similarities = cosine_similarity(query_vec, entity_vecs).flatten()

            # Create results with recency boost
            results = []
            for i, (entity, score) in enumerate(zip(entities, similarities)):
                if score >= min_score:
                    # Boost score by recency (max 20% boost)
                    boosted_score = score * (1 + 0.2 * entity.recency_score)
                    results.append((entity, float(boosted_score)))

            # Sort by score descending
            results.sort(key=lambda x: x[1], reverse=True)

            return results[:top_k]

        except ValueError as e:
            logger.warning(f"TF-IDF search failed: {e}")
            return []

    def _get_all_entities(self, category: Optional[EntityCategory] = None) -> List[Entity]:
        """
        Load all entities from database with optional category filter.

        Args:
            category: Optional category filter

        Returns:
            List of Entity objects
        """
        cursor = self.conn.cursor()

        # Base query
        if category:
            cursor.execute("""
                SELECT id, canonical_name, category, recency_score
                FROM entities
                WHERE category = ?
                ORDER BY recency_score DESC
            """, (category.value,))
        else:
            cursor.execute("""
                SELECT id, canonical_name, category, recency_score
                FROM entities
                ORDER BY recency_score DESC
            """)

        entities = []
        for row in cursor.fetchall():
            entity_id = row["id"]
            canonical_name = row["canonical_name"]

            # Check cache first
            if canonical_name in self._entity_cache:
                entities.append(self._entity_cache[canonical_name])
                continue

            # Load related data
            aliases = self._get_aliases(entity_id)
            triggers = self._get_polysemy_triggers(entity_id)
            associations = self._get_clue_associations(entity_id)

            entity = Entity(
                canonical_name=canonical_name,
                aliases=aliases,
                category=EntityCategory(row["category"]),
                polysemy_triggers=triggers,
                clue_associations=associations,
                recency_score=row["recency_score"]
            )

            self._entity_cache[canonical_name] = entity
            entities.append(entity)

        return entities

    def _get_aliases(self, entity_id: int) -> List[str]:
        """Get all aliases for an entity."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT alias FROM aliases WHERE entity_id = ?", (entity_id,))
        return [row["alias"] for row in cursor.fetchall()]

    def _get_polysemy_triggers(self, entity_id: int) -> List[str]:
        """Get all polysemy triggers for an entity."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT trigger FROM polysemy_triggers WHERE entity_id = ?", (entity_id,))
        return [row["trigger"] for row in cursor.fetchall()]

    def _get_clue_associations(self, entity_id: int) -> List[str]:
        """Get all clue associations for an entity."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT association FROM clue_associations WHERE entity_id = ?", (entity_id,))
        return [row["association"] for row in cursor.fetchall()]

    def get_entity_count(self, category: Optional[EntityCategory] = None) -> int:
        """
        Get total entity count with optional category filter.

        Args:
            category: Optional category filter

        Returns:
            Entity count
        """
        cursor = self.conn.cursor()

        if category:
            cursor.execute("SELECT COUNT(*) as count FROM entities WHERE category = ?",
                         (category.value,))
        else:
            cursor.execute("SELECT COUNT(*) as count FROM entities")

        return cursor.fetchone()["count"]

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("EntityRegistry closed")

    def __del__(self):
        """Cleanup on deletion."""
        self.close()
