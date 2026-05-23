import pytest
import json
from pathlib import Path


def test_build_scraping_tasks_returns_five_tasks():
    from modules.phase1_intel import build_scraping_tasks
    tasks = build_scraping_tasks("Cresta", "https://cresta.com")
    assert len(tasks) == 5


def test_build_scraping_tasks_includes_main_website():
    from modules.phase1_intel import build_scraping_tasks
    tasks = build_scraping_tasks("Cresta", "https://cresta.com")
    urls = [t.get("url", "") for t in tasks if t["type"] == "website"]
    assert "https://cresta.com" in urls


def test_build_scraping_tasks_news_queries_contain_company():
    from modules.phase1_intel import build_scraping_tasks
    tasks = build_scraping_tasks("Cresta", "https://cresta.com")
    news_tasks = [t for t in tasks if t["type"] == "news"]
    assert len(news_tasks) >= 2
    for task in news_tasks:
        assert "Cresta" in task["query"]


def test_prepare_claude_prompt_contains_company_name():
    from modules.phase1_intel import prepare_claude_prompt
    scraped = [{"url": "https://cresta.com", "title": "Cresta AI", "text": "Real-time coaching."}]
    prompt = prepare_claude_prompt("Cresta", scraped)
    assert "Cresta" in prompt


def test_prepare_claude_prompt_contains_all_schema_keys():
    from modules.phase1_intel import prepare_claude_prompt
    scraped = [{"url": "https://cresta.com", "title": "Cresta", "text": "Contact center AI."}]
    prompt = prepare_claude_prompt("Cresta", scraped)
    for key in ["company_profile", "products_services", "market_positioning",
                "ideal_customer_profile", "competitor_analysis",
                "warm_lead_signals", "content_intelligence"]:
        assert key in prompt, f"Schema key missing from prompt: {key}"


def test_prepare_claude_prompt_instructs_json_only():
    from modules.phase1_intel import prepare_claude_prompt
    scraped = [{"url": "https://cresta.com", "title": "Cresta", "text": "AI platform."}]
    prompt = prepare_claude_prompt("Cresta", scraped)
    assert "Return ONLY the JSON" in prompt


def test_save_intel_creates_json_file(tmp_path):
    from modules.phase1_intel import save_intel
    intel = {"company_profile": {"name": "Cresta", "website": "cresta.com"}}
    filepath = save_intel("Cresta", intel, data_dir=str(tmp_path))
    assert Path(filepath).exists()


def test_save_intel_content_is_correct(tmp_path):
    from modules.phase1_intel import save_intel
    intel = {"company_profile": {"name": "Cresta"}}
    filepath = save_intel("Cresta", intel, data_dir=str(tmp_path))
    with open(filepath) as f:
        saved = json.load(f)
    assert saved["company_profile"]["name"] == "Cresta"


def test_save_intel_adds_meta(tmp_path):
    from modules.phase1_intel import save_intel
    intel = {"company_profile": {"name": "Cresta"}}
    filepath = save_intel("Cresta", intel, data_dir=str(tmp_path))
    with open(filepath) as f:
        saved = json.load(f)
    assert "_meta" in saved
    assert saved["_meta"]["company"] == "Cresta"
    assert saved["_meta"]["generated_by"] == "Claude Code (interactive)"


def test_load_intel_returns_none_if_missing(tmp_path):
    from modules.phase1_intel import load_intel
    assert load_intel("NonExistent", data_dir=str(tmp_path)) is None


def test_load_intel_round_trips_data(tmp_path):
    from modules.phase1_intel import save_intel, load_intel
    intel = {"company_profile": {"name": "Cresta"}}
    save_intel("Cresta", intel, data_dir=str(tmp_path))
    loaded = load_intel("Cresta", data_dir=str(tmp_path))
    assert loaded["company_profile"]["name"] == "Cresta"
