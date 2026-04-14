"""Scrapers for simple mock APIs: DummyJSON and FakeStore"""
from typing import List, Optional
from base_agent import BaseScraper, HTMLCleaner
from schemas import ProductRow, VariantRow, ScrapingResult

class DummyJSONScraper(BaseScraper):
    """Scraper for DummyJSON mock API"""
    
    def __init__(self):
        super().__init__("dummyjson", "dummyjson", "unknown")

    def scrape(self) -> ScrapingResult:
        """Scrape all products from DummyJSON"""
        products = []
        variants = []
        error = None

        try:
            url = "https://dummyjson.com/products?limit=100"
            data = self.fetch_json(url)

            for product in data.get("products", []):
                product_row, variant_rows = self._parse_product(product)
                if product_row:
                    products.append(product_row)
                    variants.extend(variant_rows)

            self.logger.info(f"Fetched {len(products)} products from dummyjson")

        except Exception as e:
            error = str(e)
            self.logger.error(f"Error scraping dummyjson: {error}")

        return ScrapingResult(
            source_name="dummyjson",
            products=products,
            variants=variants,
            error=error
        )

    def _parse_product(self, product: dict) -> tuple[Optional[ProductRow], List[VariantRow]]:
        """Parse a single DummyJSON product"""
        try:
            product_id = str(product["id"])
            price = float(product.get("price", 0))
            discount_pct = float(product.get("discountPercentage", 0))
            price_original = round(price / (1 - discount_pct / 100), 2) if discount_pct else price

            # Create product row
            product_row = self._create_product(
                product_id=product_id,
                name=product.get("title", ""),
                description=HTMLCleaner.clean(product.get("description", "")),
                category=product.get("category", "uncategorized"),
                brand=product.get("brand", "unknown"),
                price=price,
                price_original=price_original,
                rating=float(product.get("rating", 0)),
                review_count=len(product.get("reviews", [])),
                in_stock=product.get("stock", 0) > 0,
                stock_qty=int(product.get("stock", 0)),
                days_since_publish=None  # Not available
            )

            # Create single variant (DummyJSON)
            variant_row = self._create_variant(
                product_id=product_id,
                variant_id=f"{product_id}-1",
                sku=product.get("sku", ""),
                option_value="Default",
                price=price,
                available=product.get("stock", 0) > 0,
                position=1
            )

            return product_row, [variant_row]

        except Exception as e:
            self.logger.warning(f"Error parsing product {product.get('id')}: {e}")
            return None, []

class FakeStoreScraper(BaseScraper):
    """Scraper for FakeStore API"""
    
    def __init__(self):
        super().__init__("fakestore", "fakestore", "unknown")

    def scrape(self) -> ScrapingResult:
        """Scrape all products from FakeStore"""
        products = []
        variants = []
        error = None

        try:
            url = "https://fakestoreapi.com/products"
            data = self.fetch_json(url)

            for product in data:
                product_row, variant_rows = self._parse_product(product)
                if product_row:
                    products.append(product_row)
                    variants.extend(variant_rows)

            self.logger.info(f"Fetched {len(products)} products from fakestore")

        except Exception as e:
            error = str(e)
            self.logger.error(f"Error scraping fakestore: {error}")

        return ScrapingResult(
            source_name="shopStore",
            products=products,
            variants=variants,
            error=error
        )

    def _parse_product(self, product: dict) -> tuple[Optional[ProductRow], List[VariantRow]]:
        """Parse a single FakeStore product"""
        try:
            product_id = str(product["id"])
            price = float(product.get("price", 0))

            # Create product row
            product_row = self._create_product(
                product_id=product_id,
                name=product.get("title", ""),
                description=HTMLCleaner.clean(product.get("description", "")),
                category=product.get("category", "uncategorized"),
                brand="unknown", 
                price=price,
                price_original=price,  # No discount info
                rating=float(product.get("rating", {}).get("rate", 0)),
                review_count=int(product.get("rating", {}).get("count", 0)),
                in_stock=True, 
                stock_qty=None,  
                days_since_publish=None  
            )

            # Create single variant
            variant_row = self._create_variant(
                product_id=product_id,
                variant_id=f"{product_id}-1",
                sku="",
                option_value="Default",
                price=price,
                available=True,
                position=1
            )

            return product_row, [variant_row]

        except Exception as e:
            self.logger.warning(f"Error parsing product {product.get('id')}: {e}")
            return None, []
