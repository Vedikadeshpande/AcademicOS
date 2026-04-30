import sys
sys.path.append('v:/Coding/Python/Academic OS/backend')
import asyncio
from app.services.viva_service import _fast_llm_generate

async def test():
    prompt = """
    Return a JSON object EXACTLY like this:
    {
      "score": 5,
      "analysis": "This is a test analysis string.",
      "good_points": ["point 1"],
      "missing_points": ["point 2"],
      "mistakes": ["mistake 1"],
      "suggestions": ["suggestion 1"]
    }
    """
    res = await _fast_llm_generate(prompt, "You are a test grader.")
    print("--- RAW RESULT ---")
    print(repr(res))

asyncio.run(test())
