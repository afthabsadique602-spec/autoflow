from groq import Groq
import os

def get_groq_client():
    key = os.getenv("GROQ_API_KEY")
    if not key: return None
    return Groq(api_key=key)

def call_llm(messages, model="llama-3.1-8b-instant", temp=0.5):
    client = get_groq_client()
    if not client: return "Warning LLM API Error: GROQ_API_KEY is missing from environment."
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temp,
            max_tokens=1024
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"LLM Error: {e}")
        return f"Warning LLM API Error: {str(e)}"
