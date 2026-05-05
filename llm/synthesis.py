"""
llm/synthesis.py
Orchestrator — runs all LLM chains and saves outputs to data/output/llm_*.txt
Run standalone: python llm/synthesis.py
"""
import os
import json
from pathlib import Path
from datetime import datetime

from storage import StorageManager

BASE_DATA_PATH = Path(os.getenv("DATA_PATH", "/app/data"))
OUTPUT_DIR = BASE_DATA_PATH / "output"
BASE_DATA_PATH.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

storage = StorageManager(base_path=BASE_DATA_PATH)


def run_synthesis(model_label: str = "Groq — Llama 3.1 8B (fast)") -> dict:
    """
    Runs all synthesis chains and saves results.
    Returns dict with all generated texts.
    """
    from llm.llm_client import get_llm_with_fallback
    from llm.chains import topk_summary_chain, strategy_chain
    from llm.context_builder import context_topk, context_dataset_stats

    print(f"Running synthesis with model: {model_label}")
    llm = get_llm_with_fallback(model_label)

    results = {}
    n_products = 3809  # from dataset

    # ── TOP-K SUMMARY ─────────────────────────────────────────────────
    print("  Generating Top-K summary...")
    try:
        chain  = topk_summary_chain(llm)
        topk_text = chain.invoke({
            "context":    context_topk(20),
            "n_products": n_products,
        })
        results["topk_summary"] = topk_text
        storage.save_text(topk_text, OUTPUT_DIR / "llm_topk_summary.txt")
        print("  ✓ Top-K summary saved")
    except Exception as e:
        results["topk_summary"] = f"Error: {e}"
        print(f"  ✗ Top-K summary failed: {e}")

    # ── STRATEGY REPORT ───────────────────────────────────────────────
    print("  Generating strategy report...")
    try:
        chain  = strategy_chain(llm)
        strategy_text = chain.invoke({
            "context":    context_dataset_stats(),
            "n_products": n_products,
        })
        results["strategy_report"] = strategy_text
        storage.save_text(strategy_text, OUTPUT_DIR / "llm_strategy_report.txt")
        print("  ✓ Strategy report saved")
    except Exception as e:
        results["strategy_report"] = f"Error: {e}"
        print(f"  ✗ Strategy report failed: {e}")

    # ── METADATA ──────────────────────────────────────────────────────
    meta = {
        "model":      model_label,
        "generated_at": datetime.now().isoformat(),
        "outputs":    list(results.keys()),
    }
    storage.save_json(meta, OUTPUT_DIR / "llm_synthesis_meta.json")

    print(f"\n  All outputs saved to {OUTPUT_DIR}/llm_*.txt")
    return results


if __name__ == "__main__":
    results = run_synthesis("Groq — Llama 3.1 8B (fast)")
    print("\n=== TOP-K SUMMARY ===")
    print(results.get("topk_summary", "N/A"))
    print("\n=== STRATEGY REPORT ===")
    print(results.get("strategy_report", "N/A"))
