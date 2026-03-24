
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


github commit msg :
feat: A new feature.
fix: A bug fix.
docs: Documentation changes.
style: Code formatting changes that don’t affect logic.
refactor: Code restructuring without changing behavior.
perf: Performance improvements.
test: Test-related changes.
build: Changes to build process or external dependencies.
ci: CI/CD configuration changes.
chore: Maintenance tasks.
revert: Reverts a previous commit.





groqcloud doc:
```python
from openai import OpenAI
import os
client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

response = client.responses.create(
    input="Explain the importance of fast language models",
    model="openai/gpt-oss-20b",
)
print(response.output_text)
```
gemeini doc:

```python
from google import genai

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client()

response = client.models.generate_content(
    model="gemini-3-flash-preview", contents="Explain how AI works in a few words"
)
print(response.text)
```


Étape 5 : LLM pour enrichissement et synthèse 
Objectif : 
Enrichir l’analyse en générant des synthèses intelligentes, des résumés ou des 
recommandations. 
Concepts : 
● LLM : modèle de langage entraîné sur de vastes corpus, capable de générer 
ou résumer du texte. 
● Prompt Engineering : conception de requêtes textuelles pour interagir 
efficacement avec un LLM. 
● Chain of Thought : raisonnement explicite pour justifier les réponses du LLM. 
3 
Outils : 
● groqCloud, ollama,  
● LangChain: orchestrer des appels complexes à des LLMs. 
● [Streamlit Chat]: interface conversationnelle