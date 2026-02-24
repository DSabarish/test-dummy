# Optional: export env-style vars from master config (no GCP, no state).
# Use when infra already exists and you only need ml_app_env.txt.
# Run from here: terraform init && terraform apply -auto-approve

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    local = { source = "hashicorp/local", version = "~> 2.0" }
  }
}

locals {
  _raw             = yamldecode(file("${path.module}/../../config.yaml"))
  data_bucket      = "${local._raw.prefix}-${local._raw.environment}-data-${local._raw.project_id}"
  artifacts_bucket = "${local._raw.prefix}-${local._raw.environment}-artifacts-${local._raw.project_id}"
  repo_id          = "${local._raw.prefix}-${local._raw.environment}-repo"
  artifact_repo_url = "${local._raw.region}-docker.pkg.dev/${local._raw.project_id}/${local.repo_id}"
  cicd_email       = "${local._raw.prefix}-${local._raw.environment}-cicd@${local._raw.project_id}.iam.gserviceaccount.com"
  runtime_email    = "${local._raw.prefix}-${local._raw.environment}-runtime@${local._raw.project_id}.iam.gserviceaccount.com"
}

resource "local_file" "ml_env" {
  filename = "${path.module}/ml_app_env.txt"
  content  = <<-EOT
GCP_PROJECT=${local._raw.project_id}
GCP_REGION=${local._raw.region}
DATA_BUCKET=${local.data_bucket}
ARTIFACTS_BUCKET=${local.artifacts_bucket}
DATASET_ID=${local._raw.dataset_id}
TABLE_ID=${local._raw.table_id}
ARTIFACT_REPO_URL=${local.artifact_repo_url}
CICD_SERVICE_ACCOUNT=${local.cicd_email}
RUNTIME_SERVICE_ACCOUNT=${local.runtime_email}
EOT
}
