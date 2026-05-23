import requests
from datetime import datetime


def _color_for_phase(phase: str) -> int:
    return {
        "phase1": 0x1abc9c,
        "phase2": 0x9b59b6,
        "phase3": 0xf39c12,
        "phase4": 0x2980b9,
        "phase5": 0xe74c3c,
        "error":  0xff0000,
    }.get(phase, 0x95a5a6)


def send_notification(webhook_url: str, message: str, phase: str = "info") -> int:
    payload = {
        "embeds": [{
            "description": message,
            "color": _color_for_phase(phase),
            "footer": {"text": f"Project F · {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
        }]
    }
    response = requests.post(webhook_url, json=payload)
    response.raise_for_status()
    return response.status_code


def phase_complete(webhook_url: str, phase: str, company: str, summary: str) -> int:
    message = f"✓ **{phase.upper()} complete** — {company}\n{summary}"
    return send_notification(webhook_url, message, phase)


def phase_error(webhook_url: str, phase: str, company: str, error: str) -> int:
    message = f"❌ **{phase.upper()} failed** — {company}\n```{error}```"
    return send_notification(webhook_url, message, "error")
