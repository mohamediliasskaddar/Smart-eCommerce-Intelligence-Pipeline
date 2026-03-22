import requests
import re
import html as html_module
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
import logging

from schemas import ProductRow, VariantRow, ScrapingResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HTMLCleaner:
    """Utility for HTML cleaning as per blueprint"""
    
    @staticmethod
    def clean(raw: str) -> str:
        """Clean HTML and cap at 1000 chars for LLM token efficiency"""
        if not raw:
            return ""
        decoded = html_module.unescape(raw)
        no_tags = re.sub(r"<[^>]+>", " ", decoded)
        collapsed = re.sub(r"\s+", " ", no_tags).strip()
        return collapsed[:1000]

class DateParser:
    """Utility for date parsing"""
    
    @staticmethod
    def parse(date_str: str) -> Optional[datetime]:
        """Parse various date formats"""
        if not date_str:
            return None
        try:
            formats = [
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d"
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    @staticmethod
    def days_since(date_str: str) -> Optional[int]:
        """Calculate days since a date"""
        date = DateParser.parse(date_str)
        if not date:
            return None
        try:
            now = datetime.now(timezone.utc) if date.tzinfo else datetime.now()
            delta = now - date
            return delta.days
        except Exception:
            return None

class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self, source_platform: str, source_store: str, shop_country: str):
        self.source_platform = 'shopify' 
        self.source_store = source_store
        self.shop_country = shop_country
        self.logger = logging.getLogger(self.__class__.__name__)

    def fetch_json(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """Fetch JSON data from URL"""
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return {}

    @abstractmethod
    def scrape(self) -> ScrapingResult:
        """Scrape data and return ScrapingResult"""
        pass

    def _create_product(
        self,
        product_id: str,
        name: str,
        description: str = "",
        category: str = "uncategorized",
        brand: str = "unknown",
        price: float = 0.0,
        price_original: Optional[float] = None,
        rating: Optional[float] = None,
        review_count: Optional[int] = None,
        in_stock: bool = False,
        stock_qty: Optional[int] = None,
        days_since_publish: Optional[int] = None,
        **kwargs
    ) -> ProductRow:
        """Helper to create a ProductRow with all derived fields"""
        price_original = price_original or price
        discount_pct = ((price_original - price) / price_original * 100) if price_original > price else 0.0
        is_on_promo = discount_pct > 0
        price_segment = "low" if price < 30 else "mid" if price < 100 else "high"

        return ProductRow(
            product_id=product_id,
            source_platform=self.source_platform,
            source_store=self.source_store,
            name=name,
            description=description,
            category=category,
            brand=brand,
            price=price,
            price_original=price_original,
            discount_pct=discount_pct,
            rating=rating,
            review_count=review_count,
            in_stock=in_stock,
            stock_qty=stock_qty,
            shop_country=self.shop_country,
            days_since_publish=days_since_publish,
            is_on_promo=is_on_promo,
            price_segment=price_segment
        )

    def _create_variant(
        self,
        product_id: str,
        variant_id: str,
        sku: str = "",
        option_value: str = "Default",
        price: float = 0.0,
        available: bool = True,
        position: int = 1
    ) -> VariantRow:
        """Helper to create a VariantRow"""
        return VariantRow(
            product_id=product_id,
            variant_id=variant_id,
            sku=sku,
            option_value=option_value,
            price=price,
            available=available,
            position=position
        )
