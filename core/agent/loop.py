"""
core/agent/loop.py - Multi-step agent: plan, gather, then act on approval.

The agent repeatedly asks a planner "what next?" and runs READ tools
immediately. WRITE tools (email, calendar, tasks, phone) are never run
here: they are queued, and the planner is told they will happen once the
user approves. The caller shows the plan and asks for one YES.

Planners:
  * GeminiPlanner – native function calling (API mode)
  * LocalPlanner  – JSON protocol over the on-device model (local mode),
                    so a local-mode agent run never leaves the machine
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from config.settings import settings
from core.agent.tools import READ, TOOLS, WRITE, Tool, ToolContext
from core.logger import get_logger
from core.rate_limiter import with_retry
from models.errors import LLMError, QuotaExceededError

logger = get_logger(__name__)

QUEUED_NOTE = (
    "Queued. This action will run after the user approves it. "
    "Treat it as done and continue; do not call it again."
)


@dataclass
class Call:
    name: str
    args: dict


@dataclass
class Step:
    tool: str
    args: dict
    kind: str
    result: str | None = None  # None for queued WRITE steps

    def describe(self) -> str:
        tool = TOOLS.get(self.tool)
        return tool.describe(self.args) if tool else f"{self.tool}({self.args})"


@dataclass
class AgentRun:
    goal: str
    steps: list[Step] = field(default_factory=list)
    pending: list[Step] = field(default_factory=list)
    answer: str = ""


class Planner(Protocol):
    def next(self) -> list[Call] | str:
        """Tool calls to make next, or the final answer text."""

    def observe(self, results: list[tuple[Call, str]]) -> None:
        """Feed back the result of each call returned by next()."""


def _now() -> str:
    return datetime.now(ZoneInfo(settings.TIMEZONE)).strftime(f"%A %Y-%m-%d %H:%M ({settings.TIMEZONE})")


def _rules() -> str:
    return (
        "You are Orchestrix, a personal assistant agent that can use tools.\n"
        f"Current time: {_now()}. User's default city: {settings.DEFAULT_CITY}.\n"
        "Work step by step toward the user's goal:\n"
        "- Gather facts with read-only tools before acting. Never invent tool results.\n"
        "- Tools that change things (sending email, creating events or tasks, phone actions) are queued "
        "for the user's approval. Call each one once with complete, final arguments "
        "(write the full email body yourself).\n"
        "- If the goal depends on a condition (e.g. 'if it's sunny'), check it first and only queue "
        "the actions whose condition holds.\n"
        "- Finish with a short answer that summarises what you found and what is queued."
    )


# ── Gemini (function calling) ─────────────────────────────────────────────────

class GeminiPlanner:
    def __init__(self, goal: str, tools: list[Tool]):
        from google.genai import types

        self._types = types
        self._config = types.GenerateContentConfig(
            system_instruction=_rules(),
            tools=[types.Tool(function_declarations=[
                types.FunctionDeclaration(**t.gemini_declaration()) for t in tools
            ])],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        self._contents = [types.Content(role="user", parts=[types.Part(text=goal)])]

    @with_retry(max_attempts=3, backoff_factor=1.5, retry_on=(LLMError,), give_up_on=(QuotaExceededError,))
    def _generate(self):
        from core.model_manager import gemini_limiter
        from models.gemini_llm import _get_client, _wrap

        gemini_limiter.wait_if_needed("gemini")
        try:
            return _get_client().models.generate_content(
                model=settings.GEMINI_MODEL, contents=self._contents, config=self._config
            )
        except Exception as e:
            raise _wrap(e) from e

    def next(self) -> list[Call] | str:
        response = self._generate()
        calls = response.function_calls or []
        if not calls:
            return (response.text or "").strip() or "Done."
        self._contents.append(response.candidates[0].content)
        return [Call(c.name, dict(c.args or {})) for c in calls]

    def observe(self, results: list[tuple[Call, str]]) -> None:
        parts = [
            self._types.Part.from_function_response(name=call.name, response={"result": result})
            for call, result in results
        ]
        self._contents.append(self._types.Content(role="user", parts=parts))


# ── Local model (JSON protocol) ───────────────────────────────────────────────

class LocalPlanner:
    def __init__(self, goal: str, tools: list[Tool]):
        self.goal = goal
        self.tools = tools
        self.history: list[tuple[Call, str]] = []

    def _catalogue(self) -> str:
        lines = []
        for t in self.tools:
            params = ", ".join(
                f"{name}: {spec.get('type', 'string')}{'' if name in t.required else '?'}"
                for name, spec in t.properties.items()
            )
            tag = "needs approval" if t.kind == WRITE else "read-only"
            lines.append(f"- {t.name}({params}) [{tag}]: {t.description}")
        return "\n".join(lines)

    def _prompt(self) -> str:
        steps = "\n".join(
            f"{i}. {c.name}({json.dumps(c.args)}) -> {r[:600]}" for i, (c, r) in enumerate(self.history, 1)
        ) or "(none yet)"
        return (
            f"Tools:\n{self._catalogue()}\n\n"
            f"Goal: {self.goal}\n\n"
            f"Steps so far:\n{steps}\n\n"
            'Reply with ONE JSON object: {"tool": "<name>", "args": {...}} to use a tool, '
            'or {"final": "<answer>"} when finished.'
        )

    def next(self) -> list[Call] | str:
        from models.local_llm import local_generate_json

        raw = local_generate_json(self._prompt(), _rules())
        decision = parse_decision(raw)
        if decision is None:
            return raw.strip()
        return decision

    def observe(self, results: list[tuple[Call, str]]) -> None:
        self.history.extend(results)


def parse_decision(raw: str) -> list[Call] | str | None:
    """Parse the local planner's JSON. Returns calls, a final answer, or None if unusable."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    if isinstance(data.get("final"), str):
        return data["final"]
    if isinstance(data.get("tool"), str):
        args = data.get("args") or {}
        return [Call(data["tool"], args if isinstance(args, dict) else {})]
    return None


