import httpx
import json
import re
from typing import Dict, Any
from app.config import settings

def parse_json(raw: str) -> Dict[str, Any]:
    if not raw or not raw.strip():
        return {}
    raw = raw.strip()
    raw = re.sub(r',\s*\}', '}', raw)
    raw = re.sub(r',\s*\]', ']', raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    cleaned = re.sub(r'^```(?:json)?', '', raw, flags=re.MULTILINE|re.IGNORECASE)
    cleaned = re.sub(r'```$', '', cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r'(\{.*\})', cleaned, re.DOTALL)
    if match:
        extracted = match.group(1).strip()
        extracted = re.sub(r',\s*\}', '}', extracted)
        extracted = re.sub(r',\s*\]', ']', extracted)
        extracted = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', extracted)
        try:
            return json.loads(extracted)
        except json.JSONDecodeError as err:
            print(f"[LLMService] Failed to parse: {err}")
    return {}

async def fast_llm_generate(prompt: str, system: str, max_tokens: int = 2500) -> str:
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": settings.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.5
            }
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload
            )
            if resp.status_code == 200:
                print(f"[LLMService] Groq success")
                return resp.json()["choices"][0]["message"]["content"].strip()
            else:
                return f"[ERROR: GROQ STATUS {resp.status_code}] {resp.text}"
    except Exception as e:
        error_name = type(e).__name__
        print(f"[LLMService] error: {error_name} - {str(e)}")
        return f"[ERROR: GROQ UNKNOWN {error_name}] {str(e)}"
