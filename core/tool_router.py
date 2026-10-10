"""
tool_router.py - Let Gemini pick a tool when no pattern handler matched.

The regex handlers cover the common phrasings; this catches the rest
("is it going to be hot in Pune?", "how's Infosys doing today?") using
Gemini's native function calling.

Only READ-ONLY tools are exposed. Anything that sends, books, deletes or
calls stays behind the pattern handlers and their YES/NO confirmations.
Used in API mode only, so local-mode requests never leave the device.
"""

from collections.abc import Callable
from dataclasses import dataclass

from config.settings import settings
from core.logger import get_logger
from core.rate_limiter import with_retry
from models.errors import LLMError, QuotaExceededError

logger = get_logger(__name__)


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    run: Callable[..., str]

    def declaration(self) -> dict:
        decl = {"name": self.name, "description": self.description}
        # Gemini rejects OBJECT schemas with no properties; omit them instead.
        if self.parameters.get("properties"):
            decl["parameters"] = self.parameters
        return decl


def _obj(properties: dict, required: list[str] | None = None) -> dict:
    schema = {"type": "OBJECT", "properties": properties}
    if required:
        schema["required"] = required
    return schema


_STR = {"type": "STRING"}
_NUM = {"type": "NUMBER"}
_INT = {"type": "INTEGER"}


def _weather(city: str = "") -> str:
    from tools.weather_tool import get_weather
    return get_weather(city or settings.DEFAULT_CITY)


def _forecast(city: str = "", days: int = 3) -> str:
    from tools.weather_tool import get_forecast
    return get_forecast(city or settings.DEFAULT_CITY, days=max(1, min(int(days), 5)))


def _convert(amount: float, from_currency: str, to_currency: str) -> str:
    from tools.finance_tool import convert_currency
    return convert_currency(float(amount), from_currency.upper(), to_currency.upper())


def _stock(ticker: str) -> str:
    from tools.finance_tool import get_stock_price
    return get_stock_price(ticker.upper())


def _crypto(symbol: str) -> str:
    from tools.finance_tool import get_crypto_price
    return get_crypto_price(symbol.upper())


def _tasks() -> str:
    from tools.google_tasks_tool import list_tasks
    return list_tasks()


def _events(days_ahead: int = 7) -> str:
    from tools.calendar_tool import list_events
    return list_events(days_ahead=max(1, min(int(days_ahead), 31)))


def _inbox() -> str:
    from tools.email_tool import format_inbox, read_inbox
    return format_inbox(read_inbox(max_results=5, unread_only=True))


def _drive(query: str) -> str:
    from tools.google_drive_tool import search_drive
    return search_drive(query)


TOOLS: dict[str, Tool] = {
    t.name: t
    for t in [
        Tool("get_weather", "Current weather for a city.", _obj({"city": _STR}), _weather),
        Tool("get_forecast", "Weather forecast for the next few days.", _obj({"city": _STR, "days": _INT}), _forecast),
        Tool(
            "convert_currency",
            "Convert an amount between currencies (ISO codes like USD, INR).",
            _obj({"amount": _NUM, "from_currency": _STR, "to_currency": _STR}, ["amount", "from_currency", "to_currency"]),
            _convert,
        ),
        Tool("get_stock_price", "Latest stock price for a ticker symbol (e.g. TCS.NS, AAPL).", _obj({"ticker": _STR}, ["ticker"]), _stock),
        Tool("get_crypto_price", "Latest price of a cryptocurrency (e.g. BTC, ETH).", _obj({"symbol": _STR}, ["symbol"]), _crypto),
        Tool("list_tasks", "The user's pending Google Tasks.", _obj({}), _tasks),
        Tool("list_calendar_events", "The user's upcoming Google Calendar events.", _obj({"days_ahead": _INT}), _events),
        Tool("check_inbox", "The user's unread Gmail messages.", _obj({}), _inbox),
        Tool("search_drive", "Search the user's Google Drive files by name.", _obj({"query": _STR}, ["query"]), _drive),
    ]
}

ROUTER_PREAMBLE = (
    "If one of the available functions directly answers the user's request, call it. "
    "Otherwise answer the question yourself in text.\n\n"
)


@with_retry(max_attempts=3, backoff_factor=1.5, retry_on=(LLMError,), give_up_on=(QuotaExceededError,))
def _generate_or_call(prompt: str):
    from core.model_manager import gemini_limiter
    from models.gemini_llm import gemini_generate_or_call

    gemini_limiter.wait_if_needed("gemini")
    return gemini_generate_or_call(prompt, [t.declaration() for t in TOOLS.values()])


def route_or_answer(prompt: str) -> tuple[str, str | None]:
    """
    One Gemini call that either answers or picks a tool.

    Returns (text, tool_name). tool_name is None when Gemini answered directly.
    Raises models.errors.LLMError on failure.
    """
    kind, payload = _generate_or_call(ROUTER_PREAMBLE + prompt)
    if kind == "text":
        return payload, None

    name, args = payload
    tool = TOOLS.get(name)
    if tool is None:
        logger.warning(f"Gemini chose unknown tool {name!r}")
        return "", None
    logger.info(f"LLM routing chose tool {name}", extra={"tool_args": args})
    try:
        return tool.run(**args), name
    except TypeError as e:
        logger.warning(f"Bad arguments for {name}: {args} ({e})")
        return "", None
