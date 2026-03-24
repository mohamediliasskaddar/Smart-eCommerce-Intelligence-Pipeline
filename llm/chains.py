"""
llm/chains.py
Four LangChain chains:
  1. guard_chain        — topic guardrail (blocks off-topic questions)
  2. topk_chain         — Top-K product summary
  3. strategy_chain     — strategic market analysis
  4. chat_chain         — conversational Q&A with dynamic context
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.language_models.chat_models import BaseChatModel

parser = StrOutputParser()

# ── SYSTEM PERSONA (shared by all chains) ─────────────────────────────
SYSTEM_PERSONA = """You are an expert ecommerce business analyst AI assistant.
You have access to a dataset of {n_products} products scraped from 10 ecommerce stores.
You help users understand product performance, market trends, and business insights.

STRICT RULES:
- Only answer questions about ecommerce, products, pricing, market analysis, or this dataset.
- If asked about anything unrelated (coding help, personal questions, news, etc.), 
  respond EXACTLY with: "I can only answer questions about the ecommerce dataset and product analysis."
- Always base your answers on the provided data context. Do not invent numbers.
- Use Chain of Thought: show your reasoning step by step before your conclusion.
- Be concise but insightful. Max 400 words per response."""


# ══════════════════════════════════════════════════════════════════════
# CHAIN 1 — GUARDRAIL
# Fast, cheap check before calling expensive chains
# ══════════════════════════════════════════════════════════════════════
GUARD_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a topic classifier. 
Classify the following question as either RELEVANT or IRRELEVANT.

RELEVANT = questions about: ecommerce, products, pricing, brands, market analysis, 
           sales performance, inventory, discounts, top products, recommendations,
           business strategy, data analysis, ML results.

IRRELEVANT = anything else: general coding, personal advice, news, weather, 
             math homework, recipes, etc.

Respond with ONLY one word: RELEVANT or IRRELEVANT."""),
    ("human", "{question}"),
])

def guard_chain(llm: BaseChatModel):
    return GUARD_PROMPT | llm | parser


# ══════════════════════════════════════════════════════════════════════
# CHAIN 2 — TOP-K SUMMARY
# Generates a narrative summary of the best products
# ══════════════════════════════════════════════════════════════════════
TOPK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PERSONA),
    ("human", """Based on the following Top-K product data from our ecommerce dataset, 
generate a professional executive summary.

TOP-K PRODUCTS DATA:
{context}

Your summary must include:
1. **Overall pattern**: What do top products have in common? (category, price range, brand)
2. **Price analysis**: Are top products premium, mid-range, or budget?
3. **Key brands**: Which brands dominate the top rankings?
4. **Business recommendation**: What 2-3 actionable insights can a buyer/manager take?

Use Chain of Thought — reason through the data before writing the summary.
Format as a professional business report section."""),
])

def topk_summary_chain(llm: BaseChatModel):
    return TOPK_PROMPT | llm | parser


# ══════════════════════════════════════════════════════════════════════
# CHAIN 3 — STRATEGIC REPORT
# Full market analysis based on aggregated stats
# ══════════════════════════════════════════════════════════════════════
STRATEGY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PERSONA),
    ("human", """You are preparing a strategic market intelligence report for a senior buyer.

DATASET STATISTICS:
{context}

Generate a structured strategic report with these sections:

## 1. Market Overview
Summarize the dataset: product diversity, price distribution, stock health.

## 2. Performance Insights
Interpret the ML results (XGBoost accuracy, feature importance, clustering).
What do the 3 clusters (budget/mid-range/premium) tell us about market structure?

## 3. Pricing Strategy
Analyze the price segments. Where is the market most competitive?

## 4. Risk Signals
Comment on anomalies, out-of-stock rates, and any concerning patterns.

## 5. Strategic Recommendations
Provide 3 concrete, data-backed recommendations.

Use Chain of Thought reasoning. Be specific — cite numbers from the data."""),
])

def strategy_chain(llm: BaseChatModel):
    return STRATEGY_PROMPT | llm | parser


# ══════════════════════════════════════════════════════════════════════
# CHAIN 4 — CONVERSATIONAL Q&A
# Dynamic context injection based on question routing
# ══════════════════════════════════════════════════════════════════════
CHAT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PERSONA),
    ("human", """Answer the following question about our ecommerce dataset.

RELEVANT DATA CONTEXT:
{context}

CONVERSATION HISTORY:
{history}

USER QUESTION: {question}

Instructions:
- If the question is not about ecommerce or this dataset, refuse politely.
- Think step by step (Chain of Thought) before giving your final answer.
- If the data context doesn't contain enough information, say so clearly.
- Keep your answer focused and under 300 words."""),
])

def chat_chain(llm: BaseChatModel):
    return CHAT_PROMPT | llm | parser


# ══════════════════════════════════════════════════════════════════════
# CHAIN 5 — PRODUCT ENRICHMENT
# Generate a better description for a single product
# ══════════════════════════════════════════════════════════════════════
ENRICH_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert ecommerce copywriter.
Your task is to enrich product descriptions to be more compelling and SEO-friendly.
Stay factual — only use information provided. Never invent specifications."""),
    ("human", """Rewrite the product description for this ecommerce product.

PRODUCT DATA:
{context}

Generate:
1. **Short description** (1-2 sentences, for product cards)
2. **Full description** (3-4 sentences, for product page)
3. **3 key selling points** (bullet points)

Keep it professional, factual, and compelling."""),
])

def enrichment_chain(llm: BaseChatModel):
    return ENRICH_PROMPT | llm | parser
