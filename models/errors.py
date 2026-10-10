class LLMError(RuntimeError):
    """A model could not produce a response."""


class QuotaExceededError(LLMError):
    """The cloud API rejected the call because of quota / rate limits."""
