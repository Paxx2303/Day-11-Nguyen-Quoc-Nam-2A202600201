"""
Lab 11 — Helper Utilities using OpenAI
"""

import os
from openai import AsyncOpenAI


_async_client = None


def get_openai_client():
    """Get or create OpenAI AsyncClient."""
    global _async_client
    if _async_client is None:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        _async_client = AsyncOpenAI(api_key=api_key)
    return _async_client


async def chat_with_openai(
    prompt: str, system_prompt: str = None, model: str = "gpt-4o-mini"
) -> str:
    """Simple chat with OpenAI API.

    Args:
        prompt: User message
        system_prompt: Optional system prompt
        model: Model to use

    Returns:
        Assistant response text
    """
    client = get_openai_client()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content


async def chat_with_agent(agent, runner, user_message: str, session_id=None):
    """Send a message to the agent and get the response.

    This is a compatibility shim - uses OpenAI if no runner provided.

    Args:
        agent: The LlmAgent instance (ignored, kept for compatibility)
        runner: The InMemoryRunner instance (ignored, kept for compatibility)
        user_message: Plain text message to send
        session_id: Optional session ID (ignored)

    Returns:
        Tuple of (response_text, session)
    """
    from core.config import VinBank_SYSTEM_PROMPT

    client = get_openai_client()

    messages = [
        {"role": "system", "content": VinBank_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )

    return response.choices[0].message.content, None
