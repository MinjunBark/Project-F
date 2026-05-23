from apify_client import ApifyClient


def get_client(api_token: str) -> ApifyClient:
    return ApifyClient(api_token)


def scrape_website(client: ApifyClient, url: str, max_pages: int = 10) -> list[dict]:
    """Crawl a website and return list of {url, title, text} dicts."""
    run = client.actor("apify/website-content-crawler").call(run_input={
        "startUrls": [{"url": url}],
        "maxCrawlPages": max_pages,
        "crawlerType": "cheerio",
    })
    dataset_id = run.default_dataset_id if hasattr(run, "default_dataset_id") else run["defaultDatasetId"]
    results = []
    for item in client.dataset(dataset_id).iterate_items():
        results.append({
            "url": item.get("url", ""),
            "title": item.get("metadata", {}).get("title", ""),
            "text": item.get("text", "")[:3000],
        })
    return results


def search_google(client: ApifyClient, query: str, max_results: int = 5) -> list[dict]:
    """Search Google and return list of {title, url, description} dicts."""
    run = client.actor("apify/google-search-scraper").call(run_input={
        "queries": query,
        "maxPagesPerQuery": 1,
        "resultsPerPage": max_results,
        "countryCode": "us",
    })
    dataset_id = run.default_dataset_id if hasattr(run, "default_dataset_id") else run["defaultDatasetId"]
    results = []
    for item in client.dataset(dataset_id).iterate_items():
        for r in item.get("organicResults", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "description": r.get("description", ""),
            })
    return results
