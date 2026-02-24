# Read master config from repo root. Single source of truth for Terraform and ML.
locals {
  _raw = yamldecode(file("${path.module}/../config.yaml"))
  config = {
    project_id                  = local._raw.project_id
    region                      = local._raw.region
    environment                 = local._raw.environment
    prefix                      = local._raw.prefix
    labels                      = try(local._raw.labels, {})
    dataset_id                  = local._raw.dataset_id
    table_id                    = local._raw.table_id
    dataset_location            = local._raw.dataset_location
    dataset_delete_on_destroy   = try(local._raw.dataset_delete_on_destroy, false)
    table_schema               = local._raw.table_schema
    bucket_storage_class       = try(local._raw.bucket_storage_class, "STANDARD")
    bucket_force_destroy       = try(local._raw.bucket_force_destroy, false)
    artifacts_retention_days    = try(local._raw.artifacts_retention_days, 30)
    data_retention_days        = try(local._raw.data_retention_days, 7)
    artifact_format            = try(local._raw.artifact_format, "DOCKER")
    artifact_description       = try(local._raw.artifact_description, "Artifact repository")
    cicd_roles = try(local._raw.cicd_roles, [
      "roles/storage.admin",
      "roles/artifactregistry.admin",
      "roles/bigquery.dataEditor",
      "roles/bigquery.jobUser",
      "roles/iam.serviceAccountUser"
    ])
    runtime_roles = try(local._raw.runtime_roles, [
      "roles/storage.objectViewer",
      "roles/bigquery.dataViewer",
      "roles/bigquery.jobUser"
    ])
  }
}
