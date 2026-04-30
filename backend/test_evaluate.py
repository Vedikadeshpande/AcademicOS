import asyncio
from app.services.viva_service import evaluate_viva_answer

async def test_evaluate():
    question = "What are the key concepts of deep learning applications?"
    ideal_answer = "- Vision, NLP, Recommendations, Fraud Detection"
    transcription = "deep learning is a subset of machine learning and deep learning has many applications like computer vision for facial recognition, natural language processing for chatbots, and healthcare diagnostics."
    res = await evaluate_viva_answer(question, ideal_answer, transcription)
    print("------- EVALUATION RESULT -------")
    print(res)

if __name__ == "__main__":
    asyncio.run(test_evaluate())
