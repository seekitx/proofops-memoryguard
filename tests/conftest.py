from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofops_memoryguard.adapters import DisabledAnchorAdapter, InMemoryMemoryAdapter
from proofops_memoryguard.module import MemoryGuard


@pytest.fixture
def policy() -> dict[str, object]:
    path = Path(__file__).resolve().parents[1] / "config" / "memoryguard-policy.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def memory() -> InMemoryMemoryAdapter:
    return InMemoryMemoryAdapter()


@pytest.fixture
def guard(memory: InMemoryMemoryAdapter, policy: dict[str, object]) -> MemoryGuard:
    return MemoryGuard(
        memory=memory,
        anchor=DisabledAnchorAdapter(),
        policy=policy,
        production=False,
    )
