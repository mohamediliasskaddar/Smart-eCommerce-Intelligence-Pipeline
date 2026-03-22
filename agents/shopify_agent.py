from typing import List, Optional
from base_agent import BaseScraper, HTMLCleaner, DateParser
from schemas import ProductRow, VariantRow, ScrapingResult

class ShopifyScraper(BaseScraper):
    """Scraper for Shopify stores via public /products.json endpoint"""
    
    def __init__(self, store_url: str, source_store: str, shop_country: str):
        super().__init__("shopify", source_store, shop_country)
        self.store_url = store_url.rstrip('/')
        self.max_pages = 10  # Safety limit

    def scrape(self) -> ScrapingResult:
        """Scrape all products from Shopify store"""
        products = []
        variants = []
        error = None

        try:
            page = 1
            total_fetched = 0

            while page <= self.max_pages:
                url = f"{self.store_url}/products.json?limit=250&page={page}"
                data = self.fetch_json(url)

                if not data.get("products"):
                    break

                for product in data["products"]:
                    product_row, variant_rows = self._parse_product(product)
                    if product_row:
                        products.append(product_row)
                        variants.extend(variant_rows)
                        total_fetched += 1

                page += 1

            self.logger.info(f"Fetched {total_fetched} products from {self.source_store}")

        except Exception as e:
            error = str(e)
            self.logger.error(f"Error scraping {self.source_store}: {error}")

        return ScrapingResult(
            source_name=self.source_store,
            products=products,
            variants=variants,
            error=error
        )

    def _parse_product(self, product: dict) -> tuple[Optional[ProductRow], List[VariantRow]]:
        """Parse a single Shopify product"""
        try:
            product_id = str(product["id"])
            product_variants = product.get("variants", [])

            if not product_variants:
                return None, []

            # Use first variant for main product pricing
            first_variant = product_variants[0]
            price = float(first_variant.get("price", 0))
            compare_at_price = first_variant.get("compare_at_price")
            price_original = float(compare_at_price) if compare_at_price else price

            # Calculate days since publish
            published_at = product.get("published_at")
            days_since_publish = DateParser.days_since(published_at) if published_at else None

            # Create product row
            product_row = self._create_product(
                product_id=product_id,
                name=product.get("title", ""),
                description=HTMLCleaner.clean(product.get("body_html", "")),
                category=product.get("product_type", "uncategorized"),
                brand=product.get("vendor", "unknown"),
                price=price,
                price_original=price_original,
                rating=None,  # Will be enriched later
                review_count=None,  # Will be enriched later
                in_stock=any(v.get("available", False) for v in product_variants),
                stock_qty=None,  # Not available in public API
                days_since_publish=days_since_publish
            )

            # Create variant rows
            variant_rows = []
            for i, variant in enumerate(product_variants):
                variant_row = self._create_variant(
                    product_id=product_id,
                    variant_id=str(variant["id"]),
                    sku=variant.get("sku", ""),
                    option_value=variant.get("title", "Default"),
                    price=float(variant.get("price", 0)),
                    available=variant.get("available", True),
                    position=variant.get("position", i + 1)
                )
                variant_rows.append(variant_row)

            return product_row, variant_rows

        except Exception as e:
            self.logger.warning(f"Error parsing product {product.get('id')}: {e}")
            return None, []
