from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Settings:
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", ".data")))
    sibyl_memory_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("SIBYL_MEMORY_PATH", ".data/sibyl-memory.db")
        )
    )
    sibyl_tenant_id: str = field(
        default_factory=lambda: os.getenv("SIBYL_TENANT_ID", "proofops-memoryguard-demo")
    )
    policy_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("MEMORYGUARD_POLICY_PATH", "config/memoryguard-policy.json")
        )
    )
    decision_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("DECISION_TTL_SECONDS", "600"))
    )
    agent_model_mode: str = field(
        default_factory=lambda: os.getenv("AGENT_MODEL_MODE", "deterministic")
    )
    agent_model_url: str = field(default_factory=lambda: os.getenv("AGENT_MODEL_URL", ""))
    agent_model_api_key: str = field(
        default_factory=lambda: os.getenv("AGENT_MODEL_API_KEY", "")
    )
    agent_model_name: str = field(
        default_factory=lambda: os.getenv("AGENT_MODEL_NAME", "")
    )
    agent_model_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("AGENT_MODEL_TIMEOUT_SECONDS", "20"))
    )
    public_base_url: str = field(
        default_factory=lambda: os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    )
    github_repo_url: str = field(
        default_factory=lambda: os.getenv(
            "GITHUB_REPO_URL", "https://github.com/seekitx/proofops-memoryguard"
        )
    )
    build_commit: str = field(
        default_factory=lambda: os.getenv(
            "BUILD_COMMIT", os.getenv("RENDER_GIT_COMMIT", "uncommitted-local-prototype")
        )
    )
    base_chain_id: int = field(
        default_factory=lambda: int(os.getenv("BASE_CHAIN_ID", "84532"))
    )
    base_network: str = field(
        default_factory=lambda: os.getenv("BASE_NETWORK", "base-sepolia")
    )
    base_rpc_url: str = field(
        default_factory=lambda: os.getenv("BASE_RPC_URL", "https://sepolia.base.org")
    )
    base_anchor_address: str = field(
        default_factory=lambda: os.getenv("BASE_ANCHOR_ADDRESS", "")
    )
    base_rpc_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("BASE_RPC_TIMEOUT_SECONDS", "10"))
    )
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            item.strip()
            for item in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:8000").split(",")
            if item.strip()
        )
    )

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sibyl_memory_path.parent.mkdir(parents=True, exist_ok=True)

    def load_policy(self) -> dict[str, Any]:
        raw = json.loads(self.policy_path.read_text(encoding="utf-8"))
        if raw.get("schema_version") != "1.0":
            raise ValueError("unsupported MemoryGuard policy schema")
        return dict(raw)

    def validate(self) -> None:
        if self.base_chain_id not in {8453, 84532}:
            raise ValueError("BASE_CHAIN_ID must be Base mainnet 8453 or Base Sepolia 84532")
        if self.app_env == "production":
            if not self.public_base_url.startswith("https://"):
                raise ValueError("PUBLIC_BASE_URL must use HTTPS in production")
            if self.sibyl_tenant_id == "proofops-memoryguard-demo":
                raise ValueError("set a deployment-specific SIBYL_TENANT_ID in production")
            if self.agent_model_mode != "remote":
                raise ValueError("production requires AGENT_MODEL_MODE=remote")
        if self.agent_model_mode not in {"deterministic", "remote"}:
            raise ValueError("AGENT_MODEL_MODE must be deterministic or remote")
        if self.agent_model_mode == "remote":
            if (
                not self.agent_model_url
                or not self.agent_model_api_key
                or not self.agent_model_name
            ):
                raise ValueError("remote Agent model configuration is incomplete")
