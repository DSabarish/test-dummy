"""
Template pipeline script: only prints variables from config (and CI env) to show they are callable.
Replace this with your real ML steps; keep using config_loader and the same variable names.

Variables you can use in this file (from config.yaml via config_loader):
  - project_id, region, environment, prefix
  - dataset_id, table_id, dataset_location
  - data_bucket, artifacts_bucket, artifact_repo_url
  - cicd_service_account, runtime_service_account
  - table_schema, target_column, feature_columns
  - data_gcs_prefix, models_gcs_prefix, model_filename, latest_subfolder
  - (and any other keys in the active environment block in config.yaml)

In CI/CD, Terraform outputs are also loaded into env vars (GCP_PROJECT, DATA_BUCKET, etc.);
you can use os.environ["GCP_PROJECT"] etc. when running in GitHub Actions.
"""
import os

from config_loader import load_config


def run():
    cfg = load_config()

    print("=== Config variables (from config.yaml) — properly callable ===")
    print("project_id       ", cfg.get("project_id"))
    print("region           ", cfg.get("region"))
    print("environment      ", cfg.get("environment"))
    print("prefix           ", cfg.get("prefix"))
    print("dataset_id       ", cfg.get("dataset_id"))
    print("table_id         ", cfg.get("table_id"))
    print("data_bucket      ", cfg.get("data_bucket"))
    print("artifacts_bucket ", cfg.get("artifacts_bucket"))
    print("artifact_repo_url", cfg.get("artifact_repo_url"))

    print("\n=== Env vars (set by CI from terraform-output.json when present) ===")
    for name in ["GCP_PROJECT", "DATA_BUCKET", "ARTIFACTS_BUCKET", "DATASET_ID", "TABLE_ID"]:
        val = os.environ.get(name, "<not set>")
        print(f"{name:20} {val}")

    print("\nDone. Replace this script with your real pipeline; use cfg['...'] and env vars above.")


if __name__ == "__main__":
    run()
