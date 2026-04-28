"""Enterprise Q&A — knowledge base with hierarchical ingestion."""

import asyncio
from contextforge import ContextForge


async def main():
    layer = ContextForge(
        provider="openai",
        api_key="sk-your-key-here",
        db_path="./enterprise_qa.db",
        max_context_tokens=6144,
        system_prompt=(
            "You are an enterprise knowledge assistant. "
            "Answer questions accurately using the provided knowledge base. "
            "Always cite your sources."
        ),
    )

    # Ingest company knowledge by department
    await layer.ingest_text(
        "Q3 2024 Revenue: $10.2M (up 15% YoY). Operating costs: $6.1M. "
        "Net profit: $2.3M. Key driver: Enterprise license sales grew 40%. "
        "Churn rate decreased to 3.2% from 4.1% in Q2.",
        title="Q3 2024 Financial Report",
        category="finance",
    )

    await layer.ingest_text(
        "Q2 2024 Revenue: $8.8M. Operating costs: $5.9M. Net profit: $1.5M. "
        "Enterprise licenses: $3.2M. SMB segment: $2.1M. "
        "Churn rate: 4.1%. New customer acquisition: 45 accounts.",
        title="Q2 2024 Financial Report",
        category="finance",
    )

    await layer.ingest_text(
        "Architecture: Microservices on Kubernetes. 12 core services. "
        "Event-driven communication via Kafka. PostgreSQL for persistence. "
        "Redis caching layer (99.2% hit rate). Average API latency: 45ms. "
        "Deployment: Blue-green with ArgoCD. 99.95% uptime SLA.",
        title="System Architecture Overview",
        category="engineering",
    )

    await layer.ingest_text(
        "PTO Policy: 20 days/year + 10 holidays. Remote work: 3 days/week. "
        "Benefits enrollment: January. 401k match: 4%. "
        "Performance reviews: Semi-annual (June, December).",
        title="Employee Handbook",
        category="hr",
    )

    print(f"Knowledge base: {layer.stats['knowledge_nodes']} nodes indexed")
    print()

    # Ask questions — knowledge is loaded proactively
    questions = [
        "What was our Q3 revenue and how does it compare to Q2?",
        "What's our system architecture?",
        "What's the PTO policy?",
    ]

    for q in questions:
        print(f"Q: {q}")
        response = await layer.chat(q)
        print(f"A: {response}\n")

    # Cross-domain analysis
    print("--- Cross-Domain Analysis ---")
    analysis = await layer.analyze(
        "How do our engineering investments correlate with revenue growth?"
    )
    print(analysis)

    layer.close()


if __name__ == "__main__":
    asyncio.run(main())
