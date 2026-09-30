import json
from app.ai.schemas import AIAnalyticsContext

SYSTEM_PROMPT = """You are an expert social media analytics explanation assistant for SocialScope.
Your task is to explain already-computed, deterministic analytics metrics for a monitored social profile.

STRICT CONSTRAINTS & RULES:
1. Rely EXCLUSIVELY on the supplied structured analytics context.
2. NEVER invent missing values, fake data points, or convert null values to zero.
3. NEVER make unsupported causal claims (e.g. "follower count dropped because...").
4. NEVER predict future follower growth, future engagement rates, or future trends.
5. NEVER rank profiles, score accounts, or declare a profile "best" or "winning".
6. Clearly distinguish analytical observations from general investigative suggestions.
7. Be concise, objective, factual, and analytical.
8. Explicitly mention when insufficient data or short observation windows limit interpretation.
9. Output strictly valid JSON matching the requested JSON schema. Do not include markdown headers or commentary outside the JSON.
"""


def build_user_prompt(context: AIAnalyticsContext) -> str:
    """Builds user prompt carrying structured analytics JSON payload."""
    payload_json = json.dumps(context.model_dump(), default=str, indent=2)
    return f"""Please analyze the following structured SocialScope analytics context and generate a structured AIInsight JSON response explaining the observed metrics.

CONTEXT PAYLOAD:
{payload_json}

REQUIREMENTS:
Return a JSON object with the following fields:
- "title": A short headline summarizing current profile status
- "summary": A concise paragraph explaining observed growth, engagement, and content trends
- "observations": Array of objects, each containing:
    - "category": One of ("growth", "engagement", "content", "frequency", "anomaly")
    - "statement": Factual explanation of the observed pattern
    - "supporting_metrics": Array of strings (e.g., ["Followers: 12,500", "7D Growth: +450"])
- "data_points": Array of 3-5 key metric highlights
- "limitations": String noting observation window or missing data caveats (or null)
"""
