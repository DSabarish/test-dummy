"""Load config from repo root config.yaml (single source for Terraform and ML)."""
from pathlib import Path

import yaml


def _repo_root() -> Path:
    """Repo root: directory that contains ML-code/ and config.yaml."""
    # This file is ML-code/config_loader.py, so parent is ML-code, parent.parent is repo root.
    root = Path(__file__).resolve().parent.parent
    return root


def load_config() -> dict:
    """Load config from repo root config.yaml. Adds computed keys for ML (buckets, SAs, repo URL)."""
    root = _repo_root()
    config_path = root / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"config.yaml not found at {config_path}. "
            "Create it at repo root (single source for Terraform and ML)."
        )
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("config.yaml must contain a mapping at the top level.")

    # feature_columns = table_schema names except target_column; target_column stays as-is
    target = data.get("target_column")
    if "table_schema" in data and isinstance(data["table_schema"], list):
        all_names = [c.get("name") for c in data["table_schema"] if c.get("name")]
        data["feature_columns"] = [n for n in all_names if n != target] if target else all_names
    elif "feature_columns" not in data:
        data["feature_columns"] = []

    # Computed values (same naming as Terraform) so ML code can use data_bucket, etc.
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
