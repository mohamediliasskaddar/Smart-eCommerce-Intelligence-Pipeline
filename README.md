
vars : 
product_id | source_platform | name | desciption |category | brand
price | price_original | discount_pct
rating | review_count | in_stock | stock_qty
shop_country | days_since_publish
is_on_promo | price_segment | popularity_score | topk_label

---

> test urls we gonna follow

```
    TEST_URLS = {

    # ── SHOPIFY STORES (public /products.json, no auth) ────────────────
    "electronics": [
        "https://satechi.net/products.json",          # USB-C hubs, chargers, keyboards (~80 products)
        "https://kyliecosmetics.com/products.json",   # beauty tech, skincare devices
        "https://mvmtwatches.com/products.json",      # watches, no morroco  
    ],

    "fashion_apparel": [
        "https://gymshark.com/products.json",         # fitness wear, 200+ products, rich variants
        "https://oneractive.com/products.json",       # women's activewear, good complement
        "https://chubbiesshorts.com/products.json",   # lifestyle clothing, strong discount data
    ],

    "lifestyle_home": [
        "https://burga.com/products.json",            # phone cases → great for association rules
        "https://allbirds.com/products.json",         # shoes, sustainability angle
        "https://taylorstitch.com/products.json",     # clothing, variants rich (color/size)
    ],

    # ── MOCK / DEV APIs (always online, ideal for pipeline testing) ─────
    "mock_apis": [
        "https://dummyjson.com/products?limit=100",   # richest mock: brand, stock, discount, rating
        "https://fakestoreapi.com/products",          # simple mock: price, category, rating
    ],
}

# Pagination pattern (same for all Shopify stores):
# page 1 → ?limit=250&page=1
# page 2 → ?limit=250&page=2  (jusqu'à réponse vide)
```
---