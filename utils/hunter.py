import requests

HUNTER_BASE_URL = "https://api.hunter.io/v2"


def verify_email(api_key: str, email: str) -> dict:
    response = requests.get(
        f"{HUNTER_BASE_URL}/email-verifier",
        params={"email": email, "api_key": api_key},
    )
    response.raise_for_status()
    data = response.json().get("data", {})
    return {
        "email": email,
        "status": data.get("status", "unknown"),
        "score": data.get("score", 0),
    }


def find_email(api_key: str, domain: str, first_name: str, last_name: str) -> dict:
    response = requests.get(
        f"{HUNTER_BASE_URL}/email-finder",
        params={
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
            "api_key": api_key,
        },
    )
    response.raise_for_status()
    data = response.json().get("data", {})
    return {
        "email": data.get("email") or "",
        "confidence": data.get("confidence", 0),
    }
