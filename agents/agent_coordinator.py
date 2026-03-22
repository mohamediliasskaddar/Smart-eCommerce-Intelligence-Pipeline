import os
import pandas as pd
import logging
from typing import List

from base_agent import BaseScraper
from shopify_agent import ShopifyScraper
from simple_api_agent import DummyJSONScraper, FakeStoreScraper
from schemas import ScrapingResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IngestCoordinator:
    """Orchestrates all scrapers and manages output"""
    
    def __init__(self, output_dir: str = None):
        # Get project root (one level up from agents/)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        # Set correct data/raw path at root
        if output_dir is None:
            output_dir = os.path.join(base_dir, "data", "raw")

        self.output_dir = output_dir
        self.products_file = os.path.join(output_dir, "products.csv")
        self.variants_file = os.path.join(output_dir, "variants.csv")
        self.results: List[ScrapingResult] = []

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
        """Save a result to CSV files"""
        if result.products:
            products_data = [p.to_dict() for p in result.products]
            df = pd.DataFrame(products_data)
            
            if os.path.exists(self.products_file):
                df.to_csv(self.products_file, mode='a', header=False, index=False)
            else:
                df.to_csv(self.products_file, mode='w', header=True, index=False)

        if result.variants:
            variants_data = [v.to_dict() for v in result.variants]
            df = pd.DataFrame(variants_data)
            
            if os.path.exists(self.variants_file):
                df.to_csv(self.variants_file, mode='a', header=False, index=False)
            else:
                df.to_csv(self.variants_file, mode='w', header=True, index=False)

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
        if os.path.exists(self.products_file):
            df = pd.read_csv(self.products_file)
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

        if os.path.exists(self.variants_file):
            df = pd.read_csv(self.variants_file)
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
        DummyJSONScraper(),
        FakeStoreScraper(),  # Disabled due to connectivity issues
        ShopifyScraper("https://satechi.net", "satechi", "US"),
        ShopifyScraper("https://kyliecosmetics.com", "kyliecosmetics", "US"),
        # Additional Shopify stores (uncomment to enable),
        ShopifyScraper("https://gymshark.com", "gymshark", "UK"),
        ShopifyScraper("https://oneractive.com", "oneractive", "UK"),
        ShopifyScraper("https://chubbiesshorts.com", "chubbies", "US"),
        ShopifyScraper("https://burga.com", "burga", "LT"),
        ShopifyScraper("https://allbirds.com", "allbirds", "US"),
        ShopifyScraper("https://taylorstitch.com", "taylorstitch", "US"),
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
