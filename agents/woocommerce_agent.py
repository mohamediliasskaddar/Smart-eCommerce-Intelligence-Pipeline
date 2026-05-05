from typing import List, Optional
from agents.base_agent import BaseScraper, HTMLCleaner, DateParser
from agents.schemas import ProductRow, VariantRow, ScrapingResult
import requests
from requests.auth import HTTPBasicAuth
import os


class WooCommerceScraper(BaseScraper):
    """Scraper for WooCommerce stores via REST API"""

    def __init__(self, store_url: str, source_store: str, shop_country: str):
        super().__init__("woocommerce", source_store, shop_country)
        self.store_url = store_url.rstrip("/")
        self.base_api = f"{self.store_url}/wp-json/wc/v3"
        self.max_pages = 50

        # Load keys from .env
        self.consumer_key = os.getenv("WC_CONSUMER_KEY")
        self.consumer_secret = os.getenv("WC_CONSUMER_SECRET")

        if not self.consumer_key or not self.consumer_secret:
            raise ValueError("WooCommerce API keys missing in .env")

    def scrape(self) -> ScrapingResult:
        products = []
        variants = []
        error = None

        try:
            page = 1
            total_fetched = 0

            while page <= self.max_pages:
                url = f"{self.base_api}/products"
                params = {
                    "per_page": 100,
                    "page": page
                }

                response = requests.get(
                    url,
                    params=params,
                    auth=HTTPBasicAuth(self.consumer_key, self.consumer_secret)
                )

                if response.status_code != 200:
                    raise Exception(f"API error {response.status_code}: {response.text}")

                data = response.json()

                if not data:
                    break

                for product in data:
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
        try:
            product_id = str(product["id"])

            price = float(product.get("price") or 0)
            regular_price = product.get("regular_price")
            price_original = float(regular_price) if regular_price else price

            published_at = product.get("date_created")
            days_since_publish = DateParser.days_since(published_at) if published_at else None

            product_row = self._create_product(
                product_id=product_id,
                name=product.get("name", ""),
                description=HTMLCleaner.clean(product.get("description", "")),
                category=self._extract_category(product),
                brand=self._extract_brand(product),
                price=price,
                price_original=price_original,
                rating=product.get("average_rating"),
                review_count=product.get("rating_count"),
                in_stock=product.get("stock_status") == "instock",
                stock_qty=product.get("stock_quantity"),
                days_since_publish=days_since_publish
            )

            # Handle variants (variable products)
            variant_rows = []
            if product.get("type") == "variable":
                variant_rows = self._fetch_variants(product_id)

            return product_row, variant_rows

        except Exception as e:
            self.logger.warning(f"Error parsing product {product.get('id')}: {e}")
            return None, []

    def _fetch_variants(self, product_id: str) -> List[VariantRow]:
        """Fetch product variations"""
        variants = []
        page = 1

        while True:
            url = f"{self.base_api}/products/{product_id}/variations"
            params = {"per_page": 100, "page": page}

            response = requests.get(
                url,
                params=params,
                auth=HTTPBasicAuth(self.consumer_key, self.consumer_secret)
            )

            if response.status_code != 200:
                break

            data = response.json()
            if not data:
                break

            for i, variant in enumerate(data):
                variant_row = self._create_variant(
                    product_id=product_id,
                    variant_id=str(variant["id"]),
                    sku=variant.get("sku", ""),
                    option_value=self._format_attributes(variant.get("attributes", [])),
                    price=float(variant.get("price") or 0),
                    available=variant.get("stock_status") == "instock",
                    position=i + 1
                )
                variants.append(variant_row)

            page += 1

        return variants

    def _extract_category(self, product: dict) -> str:
        categories = product.get("categories", [])
        return categories[0]["name"] if categories else "uncategorized"

    def _extract_brand(self, product: dict) -> str:
        # WooCommerce doesn't enforce brand → fallback
        return product.get("brand", "unknown")

    def _format_attributes(self, attrs: list) -> str:
        return ", ".join([f"{a['name']}:{a['option']}" for a in attrs])