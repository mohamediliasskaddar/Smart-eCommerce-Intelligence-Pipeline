"""
llm/enrichment.py
Batch enrichment of product descriptions using LLM.
Enriches products with empty/short descriptions.
Output: data/output/llm_enriched_products.csv
"""
import os
import pandas as pd
import time
from pathlib import Path

BASE_DATA_PATH = Path(os.getenv("DATA_PATH", "/app/data"))
PROCESSED = BASE_DATA_PATH / "processed"
OUTPUT = BASE_DATA_PATH / "output"
BASE_DATA_PATH.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)
OUTPUT.mkdir(parents=True, exist_ok=True)


def enrich_products(
    model_label: str = "Groq — Llama 3.1 8B (fast)",
    max_products: int = 50,
    min_desc_length: int = 50,
) -> pd.DataFrame:
    """
    Enriches products whose description is too short.
    Limits to max_products to control API costs.
    """
    from llm.llm_client import get_llm_with_fallback
    from llm.chains import enrichment_chain
    from llm.context_builder import context_product

    df = pd.read_csv(PROCESSED / "products.csv")

    # Only enrich products with short descriptions (< min_desc_length chars)
    needs_enrichment = df[df["description"].str.len() < min_desc_length].head(max_products)
    print(f"Products needing enrichment : {len(needs_enrichment)} (showing first {max_products})")

    if len(needs_enrichment) == 0:
        print("All products have sufficient descriptions.")
        return df

    llm   = get_llm_with_fallback(model_label)
    chain = enrichment_chain(llm)

    enriched_descriptions = {}
    errors = 0

    for i, (idx, row) in enumerate(needs_enrichment.iterrows()):
        product_id = str(row["product_id"])
        print(f"  [{i+1}/{len(needs_enrichment)}] Enriching: {row['name'][:50]}...")

        try:
            context = context_product(product_id)
            result  = chain.invoke({"context": context})
            enriched_descriptions[idx] = result

            # Rate limiting — Groq free tier: 30 req/min
            time.sleep(2.1)

        except Exception as e:
            print(f"    ✗ Failed: {e}")
            errors += 1
            if errors >= 3:
                print("  Too many errors — stopping enrichment")
                break

    # Apply enrichments
    df_enriched = df.copy()
    df_enriched["description_enriched"] = df_enriched["description"]
    for idx, text in enriched_descriptions.items():
        df_enriched.at[idx, "description_enriched"] = text

    df_enriched["is_enriched"] = df_enriched.index.isin(enriched_descriptions.keys())

    # Save
    output_path = OUTPUT / "llm_enriched_products.csv"
    df_enriched.to_csv(output_path, index=False)
    print(f"\n  ✓ Enriched {len(enriched_descriptions)} products")
    print(f"  ✓ Saved → {output_path}")

    return df_enriched


if __name__ == "__main__":
    enrich_products(max_products=10)
