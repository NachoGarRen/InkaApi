import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

models_to_test = [
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
    'gemini-1.5-flash-002',
    'gemini-1.5-flash-8b',
    'gemini-2.0-flash',
    'gemini-2.5-flash',
    'gemini-flash-latest'
]

print("Starting tests...")
for model_name in models_to_test:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("test")
        print(f"SUCCESS: {model_name} works!")
    except Exception as e:
        print(f"FAIL: {model_name} - {str(e)[:100]}")
