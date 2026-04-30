import asyncio
import httpx

async def test_ollama():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:11434/")
            print("Ollama connection:", resp.status_code, resp.text)
            
            resp = await client.post("http://localhost:11434/api/generate", json={"model": "phi3:mini", "prompt": "say hello", "stream": False})
            print("Ollama response:", resp.status_code)
            if resp.status_code == 200:
                print(resp.json())
            else:
                print(resp.text)
    except Exception as e:
        print("EXCEPTION:", type(e).__name__, str(e))

if __name__ == "__main__":
    asyncio.run(test_ollama())
