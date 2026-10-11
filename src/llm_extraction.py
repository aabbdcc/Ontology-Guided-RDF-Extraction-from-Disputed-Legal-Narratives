"""Legacy single-arm convenience wrapper; use scripts.run_paired_llm for research.

Set OPENAI_API_KEY for the endpoint (a placeholder is enough for local Ollama).
This convenience wrapper intentionally does not claim a controlled comparison.
"""

import os
from .llm_protocol import system_prompt, parse_prediction


def extract_with_llm(text, model, guided):
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("No OPENAI_API_KEY; no real LLM result may be reported")
    from openai import OpenAI

    client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL") or None, timeout=120)
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt(guided)},
            {"role": "user", "content": text},
        ],
    )
    raw = response.choices[0].message.content
    if not isinstance(raw, str):
        raise ValueError("Empty LLM response")
    parsed, _ = parse_prediction(raw, text)
    return parsed
