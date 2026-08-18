"""The project's exception taxonomy — named types only, no `except Exception:` anywhere."""

import anthropic

# Exceptions that a retryable operation may raise, and that the retry layer knows about.
RETRYABLE_MODEL_ERRORS: tuple[type[Exception], ...] = (
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
)

RETRYABLE_TOOL_ERRORS: tuple[type[Exception], ...] = (OSError,)


class BoundaryViolationError(Exception):
    """Raised when a resolved path falls outside the project root."""


class SandboxUnavailableError(Exception):
    """Raised when the bwrap startup probe fails."""


class ConfigError(Exception):
    """Raised when the Config cannot be constructed from its inputs."""


class RetriesExhaustedError(Exception):
    """Raised by the retry layer when the attempt cap is reached.

    Carries the measured wait sequence so the caller can report it verbatim.
    """

    def __init__(self, message: str, attempts: int, waits: list[float]) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.waits = waits