# ── the loop ──────────────────────────────────────────────────────────────────

def make_planner(goal: str, model_type: str) -> Planner:
    tools = list(TOOLS.values())
    return GeminiPlanner(goal, tools) if model_type == "api" else LocalPlanner(goal, tools)


def run_agent(goal: str, ctx: ToolContext, planner: Planner, max_steps: int | None = None) -> AgentRun:
    max_steps = max_steps or settings.AGENT_MAX_STEPS
    run = AgentRun(goal=goal)
    seen: dict[str, str] = {}

    for _ in range(max_steps):
        decision = planner.next()
        if isinstance(decision, str):
            run.answer = decision
            return run

        results: list[tuple[Call, str]] = []
        for call in decision:
            results.append((call, _perform(call, ctx, run, seen)))
        planner.observe(results)

    run.answer = run.answer or f"Stopped after {max_steps} steps."
    return run


def _perform(call: Call, ctx: ToolContext, run: AgentRun, seen: dict[str, str]) -> str:
    tool = TOOLS.get(call.name)
    if tool is None:
        return f"Error: there is no tool named '{call.name}'."

    key = f"{call.name}:{json.dumps(call.args, sort_keys=True, default=str)}"
    if key in seen:  # planners sometimes repeat a call; don't run (or queue) it twice
        return seen[key]

    if tool.kind == WRITE:
        step = Step(call.name, call.args, WRITE)
        run.pending.append(step)
        run.steps.append(step)
        result = QUEUED_NOTE
    else:
        try:
            result = tool.execute(ctx, call.args)
        except Exception as e:  # report to the planner so it can recover
            logger.warning(f"Agent tool {call.name} failed: {e}")
            result = f"Error: {e}"
        run.steps.append(Step(call.name, call.args, READ, result))

    seen[key] = result
    return result


def execute_pending(steps: list[Step], ctx: ToolContext) -> list[tuple[Step, str]]:
    """Run approved WRITE steps; one failure doesn't stop the rest."""
    outcomes = []
    for step in steps:
        try:
            outcomes.append((step, TOOLS[step.tool].execute(ctx, step.args)))
        except Exception as e:
            outcomes.append((step, f"Failed: {e}"))
    return outcomes
