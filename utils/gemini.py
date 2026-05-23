from google import genai


def get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def generate(client, prompt: str) -> str:
    return client.models.generate_content(model="gemini-2.0-flash", contents=prompt).text
