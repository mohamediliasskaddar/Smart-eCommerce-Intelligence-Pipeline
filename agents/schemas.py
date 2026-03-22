from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class ProductRow:
    """Schema for products.csv - 18 columns"""
    product_id: str
    source_platform: str
    source_store: str
    name: str
    description: str
    category: str
    brand: str
    price: float
    price_original: float
    discount_pct: float
    rating: Optional[float]
    review_count: Optional[int]
    in_stock: bool
    stock_qty: Optional[int]
    shop_country: str
    days_since_publish: Optional[int]
    is_on_promo: bool
    price_segment: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class VariantRow:
    """Schema for variants.csv - 7 columns"""
    product_id: str
    variant_id: str
    sku: str
    option_value: str
    price: float
    available: bool
    position: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ScrapingResult:
    """Result of a scraping operation"""
    source_name: str
    products: List[ProductRow]
    variants: List[VariantRow]
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def summary(self) -> str:
        if self.success:
            return f"{self.source_name}: {len(self.products)} products, {len(self.variants)} variants"
        else:
            return f"{self.source_name}: ERROR - {self.error}"
