"""Pattern-based intent detection (no network, no models)."""

import pytest

from tools.email_intent import detect_email_intent, extract_email_fields, should_use_ai_generation
from tools.google_tasks_intent import detect_tasks_intent
from tools.utility_intent import detect_utility_intent
from tools.web_automation.intent import detect_web_intent

# ── tasks ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "text, expected",
    [
        ("show my tasks", "list_tasks"),
        ("list all tasks", "list_tasks"),
        ("add task buy groceries", "add_task"),
        ("new task finish project report", "add_task"),
        ("mark buy groceries as done", "complete_task"),
        ("complete task finish report", "complete_task"),
        ("delete task buy groceries", "delete_task"),
        ("remove task old item", "delete_task"),
        ("clear completed tasks", "clear_completed"),
        ("task stats", "task_stats"),
        ("how many tasks do I have", "task_stats"),
    ],
)
def test_task_intent_type(text, expected):
    result = detect_tasks_intent(text)
    assert result is not None and result["type"] == expected


@pytest.mark.parametrize(
    "text, keyword",
    [
        ("mark buy groceries as done", "buy groceries"),
        ("mark buy groceries task done", "buy groceries"),
        ("mark buy groceries done", "buy groceries"),
        ("complete task finish report", "finish report"),
    ],
)
def test_task_keyword_extraction(text, keyword):
    assert detect_tasks_intent(text)["keyword"] == keyword


def test_add_task_title():
    assert detect_tasks_intent("add task buy milk")["title"] == "buy milk"


# ── email ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "text, expected",
    [
        ("send email to john@example.com use ai write about project update", True),
        ("send email to john@example.com say hello", False),
        ("let ai write email to bob@company.com about deadline", True),
    ],
)
def test_use_ai_detection(text, expected):
    assert should_use_ai_generation(text) is expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("check my email", "read"),
        ("reply to email from alice", "reply"),
        ("draft email about meeting", "draft"),
        ("send email to john@example.com use ai", "send"),
    ],
)
def test_email_intent(text, expected):
    assert detect_email_intent(text) == expected


def test_email_fields_keep_original_case():
    fields = extract_email_fields("send email to bob@company.com saying Hello Bob, see you Monday")
    assert fields["to"] == "bob@company.com"
    assert fields["body"] == "Hello Bob, see you Monday"
    assert fields["use_ai"] is False
    assert fields["missing"] == []


def test_email_fields_strip_ai_trigger():
    fields = extract_email_fields("send email to john@example.com use ai write about project deadline")
    assert fields["use_ai"] is True
    assert fields["to"] == "john@example.com"
    assert "use ai" not in (fields["subject"] or "").lower()


def test_missing_recipient_reported():
    assert "recipient email address" in extract_email_fields("send email about lunch")["missing"]


# ── utilities (restored features) ────────────────────────────────────────────

@pytest.mark.parametrize(
    "text, expected",
    [
        ("weather in Mumbai", {"type": "weather_current", "city": "mumbai"}),
        ("weather forecast for pune tomorrow", {"type": "weather_forecast", "city": "pune"}),
        ("what's the weather like", {"type": "weather_current", "city": None}),
        ("convert 500 usd to inr", {"type": "currency_convert", "amount": 500.0, "from_curr": "USD", "to_curr": "INR"}),
        ("bitcoin price", {"type": "crypto_price", "symbol": "BTC"}),
        ("TCS stock price", {"type": "stock_price", "ticker": "TCS"}),
        ("find resume on drive", {"type": "drive_search", "query": "resume"}),
        ("compare the two PDFs", {"type": "pdf_compare"}),
        ("show my reminders", {"type": "reminder_list"}),
    ],
)
def test_utility_intents(text, expected):
    assert detect_utility_intent(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "how do I solve this equation",   # "sol" inside "solve" is not Solana
        "explain the scientific method",  # "eth" inside "method"
        "it takes 10 min to get there",   # not a currency pair
        "tell me a joke",
    ],
)
def test_utility_intents_avoid_false_positives(text):
    assert detect_utility_intent(text) is None


def test_reminder_parsing():
    assert detect_utility_intent("remind me to call mom tomorrow at 6:30 pm") == {
        "type": "reminder_set", "message": "call mom", "day": "tomorrow", "time": "6:30 pm",
    }
    assert detect_utility_intent("remind me to stretch at 5pm")["day"] == "today"


def test_url_intents():
    assert detect_utility_intent("summarize https://example.com/a.")["url"] == "https://example.com/a"
    assert detect_utility_intent("track price https://amzn.in/d/x")["type"] == "track_price"


# ── phone / web automation ───────────────────────────────────────────────────

def test_web_intents():
    assert detect_web_intent("open youtube") == {"type": "youtube_open"}
    assert detect_web_intent("search youtube for lofi beats")["query"] == "lofi beats"
    assert detect_web_intent("call 98765 43210")["number"] == "9876543210"
    assert detect_web_intent("what is the capital of france") is None
