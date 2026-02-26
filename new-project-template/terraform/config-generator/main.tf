# Optional: export env-style vars from master config (no GCP, no state).
# Use when infra already exists and you only need ml_app_env.txt.
# Run from here: terraform init && terraform apply -auto-approve
# For a specific env: terraform apply -auto-approve -var="active_env=qa"
# Expects config.yaml at repo root (../../config.yaml).

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    local = { source = "hashicorp/local", version = "~> 2.0" }
  }
}

variable "active_env" {
  description = "Environment to use (dev|qa|prod). Defaults to config.yaml active_env."
  type        = string
  default     = null
}

locals {
  _raw   = yamldecode(file("${path.module}/../../config.yaml"))
  _env   = coalesce(var.active_env, local._raw.active_env)
  _cfg   = local._raw.environments[local._env]
  data_bucket      = "${local._cfg.prefix}-${local._cfg.environment}-data-${local._cfg.project_id}"
  artifacts_bucket = "${local._cfg.prefix}-${local._cfg.environment}-artifacts-${local._cfg.project_id}"
  repo_id          = "${local._cfg.prefix}-${local._cfg.environment}-repo"
  artifact_repo_url = "${local._cfg.region}-docker.pkg.dev/${local._cfg.project_id}/${local.repo_id}"
  cicd_email       = "${local._cfg.prefix}-${local._cfg.environment}-cicd@${local._cfg.project_id}.iam.gserviceaccount.com"
  runtime_email    = "${local._cfg.prefix}-${local._cfg.environment}-runtime@${local._cfg.project_id}.iam.gserviceaccount.com"
}

resource "local_file" "ml_env" {
  filename = "${path.module}/ml_app_env.txt"
  content  = <<-EOT
GCP_PROJECT=${local._cfg.project_id}
GCP_REGION=${local._cfg.region}
DATA_BUCKET=${local.data_bucket}
ARTIFACTS_BUCKET=${local.artifacts_bucket}
DATASET_ID=${local._cfg.dataset_id}
TABLE_ID=${local._cfg.table_id}
ARTIFACT_REPO_URL=${local.artifact_repo_url}
CICD_SERVICE_ACCOUNT=${local.cicd_email}
RUNTIME_SERVICE_ACCOUNT=${local.runtime_email}
EOT
}
