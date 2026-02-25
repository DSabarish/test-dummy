# Read master config from repo root. Single source of truth for Terraform and ML.
# Config has active_env + environments.{dev,qa,prod}. Override active env via -var="active_env=qa".

variable "active_env" {
  description = "Override active environment (dev|qa|prod). If not set, config.yaml active_env is used."
  type        = string
  default     = null
}

locals {
  _raw = yamldecode(file("${path.module}/../config.yaml"))
  # Resolve active env: CLI -var wins, else value in config.yaml
  _env = coalesce(var.active_env, local._raw.active_env)
  # Selected environment block (must exist in config.yaml)
  _cfg = local._raw.environments[local._env]

  config = {
    project_id                = local._cfg.project_id
    region                    = local._cfg.region
    environment               = local._cfg.environment
    prefix                    = local._cfg.prefix
    labels                    = try(local._cfg.labels, {})
    dataset_id                = local._cfg.dataset_id
    table_id                  = local._cfg.table_id
    dataset_location          = local._cfg.dataset_location
    dataset_delete_on_destroy = try(local._cfg.dataset_delete_on_destroy, false)
    table_schema              = local._cfg.table_schema
    bucket_storage_class      = try(local._cfg.bucket_storage_class, "STANDARD")
    bucket_force_destroy      = try(local._cfg.bucket_force_destroy, false)
    artifacts_retention_days  = try(local._cfg.artifacts_retention_days, 30)
    data_retention_days       = try(local._cfg.data_retention_days, 7)
    artifact_format           = try(local._cfg.artifact_format, "DOCKER")
    artifact_description      = try(local._cfg.artifact_description, "Artifact repository")
    # IAM: per-env block first, then top-level in config, then default
    cicd_roles = try(local._cfg.cicd_roles, try(local._raw.cicd_roles, [
      "roles/storage.admin",
      "roles/artifactregistry.admin",
      "roles/bigquery.dataEditor",
      "roles/bigquery.jobUser",
      "roles/iam.serviceAccountUser",
      "roles/run.admin"
    ]))
    runtime_roles = try(local._cfg.runtime_roles, try(local._raw.runtime_roles, [
      "roles/storage.objectViewer",
      "roles/bigquery.dataViewer",
      "roles/bigquery.jobUser"
    ]))
  }
}
