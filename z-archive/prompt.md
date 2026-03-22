 # **unified dataset extraction blueprint** 
---

# 🧠 1. GLOBAL DATASET SCHEMA

This is your **final unified structure**:

```json
{
  "product_id": "string",
  "source_platform": "string",
  "name": "string",
  "description": "string",
  "category": "string",
  "brand": "string",
  "price": "float",
  "price_original": "float",
  "discount_pct": "float",
  "rating": "float",
  "review_count": "int",
  "in_stock": "boolean",
  "stock_qty": "int",
  "shop_country": "string",
  "days_since_publish": "int",
  "is_on_promo": "boolean",
  "price_segment": "string",
  "popularity_score": "float",
  "topk_label": "int"
}
```

---

# 🔗 2. SOURCE PLATFORM IDENTIFICATION

use "shopify" for all surces no matter the platform is 

| API                | source_platform value |
| ------------------ | --------------------- |
| dummyjson          | `"dummyjson"`         |
| fakestoreapi       | `"fakestore"`         |
| satechi            | `"satechi"`           |
| kyliecosmetics     | `"kyliecosmetics"`    |
| gymshark/jsoncrack | `"gymshark"`          |
| oneractive         | `"oneractive"`        |
| chubbies           | `"chubbies"`          |
| burga              | `"burga"`             |
| allbirds           | `"allbirds"`          |
| taylorstitch       | `"taylorstitch"`      |

---

# 🧩 3. FIELD MAPPING (VERY IMPORTANT)

## ✅ CORE FIELDS

| Target Field | Extraction Rule              |
| ------------ | ---------------------------- |
| product_id   | `id`                         |
| name         | `title`                      |
| description  | `description` OR `body_html` |
| category     | `category` OR `product_type` |
| brand        | `brand` OR `vendor`          |

---

## 💰 PRICE FIELDS (MULTI-STRUCTURE LOGIC)
 Two-table design ✅ RECOMMENDED
products.csv          → 1 row per product  (ML + BI)
variants.csv          → 1 row per variant  (association rules only)
This is the professional approach used in real ecommerce data pipelines.

## 🧮 discount_pct

```python
IF discountPercentage exists:
    discount_pct = discountPercentage
ELSE IF price_original > price:
    discount_pct = ((price_original - price) / price_original) * 100
ELSE:
    discount_pct = 0
```

---

## ⭐ RATINGS

| Source    | Rule        |
| --------- | ----------- |
| dummyjson | rating      |
| fakestore | rating.rate |
| others    | NULL        |

---

## 🧾 REVIEW COUNT

| Source    | Rule         |
| --------- | ------------ |
| dummyjson | len(reviews) |
| fakestore | rating.count |
| others    | 0            |

---

## 📦 STOCK

### dummyjson

```python
in_stock = stock > 0
stock_qty = stock
```

### Shopify-like APIs

```python
in_stock = ANY(variant.available == true)
stock_qty = COUNT(variants where available == true)
```

---

## 🌍 shop_country

if Not existed use 

SHOP_COUNTRY_MAP = {
    "dummyjson": "unknown",
    "fakestore": "unknown",
    "satechi": "US",
    "kyliecosmetics": "US",
    "gymshark": "UK",
    "oneractive": "UK",
    "chubbies": "US",
    "burga": "LT",
    "allbirds": "US",
    "taylorstitch": "US"
}

---

## ⏱️ days_since_publish

```python
IF published_at exists:
    days_since_publish = TODAY - published_at
ELSE:
    days_since_publish = TODAY - created_at
```

---

## 🔥 is_on_promo

```python
is_on_promo = discount_pct > 0
```

---

## 💸 price_segment

Define globally:

```python
IF price < 30 → "low"
IF 30 <= price < 100 → "mid"
IF price >= 100 → "high"
```

---

## 📈 popularity_score (important 🔥)

dont touch it 

## 🏷️ topk_label (for ML later)

dont touch it 


# ⚠️ 4. SPECIAL CASE HANDLING

## 🧼 HTML CLEANING

For `body_html`:

* Remove HTML tags
* Keep plain text only

---

## 🧩 MULTI-VARIANTS STRATEGY

You have 2 choices:

### Option A (RECOMMENDED ✅)

👉 One row per product:

* Use `variants[0]`

### Option B (ADVANCED)

👉 One row per variant:

* duplicate product info
* change:

  * product_id → `variant_id`

---

# 📄 5. FINAL OUTPUT EXAMPLE

```json
{
  "product_id": "8678656409688",
  "source_platform": "satechi",
  "name": "OntheGo Foldable Stand Hub",
  "description": "The Satechi OntheGo Foldable Stand Hub is designed for creators...",
  "category": "Hubs ## Stands",
  "brand": "Satechi",
  "price": 79.99,
  "price_original": 79.99,
  "discount_pct": 0,
  "rating": null,
  "review_count": 0,
  "in_stock": true,
  "stock_qty": 1,
  "shop_country": "unknown",
  "days_since_publish": 12,
  "is_on_promo": false,
  "price_segment": "mid",
  "popularity_score": 0,
  "topk_label": 0
}
```

---

# 🤖 6. AI EXTRACTION INSTRUCTIONS (THIS IS GOLD)

You can reuse this:

```
1. Identify API structure
2. Map fields using priority rules:
   - title → name
   - description OR body_html → description
   - brand OR vendor → brand
   - category OR product_type → category

3. Handle pricing:
   - If variants موجود → use variants[0]
   - Else use direct price fields

4. Compute derived fields:
   - discount_pct
   - is_on_promo
   - price_segment
   - popularity_score

5. Normalize:
   - Remove HTML
   - Convert strings → float/int

6. Handle missing values:
   - rating → null
   - review_count → 0
   - stock_qty → 0

7. Output one JSON object per product
```

---

