# terraform\main.tf

############################################
# Terraform + Provider
############################################

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = local.config.project_id
  region  = local.config.region
}

# Variables come from root config.yaml (see config.tf). Do not use -var-file.
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@


############################################
# ARTIFACT REGISTRY
############################################

resource "google_artifact_registry_repository" "repo" {
  location      = local.config.region
  repository_id = "${local.config.prefix}-${local.config.environment}-repo"
  description   = local.config.artifact_description
  format        = local.config.artifact_format
  labels        = local.config.labels
}

############################################
# BIGQUERY
############################################

resource "google_bigquery_dataset" "dataset" {
  dataset_id                 = local.config.dataset_id
  location                   = local.config.dataset_location
  delete_contents_on_destroy = local.config.dataset_delete_on_destroy
  labels                     = local.config.labels
}

resource "google_bigquery_table" "table" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = local.config.table_id
  project    = local.config.project_id

  deletion_protection = false
  schema              = jsonencode(local.config.table_schema)

  labels = local.config.labels
}

############################################
# GCS BUCKETS
############################################

resource "google_storage_bucket" "artifacts" {
  name                        = "${local.config.prefix}-${local.config.environment}-artifacts-${local.config.project_id}"
  location                    = local.config.region
  storage_class               = local.config.bucket_storage_class
  force_destroy               = local.config.bucket_force_destroy
  uniform_bucket_level_access = true
  labels                      = local.config.labels

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = local.config.artifacts_retention_days
    }
  }
}

resource "google_storage_bucket" "data" {
  name                        = "${local.config.prefix}-${local.config.environment}-data-${local.config.project_id}"
  location                    = local.config.region
  storage_class               = local.config.bucket_storage_class
  force_destroy               = local.config.bucket_force_destroy
  uniform_bucket_level_access = true
  labels                      = local.config.labels

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = local.config.data_retention_days
    }
  }
}

############################################
# IAM
############################################

resource "google_service_account" "cicd" {
  account_id   = "${local.config.prefix}-${local.config.environment}-cicd"
  display_name = "CI/CD SA (${local.config.environment})"
}

resource "google_service_account" "runtime" {
  account_id   = "${local.config.prefix}-${local.config.environment}-runtime"
  display_name = "Runtime SA (${local.config.environment})"
}

resource "google_project_iam_member" "cicd_roles" {
  for_each = toset(local.config.cicd_roles)

  project = local.config.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cicd.email}"
}

resource "google_project_iam_member" "runtime_roles" {
  for_each = toset(local.config.runtime_roles)

  project = local.config.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

############################################
# OUTPUTS (used by CI/CD via terraform/outputs.json)
############################################

output "project_id" {
  value = local.config.project_id
}

output "region" {
  value = local.config.region
}

output "table_id" {
  value = local.config.table_id
}

output "artifact_repo_url" {
  value = "${google_artifact_registry_repository.repo.location}-docker.pkg.dev/${local.config.project_id}/${google_artifact_registry_repository.repo.repository_id}"
}

output "artifacts_bucket" {
  value = google_storage_bucket.artifacts.name
}

output "data_bucket" {
  value = google_storage_bucket.data.name
}

output "dataset_id" {
  value = google_bigquery_dataset.dataset.dataset_id
}

output "cicd_service_account" {
  value = google_service_account.cicd.email
}

output "runtime_service_account" {
  value = google_service_account.runtime.email
}

