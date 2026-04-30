import asyncio
import httpx

async def test_ollama():
    prompt = """
You are grading a university viva exam.
Your task is to evaluate the student's answer based on the points they covered, the points they missed, mistakes they made, and how they could make it better.

STRICT EVALUATION ALGORITHM:
1. Break down the Ideal Answer into essential key concepts/points.
2. Check the Student Answer specifically for each of those key concepts.
3. If the student adequately explains a concept, add it to "good_points".
4. If the student fails to mention a critical concept, add it to "missing_points".
5. If the student states something factually incorrect or hallucinates information, add it to "mistakes".
6. Based on their performance, give specific "suggestions" on how they could have made their answer better and more complete.

Question:
What are vanishing and exploding gradients?

Ideal Answer / Expected Concepts:
- Definition of vanishing gradient
- Definition of exploding gradient
- Backpropagation context

Student Answer (from speech-to-text):
So the main concepts and applications of deep learning...

Return a valid JSON object EXACTLY like this (ensure strict JSON syntax):
{
  "score": 5,
  "analysis": "A brief paragraph...",
  "good_points": ["Point they successfully covered"],
  "missing_points": ["Point they missed"],
  "mistakes": ["Incorrect statement they made (if any)"],
  "suggestions": ["How they could have improved their answer"]
}
"""
    system = "You are a highly analytical university professor evaluating a Viva (oral exam) answer. Output ONLY valid JSON without any formatting or comments."
    payload = {
        "model": "llama3.2",
        "prompt": prompt,
        "system": system,
        "stream": False,
        "format": "json",
        "options": {
            "num_predict": 1500,
            "temperature": 0.5
        }
    }
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post("http://localhost:11434/api/generate", json=payload)
        print("Status code:", resp.status_code)
        if resp.status_code == 200:
            print("Response:", resp.json().get("response", ""))
        else:
            print("Error:", resp.text)

if __name__ == "__main__":
    asyncio.run(test_ollama())
