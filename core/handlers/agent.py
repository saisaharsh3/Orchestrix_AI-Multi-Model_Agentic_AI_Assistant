"""
/agent <goal> – multi-step agent with plan-then-approve.

Read-only steps run straight away; actions that change something are shown
as a numbered plan and run only after the user replies YES.
"""

from core.agent import AgentRun, ToolContext, execute_pending, make_planner, run_agent
from core.handlers.base import STAGE_AGENT, Reply, Request
from core.logger import get_logger

logger = get_logger(__name__)

PREFIX = "/agent"
CONFIRM_WORDS = {"yes", "y", "confirm", "go", "do it"}
CANCEL_WORDS = {"no", "n", "cancel", "stop"}

USAGE = (
    "Agent mode plans and chains several steps for you.\n\n"
    "Usage: /agent <goal>\n"
    "e.g. /agent check the weather in Goa tomorrow; if it's sunny add a beach day at 10am "
    "to my calendar and email ravi@example.com about it\n\n"
    "I look things up on my own, but anything that sends, creates or controls something "
    "waits for your YES."
)


def handle_pending(req: Request) -> Reply | None:
    pending = req.session.agent_pending
    if not pending:
        return None

    if req.lower in CONFIRM_WORDS:
        req.session.agent_pending = []
        outcomes = execute_pending(pending, _ctx(req))
        lines = ["Done:"] + [f"{i}. {step.describe()}\n   → {result}" for i, (step, result) in enumerate(outcomes, 1)]
        return Reply("\n".join(lines), stage=STAGE_AGENT)

    if req.lower in CANCEL_WORDS:
        req.session.agent_pending = []
        return Reply("Cancelled. Nothing was changed.", stage=STAGE_AGENT)

    return Reply(_pending_text(pending) + "\n\nReply YES to run these, or NO to cancel.", stage=STAGE_AGENT)


def handle(req: Request) -> Reply | None:
    if not (req.lower == PREFIX or req.lower.startswith(PREFIX + " ")):
        return None
    goal = req.text[len(PREFIX):].strip()
    if not goal:
        return Reply(USAGE, stage=STAGE_AGENT)

    planner = make_planner(goal, req.model_type)
    run = run_agent(goal, _ctx(req), planner)
    logger.info(
        "Agent run finished",
        extra={"steps": len(run.steps), "pending": len(run.pending), "model": req.model_type},
    )
    req.session.agent_pending = run.pending
    return Reply(format_run(run), stage=STAGE_AGENT)


def _ctx(req: Request) -> ToolContext:
    return ToolContext(user_id=req.user_id, session=req.session)


def format_run(run: AgentRun) -> str:
    lines = [f"🤖 Goal: {run.goal}"]
    looked_up = [s for s in run.steps if s.result is not None]
    if looked_up:
        lines.append("\nLooked up:")
        for i, step in enumerate(looked_up, 1):
            summary = " ".join(step.result.split()) or "(empty)"
            lines.append(f"{i}. {step.describe()}\n   → {summary[:200]}")
    if run.answer:
        lines.append(f"\n{run.answer}")
    if run.pending:
        lines.append("\n" + _pending_text(run.pending))
        lines.append("\nReply YES to run these, or NO to cancel.")
    return "\n".join(lines)


def _pending_text(pending) -> str:
    lines = ["Waiting for your approval:"]
    for i, step in enumerate(pending, 1):
        lines.append(f"{i}. {step.tool}")
        for key, value in step.args.items():
            lines.append(f"   {key}: {value}")
    return "\n".join(lines)
