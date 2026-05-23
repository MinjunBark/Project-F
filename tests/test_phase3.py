from unittest.mock import MagicMock


SAMPLE_LEAD = {
    "first_name": "Jane",
    "last_name": "Doe",
    "title": "VP of Customer Experience",
    "company_name": "Acme Telecom",
    "company_industry": "Telecommunications",
    "company_employees": 500,
    "company_revenue": "120M",
    "company_technologies": "five9, salesforce, cisco, hubspot",
    "company_keywords": "contact center, customer service, telecom, support, voice, broadband",
}

SAMPLE_INTEL = {
    "market_positioning": {
        "value_proposition": "The only unified platform for human and AI agents.",
        "differentiators": [
            "Real-time AI guidance during live conversations",
            "Unified platform for autonomous AI and human agents",
            "Enterprise-grade compliance and guardrails",
        ],
    },
    "ideal_customer_profile": {
        "pain_points": [
            "High and rising cost-to-serve in contact centers",
            "Agent performance variability",
            "Manual QA limited to small sample of conversations",
            "Compliance risk from inconsistent agent behavior in regulated industries",
        ],
        "tech_stack_signals": ["Genesys", "Five9", "Salesforce", "Avaya"],
    },
}

SAMPLE_RESPONSE = """
[EMAIL_SUBJECT]
AI coaching for your Five9 contact center
[EMAIL_BODY]
Hi Jane, I noticed Acme Telecom runs Five9 across your contact center. Teams at your scale often struggle with agent performance variability and rising cost-to-serve. Cresta's real-time AI platform sits on top of Five9 and gives agents live guidance during calls. Would you be open to a 15-minute chat to see if it fits?
[CALL_SCRIPT]
Opener: Hi Jane, this is [name] from Cresta — we work with telecom contact centers running Five9. | Discovery Q1: How are you currently coaching agents between calls vs during live conversations? | Discovery Q2: What percentage of calls does your QA team actually review today? | Pitch: Cresta puts an AI coach on every call in real time — we've helped similar teams cut handle time by 20% and double QA coverage without adding headcount.
[LINKEDIN]
Hi Jane — saw Acme Telecom is scaling its contact center operations. Cresta helps telecom teams using Five9 cut handle time with real-time AI coaching. Would love to connect and share what we've seen work at similar companies.
[END]
"""


def test_build_outreach_prompt_includes_lead_identity():
    from modules.phase3_outreach import build_outreach_prompt
    prompt = build_outreach_prompt(SAMPLE_LEAD, SAMPLE_INTEL)
    assert "Jane Doe" in prompt
    assert "VP of Customer Experience" in prompt
    assert "Acme Telecom" in prompt


def test_build_outreach_prompt_includes_filtered_tech_signals():
    from modules.phase3_outreach import build_outreach_prompt
    prompt = build_outreach_prompt(SAMPLE_LEAD, SAMPLE_INTEL)
    assert "Five9" in prompt
    assert "Salesforce" in prompt


def test_build_outreach_prompt_omits_tech_line_when_no_match():
    from modules.phase3_outreach import build_outreach_prompt
    lead = {**SAMPLE_LEAD, "company_technologies": "shopify, wordpress, mailchimp"}
    prompt = build_outreach_prompt(lead, SAMPLE_INTEL)
    assert "Tech signals" not in prompt


def test_parse_outreach_response_extracts_all_fields():
    from modules.phase3_outreach import parse_outreach_response
    result = parse_outreach_response(SAMPLE_RESPONSE)
    assert "Five9" in result["email_subject"]
    assert "Jane" in result["email_body"]
    assert "Opener" in result["call_script"]
    assert "connect" in result["linkedin_message"]


def test_parse_outreach_response_returns_empty_on_malformed_input():
    from modules.phase3_outreach import parse_outreach_response
    result = parse_outreach_response("This has no delimiters at all.")
    assert result["email_subject"] == ""
    assert result["email_body"] == ""
    assert result["call_script"] == ""
    assert result["linkedin_message"] == ""
    assert "raw_response" in result


def test_generate_outreach_returns_required_keys():
    from modules.phase3_outreach import generate_outreach
    mock_gemini = MagicMock()
    mock_gemini.models.generate_content.return_value.text = SAMPLE_RESPONSE
    result = generate_outreach(mock_gemini, SAMPLE_LEAD, SAMPLE_INTEL)
    for key in ["email_subject", "email_body", "call_script", "linkedin_message"]:
        assert key in result
