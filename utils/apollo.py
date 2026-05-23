import requests

APOLLO_BASE_URL = "https://api.apollo.io/v1"


def search_people(
    api_key: str,
    titles: list[str],
    employee_ranges: list[str],
    per_page: int = 25,
    page: int = 1,
) -> dict:
    response = requests.post(
        f"{APOLLO_BASE_URL}/mixed_people/search",
        json={
            "page": page,
            "per_page": per_page,
            "person_titles": titles,
            "organization_num_employees_ranges": employee_ranges,
        },
        headers={
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        },
    )
    response.raise_for_status()
    return response.json()


def extract_people(response: dict) -> list[dict]:
    people = []
    for p in response.get("people", []):
        org = p.get("organization") or {}
        people.append({
            "first_name": p.get("first_name", ""),
            "last_name": p.get("last_name", ""),
            "name": p.get("name", ""),
            "title": p.get("title", ""),
            "email": p.get("email", ""),
            "email_status": p.get("email_status", ""),
            "linkedin_url": p.get("linkedin_url", ""),
            "company_name": org.get("name", ""),
            "company_website": org.get("website_url", ""),
            "company_industry": org.get("industry", ""),
            "company_employees": org.get("estimated_num_employees"),
            "apollo_id": p.get("id", ""),
        })
    return people
