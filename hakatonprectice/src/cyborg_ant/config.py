"""All tunable values in one frozen dataclass."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Every tunable value the agent uses, resolved once at startup."""

    project_root: Path
    model: str = "claude-opus-5"
    max_tokens: int = 6000
    effort: str = "medium"
    retry_attempts: int = 3
    backoff_base_seconds: float = 1.0
    backoff_ratio: float = 2.0
    command_timeout_seconds: float = 30.0
    max_iterations: int = 10
    read_word_ceiling: int = 1000
    log_value_cap_bytes: int = 8192
    typo_cutoff: float = 0.75
    exit_word: str = "suerte_socio"

    def __post_init__(self) -> None:
        resolved = self.project_root.resolve()
        if not resolved.is_dir():
            raise NotADirectoryError(
                f"project_root does not exist or is not a directory: {resolved}"
            )
        object.__setattr__(self, "project_root", resolved)


def load_config(project_root: Path, **overrides: object) -> Config:
    """Build a Config for the given project root, applying any override fields."""
    return Config(project_root=project_root, **overrides)  # type: ignore[arg-type]
