"""
Load config from repo root config.yaml (single source for Terraform and ML).
Use these variables in your scripts — see run_pipeline.py for a print-only example.
"""
import os
from pathlib import Path

import yaml


def _repo_root() -> Path:
    """Repo root: directory that contains ML-code/ and config.yaml."""
    root = Path(__file__).resolve().parent.parent
    return root


def load_config() -> dict:
    """
    Load config from repo root config.yaml.
    Uses ACTIVE_ENV env var if set (CI), else active_env in file, else "dev".
    Returns the active environment block with computed keys (buckets, etc.).
    """
    root = _repo_root()
    config_path = root / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"config.yaml not found at {config_path}. "
            "Create it at repo root (same level as ML-code/)."
        )
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise ValueError("config.yaml must contain a mapping at the top level.")

    active_env = os.environ.get("ACTIVE_ENV") or raw.get("active_env") or "dev"
    if "environments" not in raw or active_env not in raw["environments"]:
        raise ValueError(
            f"config.yaml must have environments.{active_env}. "
            f"Got active_env={active_env!r}, keys={list(raw.get('environments', {}).keys())!r}."
        )
    data = dict(raw["environments"][active_env])

    # Computed values (same naming as Terraform) so you can use them in scripts
    prefix = data.get("prefix", "mlapp")
    environment = data.get("environment", "dev")
    project_id = data.get("project_id", "")
    region = data.get("region", "")

    data["data_bucket"] = f"{prefix}-{environment}-data-{project_id}"
    data["artifacts_bucket"] = f"{prefix}-{environment}-artifacts-{project_id}"
    data["artifact_repo_url"] = f"{region}-docker.pkg.dev/{project_id}/{prefix}-{environment}-repo"
    data["cicd_service_account"] = f"{prefix}-{environment}-cicd@{project_id}.iam.gserviceaccount.com"
    data["runtime_service_account"] = f"{prefix}-{environment}-runtime@{project_id}.iam.gserviceaccount.com"

    return data
