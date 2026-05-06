import os
import pandas as pd
import logging
from pathlib import Path
from typing import List

from agents.base_agent import BaseScraper
from agents.shopify_agent import ShopifyScraper
from agents.simple_api_agent import DummyJSONScraper, FakeStoreScraper
from agents.schemas import ScrapingResult
from storage import StorageManager, RAW_PREFIX



BASE_DATA_PATH = Path(os.getenv("DATA_PATH", "/app/data"))
RAW_DATA_PATH = BASE_DATA_PATH / "raw"

BASE_DATA_PATH.mkdir(parents=True, exist_ok=True)
RAW_DATA_PATH.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IngestCoordinator:
    """Orchestrates all scrapers and manages output"""
    
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = RAW_DATA_PATH

        self.output_dir = Path(output_dir)
        self.products_file = Path("raw/products.csv")
        self.variants_file = Path("raw/variants.csv")
        self.results: List[ScrapingResult] = []
        self.storage = StorageManager(base_path=self.output_dir)

        os.makedirs(output_dir, exist_ok=True)

        # Clear existing files
        if os.path.exists(self.products_file):
            os.remove(self.products_file)
        if os.path.exists(self.variants_file):
            os.remove(self.variants_file)

    def add_scraper(self, scraper: BaseScraper) -> None:
        """Add a scraper to the coordinator"""
        result = scraper.scrape()
        self.results.append(result)
        
        # Log result
        logger.info(result.summary)
        
        # Save incrementally (as per blueprint)
        if result.success:
            self._save_result(result)

    def _save_result(self, result: ScrapingResult) -> None:
        """Save a result to CSV files using StorageManager ONLY"""
        # ===== PRODUCTS =====
        if result.products:
            new_df = pd.DataFrame([p.to_dict() for p in result.products])

            try:
                existing_df = self.storage.load_dataframe("products.csv", prefix=RAW_PREFIX)
                df = pd.concat([existing_df, new_df], ignore_index=True)
            except FileNotFoundError:
                df = new_df

            self.storage.save_dataframe(df, "products.csv", prefix=RAW_PREFIX)

        # ===== VARIANTS =====
        if result.variants:
            new_df = pd.DataFrame([v.to_dict() for v in result.variants])

            try:
                existing_df = self.storage.load_dataframe("variants.csv", prefix=RAW_PREFIX)
                df = pd.concat([existing_df, new_df], ignore_index=True)
            except FileNotFoundError:
                df = new_df

            self.storage.save_dataframe(df, "variants.csv", prefix=RAW_PREFIX)

    def get_summary(self) -> dict:
        """Get summary of all scraping results"""
        total_products = sum(len(r.products) for r in self.results if r.success)
        total_variants = sum(len(r.variants) for r in self.results if r.success)
        total_errors = sum(1 for r in self.results if not r.success)
        
        return {
            "total_sources": len(self.results),
            "successful_sources": len([r for r in self.results if r.success]),
            "failed_sources": total_errors,
            "total_products": total_products,
            "total_variants": total_variants
        }

    def validate_output(self) -> bool:
        """Validate that output files were created correctly"""
        if self.storage.exists(self.products_file):
            products_path = self.storage.fetch_local(self.products_file)
            df = pd.read_csv(products_path)
            logger.info(f"Products: {len(df)} rows, {len(df.columns)} columns")
            
            # Check all required columns
            expected_cols = [
                'product_id', 'source_platform', 'source_store', 'name', 'description',
                'category', 'brand', 'price', 'price_original', 'discount_pct',
                'rating', 'review_count', 'in_stock', 'stock_qty', 'shop_country',
                'days_since_publish', 'is_on_promo', 'price_segment'
            ]
            if list(df.columns) == expected_cols:
                logger.info("✓ Products schema is correct")
            else:
                logger.error("✗ Products schema mismatch")
                return False

        if self.storage.exists(self.variants_file):
            variants_path = self.storage.fetch_local(self.variants_file)
            df = pd.read_csv(variants_path)
            logger.info(f"Variants: {len(df)} rows, {len(df.columns)} columns")
            
            # Check all required columns
            expected_cols = ['product_id', 'variant_id', 'sku', 'option_value', 'price', 'available', 'position']
            if list(df.columns) == expected_cols:
                logger.info("✓ Variants schema is correct")
            else:
                logger.error("✗ Variants schema mismatch")
                return False

        return True

def run_ingestion():
    """Main ingestion function"""
    coordinator = IngestCoordinator()

    # Define and run scrapers
    scrapers = [
      
    ] 

    print("\n=== INGESTION COORDINATOR ===\n")
    for scraper in scrapers:
        coordinator.add_scraper(scraper)

    # Print summary
    summary = coordinator.get_summary()
    print("\n=== SUMMARY ===")
    print(f"Sources processed: {summary['successful_sources']}/{summary['total_sources']}")
    print(f"Products: {summary['total_products']}")
    print(f"Variants: {summary['total_variants']}")
    if summary['failed_sources'] > 0:
        print(f"Failed: {summary['failed_sources']}")

    # Validate output
    print("\n=== VALIDATION ===")
    if coordinator.validate_output():
        print("✓ All validations passed")
    else:
        print("✗ Validation failed")

if __name__ == "__main__":
    run_ingestion()
