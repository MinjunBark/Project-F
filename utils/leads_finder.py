from apify_client import ApifyClient

try:
    from apify_client.errors import ForbiddenError
except ImportError:
    ForbiddenError = Exception  # fallback

ACTOR_ID = "code_crafter/leads-finder"


def search_leads(
    client: ApifyClient,
    job_titles: list[str],
    company_sizes: list[str] | None = None,
    industry: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Run the leads-finder actor and return raw result items."""
    run_input = {
        "job_titles": job_titles,
        "fetch_count": limit,
    }
    if company_sizes:
        run_input["company_sizes"] = company_sizes
    if industry:
        run_input["industry"] = industry

    try:
        run = client.actor(ACTOR_ID).call(run_input=run_input)
    except ForbiddenError:
        raise RuntimeError(
            "Leads Finder actor requires permission approval. "
            "Visit https://apify.com/code_crafter/leads-finder and click 'Try for free' "
            "to authorize it on your account, then re-run."
        )

    dataset_id = run.default_dataset_id if hasattr(run, "default_dataset_id") else run["defaultDatasetId"]
    items = list(client.dataset(dataset_id).iterate_items())
    # Detect free-plan API block: actor returns a single {"error": "..."} item
    if len(items) == 1 and "error" in items[0] and not items[0].get("email"):
        raise RuntimeError(
            f"Leads Finder API blocked: {items[0]['error']} "
            "Upgrade to Apify Starter plan ($49/mo) to call this actor via API."
        )
    return items


def extract_people(items: list[dict]) -> list[dict]:
    """Normalize leads-finder output to the project's standard lead schema."""
    people = []
    for item in items:
        if "error" in item:
            continue
        people.append({
            "first_name": item.get("firstName") or item.get("first_name", ""),
            "last_name": item.get("lastName") or item.get("last_name", ""),
            "name": item.get("fullName") or item.get("full_name") or item.get("name", ""),
            "title": item.get("title") or item.get("jobTitle") or item.get("job_title", ""),
            "email": item.get("email") or item.get("workEmail") or item.get("work_email", ""),
            "email_status": "unverified",
            "linkedin_url": item.get("linkedinUrl") or item.get("linkedin_url") or item.get("linkedin", ""),
            "company_name": item.get("companyName") or item.get("company_name") or item.get("company", ""),
            "company_website": item.get("companyDomain") or item.get("company_domain") or item.get("website") or item.get("domain", ""),
            "company_industry": item.get("companyIndustry") or item.get("company_industry") or item.get("industry", ""),
            "company_employees": item.get("companySize") or item.get("company_size") or item.get("employees", ""),
            "source": "leads_finder",
        })
    return people
