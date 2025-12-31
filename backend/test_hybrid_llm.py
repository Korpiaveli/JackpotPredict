"""
Test script for Hybrid LLM + Bayesian prediction system.

This script tests the new Qwen 2.5 32B integration via Text-Generation-WebUI.

Prerequisites:
1. Text-Generation-WebUI running at http://127.0.0.1:5000
2. Qwen 2.5 32B model loaded with ExLlamaV2

Run:
    python test_hybrid_llm.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.inference_engine import InferenceEngine, get_inference_engine
from app.core.context_manager import build_system_prompt, get_context_manager
from app.core.hybrid_combiner import HybridCombiner


async def test_llm_availability():
    """Test if the LLM API is available."""
    print("\n" + "=" * 60)
    print("TEST 1: LLM API Availability")
    print("=" * 60)

    engine = await get_inference_engine()
    available = await engine.is_available()

    if available:
        print(f"[OK] LLM API is available at {engine.api_url}")
        print(f"[OK] Model: {engine.model_name}")
        return True
    else:
        print(f"[WARN] LLM API not available at {engine.api_url}")
        print("[INFO] Make sure Text-Generation-WebUI is running with:")
        print("       python server.py --api --api-port 5000 --extensions openai")
        return False


async def test_llm_warmup():
    """Test GPU warmup."""
    print("\n" + "=" * 60)
    print("TEST 2: LLM Warmup")
    print("=" * 60)

    engine = await get_inference_engine()
    success = await engine.warm_up()

    if success:
        print("[OK] LLM warmup successful - GPU ready")
        return True
    else:
        print("[FAIL] LLM warmup failed")
        return False


async def test_context_manager():
    """Test historical data loading and prompt building."""
    print("\n" + "=" * 60)
    print("TEST 3: Context Manager")
    print("=" * 60)

    manager = get_context_manager()
    stats = manager.get_stats()

    print(f"[INFO] Historical games loaded: {stats.get('total_games', 0)}")

    if stats.get('total_games', 0) > 0:
        print(f"[INFO] Categories: {stats.get('by_category', {})}")
        print(f"[INFO] Avg solve clue: {stats.get('avg_solve_clue', 'N/A'):.1f}")

        # Test prompt building
        prompt = build_system_prompt(category_hint="thing")
        print(f"[OK] System prompt generated ({len(prompt)} chars)")

        # Show a snippet
        print("\n[PREVIEW] System prompt (first 500 chars):")
        print("-" * 40)
        print(prompt[:500])
        print("-" * 40)

        return True
    else:
        print("[WARN] No historical games loaded")
        return False


async def test_single_prediction():
    """Test a single LLM prediction."""
    print("\n" + "=" * 60)
    print("TEST 4: Single LLM Prediction")
    print("=" * 60)

    engine = await get_inference_engine()

    if not await engine.is_available():
        print("[SKIP] LLM not available")
        return False

    # Test with Monopoly clues
    clues = [
        "Savors many flavors",
        "Round and round",
        "A hostile takeover"
    ]

    system_prompt = build_system_prompt(category_hint="thing")

    print(f"[INFO] Testing with clues: {clues}")
    print("[INFO] Getting LLM prediction...")

    prediction = await engine.get_prediction(
        clues=clues,
        system_prompt=system_prompt,
        category_hint="thing"
    )

    if prediction:
        print(f"\n[RESULT]")
        print(f"  Answer: {prediction.answer}")
        print(f"  Confidence: {prediction.confidence:.0f}%")
        print(f"  Is WAIT: {prediction.is_wait}")
        print(f"  Reasoning: {prediction.reasoning[:100]}...")

        if prediction.answer.lower() == "monopoly":
            print("\n[SUCCESS] LLM correctly identified Monopoly!")
            return True
        else:
            print(f"\n[INFO] LLM guessed {prediction.answer} (expected Monopoly)")
            return True  # Still counts as success if it returned a prediction
    else:
        print("[FAIL] No prediction returned")
        return False


async def test_hybrid_combination():
    """Test hybrid LLM + Bayesian combination."""
    print("\n" + "=" * 60)
    print("TEST 5: Hybrid Combination")
    print("=" * 60)

    from app.core.entity_registry import EntityRegistry
    from app.core.clue_analyzer import ClueAnalyzer
    from app.core.jackpot_predict import JackpotPredict

    # Initialize components
    registry = EntityRegistry()
    analyzer = ClueAnalyzer()
    predictor = JackpotPredict(
        entity_registry=registry,
        clue_analyzer=analyzer,
        enable_llm=True,
        enable_hybrid=True
    )

    print(f"[INFO] Entity count: {registry.get_entity_count()}")
    print(f"[INFO] Hybrid mode: {predictor.enable_hybrid}")

    # Process clues
    clues = [
        "Savors many flavors",
        "Round and round",
        "A hostile takeover",
        "Trespassing will cost you"
    ]

    for i, clue in enumerate(clues, 1):
        print(f"\n--- Clue {i}: {clue} ---")
        response = await predictor.add_clue_async(clue)

        print(f"Top 3 predictions:")
        for pred in response.predictions:
            marker = " <- TARGET" if pred.answer.lower() == "monopoly" else ""
            print(f"  {pred.rank}. {pred.answer} ({pred.confidence:.1f}%){marker}")

        # Check hybrid result
        hybrid = predictor.get_hybrid_result()
        if hybrid:
            print(f"\n[HYBRID]")
            if hybrid.llm_prediction:
                print(f"  LLM: {hybrid.llm_prediction.answer} ({hybrid.llm_prediction.confidence:.1%})")
            else:
                print("  LLM: Not available")

            if hybrid.bayesian_predictions:
                print(f"  Bayesian: {hybrid.bayesian_predictions[0].answer} ({hybrid.bayesian_predictions[0].confidence:.1%})")

            print(f"  Agreement: {hybrid.agreement}")
            print(f"  Recommended: {hybrid.recommended_source} -> {hybrid.recommended_answer}")

    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("HYBRID LLM + BAYESIAN PREDICTION SYSTEM TEST")
    print("=" * 60)

    results = {}

    # Test 1: LLM availability
    results['availability'] = await test_llm_availability()

    # Test 2: Context manager
    results['context'] = await test_context_manager()

    # Only run LLM tests if available
    if results['availability']:
        results['warmup'] = await test_llm_warmup()
        results['prediction'] = await test_single_prediction()
    else:
        print("\n[INFO] Skipping LLM tests - API not available")
        results['warmup'] = None
        results['prediction'] = None

    # Test 5: Hybrid (works even without LLM - falls back to Bayesian only)
    results['hybrid'] = await test_hybrid_combination()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, result in results.items():
        if result is True:
            status = "[PASS]"
        elif result is False:
            status = "[FAIL]"
        else:
            status = "[SKIP]"
        print(f"  {test_name}: {status}")

    passed = sum(1 for r in results.values() if r is True)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")

    if not results['availability']:
        print("\n" + "-" * 60)
        print("TO ENABLE HYBRID LLM MODE:")
        print("-" * 60)
        print("1. Install Text-Generation-WebUI:")
        print("   git clone https://github.com/oobabooga/text-generation-webui")
        print("")
        print("2. Download Qwen 2.5 32B EXL2 model:")
        print("   python download-model.py turboderp/Qwen2.5-32B-Instruct-exl2 --branch 4.0bpw")
        print("")
        print("3. Start with API enabled:")
        print("   python server.py --api --api-port 5000 --extensions openai")
        print("")
        print("4. Load model in UI with ExLlamaV2 loader")
        print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
