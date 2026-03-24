"""
llm/mcp_agents.py
Module 5/6 — Responsible Agent Design based on Model Context Protocol (MCP)
This implements the conceptual architecture for responsible A2A agents.

MCP Principles applied:
  - Context scoping   : each agent sees only its relevant context
  - Tool permissions  : agents declare what tools/data they can access
  - Refusal handling  : agents refuse out-of-scope requests
  - Audit trail       : all agent actions are logged
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import json
from pathlib import Path

LOG_PATH = Path(__file__).parent.parent / "data" / "output" / "agent_audit_log.jsonl"


# ══════════════════════════════════════════════════════════════════════
# MCP CONTEXT — defines what each agent is allowed to see and do
# ══════════════════════════════════════════════════════════════════════
@dataclass
class MCPContext:
    """
    Defines the scope of an agent's access.
    Following Anthropic's Model Context Protocol design principles.
    """
    agent_name:       str
    allowed_topics:   list[str]
    allowed_tools:    list[str]
    max_tokens:       int = 2000
    temperature:      float = 0.3
    requires_context: bool = True   # must have data context before responding

    def can_answer(self, question: str) -> bool:
        """Check if question falls within this agent's scope."""
        q = question.lower()
        return any(topic in q for topic in self.allowed_topics)

    def to_system_prompt(self) -> str:
        return f"""You are {self.agent_name}.
Your scope is strictly limited to: {', '.join(self.allowed_topics)}.
You have access to: {', '.join(self.allowed_tools)}.
If asked about anything outside your scope, respond:
"This question is outside my scope. Please ask about: {', '.join(self.allowed_topics[:3])}."
Always cite the data you used in your answer."""


# ── PREDEFINED AGENT CONTEXTS ─────────────────────────────────────────
TOPK_AGENT_CONTEXT = MCPContext(
    agent_name    = "TopK Analysis Agent",
    allowed_topics= ["top", "best", "rank", "popular", "recommend",
                     "performance", "score", "success"],
    allowed_tools = ["context_topk", "context_dataset_stats"],
    max_tokens    = 1500,
    temperature   = 0.2,
)

STRATEGY_AGENT_CONTEXT = MCPContext(
    agent_name    = "Market Strategy Agent",
    allowed_topics= ["strategy", "market", "trend", "insight", "overview",
                     "summary", "report", "competi", "segment", "cluster"],
    allowed_tools = ["context_dataset_stats", "context_association_rules",
                     "context_feature_importance"],
    max_tokens    = 2000,
    temperature   = 0.4,
)

ANOMALY_AGENT_CONTEXT = MCPContext(
    agent_name    = "Anomaly Detection Agent",
    allowed_topics= ["anomal", "outlier", "unusual", "weird", "strange",
                     "suspicious", "price issue", "discount"],
    allowed_tools = ["context_anomalies", "context_dataset_stats"],
    max_tokens    = 1000,
    temperature   = 0.1,
)

ENRICHMENT_AGENT_CONTEXT = MCPContext(
    agent_name    = "Product Enrichment Agent",
    allowed_topics= ["description", "enrich", "rewrite", "product detail",
                     "summarize product", "improve"],
    allowed_tools = ["context_product"],
    max_tokens    = 800,
    temperature   = 0.5,
)

ALL_AGENT_CONTEXTS = [
    TOPK_AGENT_CONTEXT,
    STRATEGY_AGENT_CONTEXT,
    ANOMALY_AGENT_CONTEXT,
    ENRICHMENT_AGENT_CONTEXT,
]


# ══════════════════════════════════════════════════════════════════════
# RESPONSIBLE AGENT — wraps an LLM with MCP context enforcement
# ══════════════════════════════════════════════════════════════════════
class ResponsibleAgent:
    """
    An agent that enforces its MCP context:
    - Refuses out-of-scope questions
    - Logs all interactions for audit
    - Injects only permitted context
    """

    def __init__(self, context: MCPContext, llm):
        self.context = context
        self.llm     = llm

    def run(self, question: str, data_context: str = "") -> str:
        """
        Run the agent on a question.
        Returns refusal message if out of scope.
        Logs the interaction regardless.
        """
        in_scope = self.context.can_answer(question)
        response = ""

        if not in_scope:
            response = (f"This question is outside my scope ({self.context.agent_name}). "
                        f"I can only help with: {', '.join(self.context.allowed_topics[:4])}.")
        else:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            prompt = ChatPromptTemplate.from_messages([
                ("system", self.context.to_system_prompt()),
                ("human", "DATA CONTEXT:\n{context}\n\nQUESTION: {question}"),
            ])
            chain    = prompt | self.llm | StrOutputParser()
            response = chain.invoke({
                "context":  data_context,
                "question": question,
            })

        # ── AUDIT LOG ─────────────────────────────────────────────────
        log_entry = {
            "timestamp":  datetime.now().isoformat(),
            "agent":      self.context.agent_name,
            "question":   question[:200],
            "in_scope":   in_scope,
            "response_len": len(response),
            "refused":    not in_scope,
        }
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

        return response


# ══════════════════════════════════════════════════════════════════════
# AGENT ROUTER — picks the right agent for a question
# ══════════════════════════════════════════════════════════════════════
def route_to_agent(question: str, llm) -> tuple[ResponsibleAgent, str]:
    """
    Route a question to the most appropriate agent.
    Returns (agent, agent_name).
    """
    from llm.context_builder import get_context_for_question

    q = question.lower()

    for ctx in ALL_AGENT_CONTEXTS:
        if ctx.can_answer(q):
            context_data = get_context_for_question(question)
            return ResponsibleAgent(ctx, llm), ctx.agent_name

    # Default: strategy agent handles general questions
    context_data = get_context_for_question(question)
    return ResponsibleAgent(STRATEGY_AGENT_CONTEXT, llm), STRATEGY_AGENT_CONTEXT.agent_name


def get_audit_log() -> list[dict]:
    """Read the agent audit log."""
    if not LOG_PATH.exists():
        return []
    entries = []
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries
