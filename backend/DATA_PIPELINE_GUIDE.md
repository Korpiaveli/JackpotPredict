# Data Pipeline Guide

This guide explains how to populate the entity database with 500-1,000+ trivia answers.

## Quick Start (Recommended for Testing)

The fastest way to get started with 90+ entities:

```bash
# 1. Activate virtual environment
cd backend
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 2. Run the entity scraper (creates scraped_entities.json)
python scripts/scrape_entities.py --output app/data/scraped_entities.json

# 3. Populate database directly (uses manual curated entities)
python scripts/populate_db.py --input app/data/scraped_entities.json
```

This gives you **90+ high-quality entities** immediately, including:
- Board games (Monopoly, Scrabble, Chess, etc.)
- Famous landmarks (Eiffel Tower, Mt. Rushmore, etc.)
- Celebrities (Taylor Swift, LeBron James, Paris Hilton, etc.)
- Food/brands (Oreo, M&M's, Pizza, Nike, etc.)

## Full Pipeline (500-1,000+ Entities with AI Annotation)

For production-level coverage:

### Step 1: Scrape Entities

```bash
python scripts/scrape_entities.py \
  --source all \
  --output app/data/scraped_entities.json
```

This scrapes:
- 90+ manually curated high-probability entities
- 100+ Wikipedia landmarks
- Total: ~190 entities

### Step 2: AI Annotation (Requires Anthropic API Key)

Set your API key:
```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY="your-api-key-here"

# Windows CMD
set ANTHROPIC_API_KEY=your-api-key-here

# Linux/Mac
export ANTHROPIC_API_KEY=your-api-key-here
```

Or create a `.env` file in `backend/`:
```
ANTHROPIC_API_KEY=your-api-key-here
```

Then run annotation:
```bash
python scripts/annotate_entities.py \
  --input app/data/scraped_entities.json \
  --output app/data/annotated_entities.json \
  --limit 50  # Start with 50 for testing
```

**Cost Estimate:**
- ~$0.50-1.00 per 100 entities using Claude 3.5 Sonnet
- 500 entities ≈ $2.50-5.00
- Rate limited to 5 req/sec (respects API limits)

**Time Estimate:**
- ~5 seconds per entity with rate limiting
- 100 entities ≈ 8-10 minutes
- 500 entities ≈ 40-50 minutes

### Step 3: Populate Database

```bash
python scripts/populate_db.py \
  --input app/data/annotated_entities.json
```

This imports all annotated entities into SQLite with:
- Canonical spellings
- Polysemy triggers (for dual-meaning detection)
- Clue associations (for pattern matching)
- Aliases (for fuzzy matching)

## Entity Database Structure

Each entity includes:

```json
{
  "name": "Paris Hilton",
  "category": "person",
  "polysemy_triggers": [
    "romantic city",
    "hotel chain",
    "basic",
    "simple life"
  ],
  "clue_associations": [
    "hospitality",
    "reality TV",
    "2000s icon",
    "DJ",
    "that's hot"
  ],
  "aliases": [
    "Paris",
    "Hilton"
  ],
  "recency_score": 0.7
}
```

## Performance Considerations

### Entity Count vs Response Time

| Entities | Search Time | Notes |
|----------|-------------|-------|
| 100 | <10ms | Instant |
| 500 | <50ms | Very fast |
| 1,000 | <100ms | Fast (within budget) |
| 5,000 | <200ms | Good (SQLite FTS indexed) |
| 10,000 | <300ms | Acceptable (still under 2s budget) |

**Recommendation: 500-1,000 entities is the sweet spot**
- Covers most probable trivia answers
- Fast search performance
- Manageable annotation cost/time

### Why More Entities = Better Predictions

1. **Coverage**: More candidates means higher chance the correct answer is in the database
2. **Semantic Search**: TF-IDF finds best matches even with 10K+ candidates
3. **Bayesian Filtering**: Narrows from many candidates to top 3 efficiently
4. **No Training Needed**: This isn't ML training - just answer lookup

## Expanding Beyond 190 Entities

### Option 1: Add More Manual Entities

Edit `scripts/scrape_entities.py` and add to `get_manual_curated_entities()`:

```python
# Add to the entities list:
{"name": "Your Entity", "category": "thing", "source": "manual"},
```

Categories:
- `thing` - Objects, games, food, brands (60% of answers)
- `place` - Landmarks, cities, locations (25% of answers)
- `person` - Celebrities, characters (15% of answers)

### Option 2: Use Gemini for Bulk Generation

Use the Gemini CLI for parallel entity generation:

```bash
gemini -p "Generate 200 high-probability trivia answers from 2024-2025 pop culture. Include:
- Recent movies/TV shows
- Viral trends
- Popular brands
- Famous landmarks
- A-list celebrities
Format as JSON array with name, category (thing/place/person)"
```

Save output and process with annotate_entities.py

### Option 3: Scrape Additional Sources

Enhance `scrape_entities.py` with:
- IMDb API (movies/shows)
- Spotify API (artists)
- Wikipedia category pages (games, foods, etc.)

## Testing the Database

After population, test the system:

```bash
# CLI interface
python -m app.main

# Or run the Monopoly test
>>> test
```

Expected results:
- Clue 1: Monopoly should appear in top 5
- Clue 2: Monopoly should appear in top 3
- Clue 3: Monopoly should be #1 with >75% confidence

## Database Statistics

Check entity counts:

```python
from app.core.entity_registry import EntityRegistry

registry = EntityRegistry()
print(f"Total entities: {registry.get_entity_count()}")
print(f"Things: {registry.get_entity_count(EntityCategory.THING)}")
print(f"Places: {registry.get_entity_count(EntityCategory.PLACE)}")
print(f"People: {registry.get_entity_count(EntityCategory.PERSON)}")
```

## Troubleshooting

### "Entity already exists" errors
Use `--replace` flag to update existing entities:
```bash
python scripts/populate_db.py --input data.json --replace
```

### API rate limiting
The annotator automatically handles rate limiting (5 req/sec). If you get 429 errors:
1. Check your API quota
2. Reduce concurrency in annotate_entities.py (default: 3)

### spaCy model not found
```bash
python -m spacy download en_core_web_lg
```

## Best Practices

1. **Start Small**: Test with 50-100 entities before scaling to 500+
2. **Validate Quality**: Manually review first 10-20 AI annotations
3. **Incremental Growth**: Add entities in batches of 100-200
4. **Category Balance**: Aim for 60% thing, 25% place, 15% person
5. **Recency Matters**: Recent (2024-2025) pop culture gets higher scores

## Next Steps

Once you have 500+ entities:
1. Test CLI with various clues
2. Verify top predictions are sensible
3. Tune Bayesian weights if needed (in `bayesian_updater.py`)
4. Move to Phase 3: Build FastAPI + Frontend
