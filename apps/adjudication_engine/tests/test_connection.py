from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY not found")
else:
    print(f"API key found: {api_key[:6]}...")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents="Say hello in one word."
    )
    print("Connection successful!")
    print("Response:", response.text)