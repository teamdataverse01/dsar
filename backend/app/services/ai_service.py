"""
AI draft generation — optional, uses Anthropic Claude.
Only called when ANTHROPIC_API_KEY is configured.
Every output carries a confidence_score and ai_risk_level.
AI is NEVER used for routing, risk decisions, or data retrieval.
"""
import logging
import json
from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_draft(
    request_type: str,
    subject_name: str,
    reference: str,
    template_draft: str,
    lookup_summary: str | None = None,
) -> dict:
    """
    Returns:
        {
            "draft_text": str,
            "confidence_score": float,   # 0.0 – 1.0
            "ai_risk_level": str,        # "low" | "medium" | "high"
            "skipped": bool,
        }
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.info("AI draft skipped — ANTHROPIC_API_KEY not configured")
        return {
            "draft_text": template_draft,
            "confidence_score": 1.0,
            "ai_risk_level": "low",
            "skipped": True,
        }

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        prompt = f"""You are a data protection officer drafting a GDPR/DSAR response letter.

Request type: {request_type}
Subject name: {subject_name}
Reference: {reference}
{"Data lookup summary: " + lookup_summary if lookup_summary else ""}

Use the following draft as a starting point and improve it for clarity, compliance, and tone.
Keep it professional and concise. Do not invent data or make promises not supported by the facts.

Draft:
{template_draft}

Respond with JSON only in this format:
{{
  "improved_draft": "...",
  "confidence_score": 0.0-1.0,
  "risk_level": "low|medium|high",
  "risk_notes": "brief explanation"
}}"""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)

        return {
            "draft_text": parsed.get("improved_draft", template_draft),
            "confidence_score": float(parsed.get("confidence_score", 0.7)),
            "ai_risk_level": parsed.get("risk_level", "medium"),
            "skipped": False,
        }

    except Exception as exc:
        logger.error("AI draft generation failed: %s", exc)
        return {
            "draft_text": template_draft,
            "confidence_score": 0.5,
            "ai_risk_level": "medium",
            "skipped": True,
            "error": str(exc),
        }
