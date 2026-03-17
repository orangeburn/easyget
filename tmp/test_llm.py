import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Load .env
load_dotenv('backend/.env')

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
model_name = os.getenv("MODEL_NAME")

print(f"Testing LLM with:")
print(f"Base URL: {base_url}")
print(f"Model: {model_name}")
print(f"API Key: {api_key[:10]}...{api_key[-5:]}")

client = OpenAI(api_key=api_key, base_url=base_url)

def test_json_mode():
    system_prompt = "You are a helpful assistant. Directly return target keywords as a JSON object with key 'keywords'."
    user_input = "Expand: 'Charging pile'"
    try:
        print("\n--- Testing JSON Mode ---")
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        content = response.choices[0].message.content
        print("Raw Response:", content)
        data = json.loads(content)
        print("Parsed Result:", data)
    except Exception as e:
        print("JSON Mode Failed:", str(e))

def test_plain_mode():
    system_prompt = "You are a helpful assistant. Directly return target keywords as a JSON array."
    user_input = "Expand: 'Charging pile'"
    try:
        print("\n--- Testing Plain Mode ---")
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.1
        )
        content = response.choices[0].message.content
        print("Raw Response:", content)
    except Exception as e:
        print("Plain Mode Failed:", str(e))

if __name__ == "__main__":
    # test_json_mode()
    test_plain_mode()
