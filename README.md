
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
        "https://oneractive.com/products.json",       # women's activewear,shorts, tshirts, sport bras, underware, : title is liek a descriptions 
        "https://chubbiesshorts.com/products.json",   # lifestyle clothing for Men's Clothes  Kid's Clothes, 
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



Justification of 04 script :

Description fallback — instead of leaving oneractive and kyliecosmetics with 99% empty descriptions, it builds "Varsity Stripe Long Crew Socks | Sportswear | Oner Active" — not a real description but enough for the LLM enrichment module to work with in Module 4.
Chubbies category — parsed from tags. Their tags contain "MENS", "KIDS", "SWIM" — that's enough to assign mens clothing, swimwear, kids clothing. This fixes the 97.7% critical missing.
Rating enrichment — the key design decision is segment-calibrated, not flat random. A $9 mascara and a $400 tech hub should not get the same rating distribution. Low-price = more variance (impulse buys, more disappointed buyers). High-price = higher mean but fewer reviews. This makes your KMeans clusters meaningful — the high cluster will genuinely look different from low.
Stock enrichment — same logic: Gamma(3, 60) for cheap items (bulk stock), Gamma(1.5, 20) for premium (scarcity). Out-of-stock = 0 always.
Capping strategy — products are sorted by popularity_score descending before capping, so you keep the most analytically interesting products from each source, not a random slice.