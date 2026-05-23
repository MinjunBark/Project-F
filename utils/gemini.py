import google.generativeai as genai


def get_client(api_key: str):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def generate(client, prompt: str) -> str:
    return client.generate_content(prompt).text
