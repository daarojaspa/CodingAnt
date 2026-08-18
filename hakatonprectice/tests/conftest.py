"""Shared fixtures: temp project root, fake clock, fake sleeper, fake Anthropic client."""

from __future__ import annotations

from pathlib import Path

import pytest

from fakes import FakeAnthropicClient, FakeClock, FakeSleeper


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def fake_sleeper(fake_clock: FakeClock) -> FakeSleeper:
    return FakeSleeper(clock=fake_clock)


@pytest.fixture
def fake_anthropic_client() -> FakeAnthropicClient:
    return FakeAnthropicClient()
