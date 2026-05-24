import re
import time

from google import genai

_RETRY_DELAY_RE = re.compile(r"retry in ([\d.]+)s", re.IGNORECASE)
_MAX_RETRIES = 2


def get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def generate(client, prompt: str) -> str:
    return client.models.generate_content(model="gemini-2.5-flash", contents=prompt).text


def generate_with_fallback(keys: list[str], prompt: str) -> str:
    last_exc: Exception = Exception("No API keys provided")
    for key in keys:
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return generate(get_client(key), prompt)
            except Exception as e:
                last_exc = e
                match = _RETRY_DELAY_RE.search(str(e))
                if match and attempt < _MAX_RETRIES:
                    time.sleep(float(match.group(1)) + 1)
                else:
                    break
    raise last_exc
