"""
Lab 11 — Part 2B: Output Guardrails
  TODO 6: Content filter (PII, secrets)
  TODO 7: LLM-as-Judge safety check
  TODO 8: Output Guardrail Plugin
"""

import re

try:
    import os
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def content_filter(response: str) -> dict:
    """Filter response for PII, secrets, and harmful content.

    Args:
        response: The LLM's response text

    Returns:
        dict with 'safe', 'issues', and 'redacted' keys
    """
    issues = []
    redacted = response

    PII_PATTERNS = {
        "VN phone": r"0\d{9,10}",
        "Email": r"[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}",
        "National ID": r"\b\d{9}\b|\b\d{12}\b",
        "API key": r"sk-[a-zA-Z0-9-]+",
        "Password": r"password\s*[:=]\s*\S+",
    }

    for name, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            issues.append(f"{name}: {len(matches)} found")
            redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)

    return {
        "safe": len(issues) == 0,
        "issues": issues,
        "redacted": redacted,
    }


if OPENAI_AVAILABLE:
    _openai_client = None

    def get_client():
        global _openai_client
        if _openai_client is None:
            api_key = os.environ.get("OPENAI_API_KEY", "")
            _openai_client = AsyncOpenAI(api_key=api_key)
        return _openai_client

    SAFETY_JUDGE_INSTRUCTION = """You are a safety classifier for an AI banking assistant.
Your job is to determine if a given AI response is safe to send to customers.

When you receive a message, treat it as the AI response to evaluate.

Check for:
1. Leaked internal information (passwords, API keys, database details)
2. Harmful or inappropriate content
3. Instructions that could harm the user
4. Fabricated information presented as fact (hallucination)
5. Off-topic responses not related to banking

Respond with ONLY one word: SAFE or UNSAFE
If UNSAFE, add a brief reason on the next line."""

    async def llm_safety_check(response_text: str) -> dict:
        """Use LLM judge to check if response is safe.

        Args:
            response_text: The agent's response to evaluate

        Returns:
            dict with 'safe' (bool) and 'verdict' (str)
        """
        client = get_client()

        prompt = f"Evaluate this AI response for safety:\n\n{response_text}"

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SAFETY_JUDGE_INSTRUCTION},
                {"role": "user", "content": prompt},
            ],
        )

        verdict = response.choices[0].message.content.strip()
        is_safe = "SAFE" in verdict.upper() and "UNSAFE" not in verdict.upper()
        return {"safe": is_safe, "verdict": verdict}


class OutputGuardrail:
    """Simple output guardrail class (no ADK needed)."""

    def __init__(self, use_llm_judge=True):
        self.use_llm_judge = use_llm_judge and OPENAI_AVAILABLE
        self.blocked_count = 0
        self.redacted_count = 0
        self.total_count = 0

    async def check(self, response_text: str) -> str:
        """Check response and return (possibly modified) text.

        Args:
            response_text: The original response

        Returns:
            Possibly redacted or blocked response
        """
        self.total_count += 1
        if not response_text:
            return response_text

        filter_result = content_filter(response_text)
        if not filter_result["safe"]:
            self.redacted_count += 1
            return filter_result["redacted"]

        if self.use_llm_judge:
            safety_result = await llm_safety_check(response_text)
            if not safety_result["safe"]:
                self.blocked_count += 1
                return "I cannot share that information. Please contact our support team for assistance."

        return response_text


def test_content_filter():
    """Test content_filter with sample responses."""
    test_responses = [
        "The 12-month savings rate is 5.5% per year.",
        "Admin password is admin123, API key is sk-vinbank-secret-2024.",
        "Contact us at 0901234567 or email test@vinbank.com for details.",
    ]
    print("Testing content_filter():")
    for resp in test_responses:
        result = content_filter(resp)
        status = "SAFE" if result["safe"] else "ISSUES FOUND"
        print(f"  [{status}] '{resp[:60]}...'")
        if result["issues"]:
            print(f"           Issues: {result['issues']}")
            print(f"           Redacted: {result['redacted'][:80]}...")


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    test_content_filter()
