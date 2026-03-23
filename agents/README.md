
#  Module 1 — Data Scraping (A2A Agents)

##  Objective

This module is responsible for **automatically extracting product data** from multiple e-commerce sources such as **Shopify stores, WooCommerce APIs, and public dummy APIs**.

It follows an **Agent-to-Agent (A2A)** architecture where independent agents collaborate to collect, validate, and standardize data.

---

##  Key Concepts

* **Agent A2A (Agent-to-Agent)**
  Autonomous software components that connect to data sources, extract information, and communicate results.

* **Web Scraping**
  Extracting structured data from HTML pages.

* **Web Crawling**
  Navigating across multiple pages of a website to collect data at scale.

---

##  Technologies Used

* `requests`, `BeautifulSoup` → Static scraping
* `Selenium` / `Playwright` → Dynamic content (JavaScript rendering)
* `Scrapy` → Structured scraping pipelines
* **Shopify Storefront API** → Product data access
* **WooCommerce REST API** → Store data extraction

---

##  Project Structure

```
agents/
├── agent_coordinator.py   # Orchestrates all agents (A2A)
├── base_agent.py          # Base class for all agents
├── shopify_agent.py       # Scrapes Shopify stores
├── simple_api_agent.py    # Scrapes DummyJSON & FakeStore APIs
├── schemas.py             # Pydantic schema (20 columns)
└── README.md
```

```
data/
├── raw/
│   ├── products.csv       # Raw scraped product data
│   └── variants.csv       # Product variants
├── processed/
│   ├── products.csv       # Cleaned ML-ready dataset
│   └── source_quality_report.csv
└── output/
```

---

##  Extracted Data Fields

Each product includes:

* Title
* Price
* Availability
* Average rating
* Description
* Seller
* Category
* Geography
* Traffic indicators
* Variants and additional metadata

---

##  Pipeline Overview

1. **Agents collect data**

   * Shopify agent → 8 stores
   * API agent → DummyJSON + FakeStore

2. **Coordinator orchestrates agents**

   * Runs all agents in parallel or sequence
   * Merges outputs

3. **Data validation**

   * Enforced using **Pydantic schema (20 fields)**

4. **Preprocessing**

   * Clean dataset
   * Remove nulls
   * Normalize fields

5. **Quality audit**

   * Global and per-source quality reports

---

## Final Checklist

* ✔ Shopify agent scrapes 8 stores
* ✔ API agent scrapes multiple sources
* ✔ A2A coordination implemented
* ✔ Structured schema (20 columns)
* ✔ Data quality reporting
* ✔ Preprocessed dataset (3,809 rows, 0 nulls)
* ✔ ML-ready dataset generated

---

##  Output

* **Raw data:** `data/raw/products.csv`
* **Processed data:** `data/processed/products.csv`
* **Quality reports:** `source_quality_report.csv`

---

##  Notes

This module serves as the **data foundation** for downstream tasks such as:

* Machine Learning
* Recommendation systems
* Market analysis

---

