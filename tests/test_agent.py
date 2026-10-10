"""Agent loop, approval flow, and the shared tool registry."""

import pytest

from core.agent import loop
from core.agent.loop import QUEUED_NOTE, Call, parse_decision, run_agent
from core.agent.tools import READ, TOOLS, WRITE, Tool, ToolContext
from core.orchestrator import respond
from core.session import sessions


class ScriptedPlanner:
    """Returns pre-set decisions and records what it was told."""

    def __init__(self, *decisions):
        self.decisions = list(decisions)
        self.observed = []

    def next(self):
        return self.decisions.pop(0)

    def observe(self, results):
        self.observed.extend(results)


@pytest.fixture
def fake_tools(monkeypatch):
    calls = []

    def weather(ctx, city=""):
        calls.append(("get_weather", city))
        return f"Sunny, 31C in {city}"

    def event(ctx, title, start, duration_minutes=60, location=""):
        calls.append(("create_calendar_event", title, start))
        return f"Event created: {title}"

    def email(ctx, to, subject, body):
        calls.append(("send_email", to))
        return f"Email sent to {to}."

    monkeypatch.setitem(TOOLS, "get_weather", Tool("get_weather", "", READ, weather, {"city": {"type": "string"}}))
    monkeypatch.setitem(TOOLS, "create_calendar_event", Tool(
        "create_calendar_event", "", WRITE, event,
        {"title": {"type": "string"}, "start": {"type": "string"}}, ["title", "start"]))
    monkeypatch.setitem(TOOLS, "send_email", Tool(
        "send_email", "", WRITE, email,
        {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}},
        ["to", "subject", "body"]))
    return calls


GOAL_PLAN = [
    [Call("get_weather", {"city": "Goa"})],
    [Call("create_calendar_event", {"title": "Beach day", "start": "2026-10-11T10:00"}),
     Call("send_email", {"to": "ravi@example.com", "subject": "Beach", "body": "Sunny tomorrow!"})],
    "It will be sunny in Goa. I queued a calendar event and an email.",
]


def test_reads_run_and_writes_are_queued(fake_tools):
    planner = ScriptedPlanner(*GOAL_PLAN)
    run = run_agent("beach plan", ToolContext(user_id="u"), planner)

    assert fake_tools == [("get_weather", "Goa")]          # only the READ tool ran
    assert [s.tool for s in run.pending] == ["create_calendar_event", "send_email"]
    assert ("Sunny, 31C in Goa") in [r for _, r in planner.observed]
    assert [r for c, r in planner.observed if c.name == "send_email"] == [QUEUED_NOTE]
    assert run.answer.startswith("It will be sunny")


def test_unknown_tool_and_errors_are_reported_back(monkeypatch):
    def broken(ctx):
        raise RuntimeError("service down")

    monkeypatch.setitem(TOOLS, "list_tasks", Tool("list_tasks", "", READ, broken))
    planner = ScriptedPlanner([Call("hack_the_planet", {})], [Call("list_tasks", {})], "done")
    run_agent("x", ToolContext(user_id="u"), planner)
    results = [r for _, r in planner.observed]
    assert "no tool named" in results[0]
    assert "service down" in results[1]


def test_repeated_calls_run_once(fake_tools):
    call = Call("get_weather", {"city": "Goa"})
    run_agent("x", ToolContext(user_id="u"), ScriptedPlanner([call], [call], "ok"))
    assert fake_tools == [("get_weather", "Goa")]


def test_step_limit(fake_tools):
    planner = ScriptedPlanner(*[[Call("get_weather", {"city": str(i)})] for i in range(10)])
    run = run_agent("x", ToolContext(user_id="u"), planner, max_steps=3)
    assert len(run.steps) == 3 and "Stopped after 3 steps" in run.answer


def test_bad_arguments_rejected(fake_tools):
    planner = ScriptedPlanner([Call("get_weather", {"town": "Goa"})], "ok")
    run_agent("x", ToolContext(user_id="u"), planner)
    assert "unknown argument" in planner.observed[0][1]
    assert fake_tools == []


# ── approval flow through the orchestrator ───────────────────────────────────

@pytest.fixture
def scripted(monkeypatch):
    def install(*decisions):
        monkeypatch.setattr("core.handlers.agent.make_planner", lambda goal, model: ScriptedPlanner(*decisions))
    return install


def test_agent_waits_for_yes(fake_tools, scripted):
    scripted(*GOAL_PLAN)
    reply = respond("/agent plan a beach day", user_id="u")
    assert "Waiting for your approval" in reply.text and "ravi@example.com" in reply.text
    assert reply.stage == 5
    assert ("send_email", "ravi@example.com") not in fake_tools

    # Another user's YES does nothing.
    respond("yes", user_id="mallory")
    assert ("send_email", "ravi@example.com") not in fake_tools

    done = respond("yes", user_id="u")
    assert "Event created: Beach day" in done.text and "Email sent" in done.text
    assert sessions.get("u").agent_pending == []


def test_agent_cancel(fake_tools, scripted):
    scripted(*GOAL_PLAN)
    respond("/agent plan a beach day", user_id="u")
    assert "Nothing was changed" in respond("no", user_id="u").text
    assert all(c[0] == "get_weather" for c in fake_tools)


def test_agent_usage_and_non_agent_text(scripted):
    assert "Usage: /agent" in respond("/agent", user_id="u").text
    assert "/agentic" not in respond("/help", user_id="u").text  # only the exact prefix triggers


def test_local_mode_uses_local_planner():
    planner = loop.make_planner("goal", "local")
    assert isinstance(planner, loop.LocalPlanner)


# ── local JSON protocol ──────────────────────────────────────────────────────

def test_parse_decision():
    assert parse_decision('{"final": "all done"}') == "all done"
    calls = parse_decision('Sure! {"tool": "get_weather", "args": {"city": "Pune"}}')
    assert calls[0].name == "get_weather" and calls[0].args == {"city": "Pune"}
    assert parse_decision("no json here") is None
    assert parse_decision('{"tool": "x", "args": "oops"}')[0].args == {}


def test_local_planner_feeds_history(monkeypatch):
    prompts = []

    def fake_json(prompt, system):
        prompts.append(prompt)
        return '{"tool": "get_weather", "args": {"city": "Goa"}}' if len(prompts) == 1 else '{"final": "sunny"}'

    monkeypatch.setattr("models.local_llm.local_generate_json", fake_json)
    monkeypatch.setitem(TOOLS, "get_weather", Tool("get_weather", "", READ, lambda ctx, city="": "Sunny", {"city": {"type": "string"}}))
    run = run_agent("weather?", ToolContext(user_id="u"), loop.LocalPlanner("weather?", list(TOOLS.values())))
    assert run.answer == "sunny"
    assert "-> Sunny" in prompts[1]


# ── registry ─────────────────────────────────────────────────────────────────

def test_registry_schemas_are_valid_for_gemini():
    from google.genai import types

    for tool in TOOLS.values():
        types.FunctionDeclaration(**tool.gemini_declaration())
        for name in tool.required:
            assert name in tool.properties


def test_write_tools_are_the_side_effect_ones():
    writes = {t.name for t in TOOLS.values() if t.kind == WRITE}
    assert writes == {"add_task", "create_calendar_event", "send_email", "save_email_draft", "set_phone_alarm"}


def test_document_search_without_documents_skips_model_load():
    session = sessions.get("nodocs")
    result = TOOLS["search_my_documents"].execute(ToolContext(user_id="nodocs", session=session), {"query": "x"})
    assert "No documents" in result
    assert session._pdf_store is None  # the embedding model was never loaded
