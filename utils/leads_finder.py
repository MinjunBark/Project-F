from apify_client import ApifyClient

ACTOR_ID = "code_crafter/leads-finder"


def search_leads(
    client: ApifyClient,
    job_titles: list[str],
    company_sizes: list[str] | None = None,
    industry: str | list[str] | None = None,
    limit: int = 100,
) -> list[dict]:
    """Run the leads-finder actor and return raw result items."""
    # TODO: verify param names for code_crafter/leads-finder before running live
    run_input = {
        "personTitle": job_titles,
        "totalResults": max(100, limit),
    }
    if company_sizes:
        run_input["companyEmployeeSize"] = company_sizes
    if industry:
        run_input["industry"] = [industry] if isinstance(industry, str) else industry

    run = client.actor(ACTOR_ID).call(run_input=run_input)
    dataset_id = run.default_dataset_id if hasattr(run, "default_dataset_id") else run["defaultDatasetId"]
    return list(client.dataset(dataset_id).iterate_items())


def extract_people(items: list[dict]) -> list[dict]:
    """Normalize code_crafter/leads-finder output to the project's standard lead schema."""
    people = []
    for item in items:
        if "error" in item:
            continue
        raw_email = item.get("email", "") or ""
        email = raw_email.split(",")[0].strip()
        founded = item.get("company_founded_year")
        people.append({
            "first_name": item.get("first_name", ""),
            "last_name": item.get("last_name", ""),
            "name": item.get("full_name", ""),
            "title": item.get("job_title", ""),
            "email": email,
            "email_status": "unverified",
            "personal_phone": item.get("mobile_number") or "",
            "linkedin_url": item.get("linkedin", ""),
            "company_name": item.get("company_name", ""),
            "company_website": item.get("company_website", ""),
            "company_industry": item.get("industry", ""),
            "company_employees": item.get("company_size") or 0,
            "company_technologies": item.get("company_technologies", ""),
            "company_keywords": item.get("keywords", ""),
            "company_revenue": item.get("company_annual_revenue_clean", ""),
            "company_phone": item.get("company_phone", ""),
            "company_total_funding_clean": item.get("company_total_funding_clean") or "",
            "company_age": str(2026 - int(founded)) if founded and str(founded).isdigit() else "",
            "source": "leads_finder",
        })
    return people
