# Terraform Implementation Guide <img src="./logo.png" alt="DataNeurus logo" align="right" width="150" />

## Terraform + CI/CD: Infrastructure as Code for ML/AI/Data Projects

> **Document Type:** Internal Engineering Reference  
> **Audience:** Engineers new to Infrastructure as Code (beginner → intermediate)  
> **Status:** 🟡 Active Template — Under Review  
> **Last Updated:** 26-02-2026

---

## Table of Contents

1. [Introduction](1-introduction.md)
2. [Why Terraform Instead of Python + GCP SDK](2-why-terraform-python-gcp-sdk.md)
3. [Responsibility Split: Terraform vs CI/CD](3-responsibility-split-terraform-cicd.md)
4. [Terraform Project Structure](4-terraform-project-structure.md)
5. [Terraform Code Walkthrough](5-terraform-code-walkthrough.md)
6. [Terraform Workflow](6-terraform-workflow.md)
7. [CI/CD Integration](7-cicd-integration.md)
8. [Maintenance & Scaling](8-maintenance-scaling.md)
9. [Quick Reference Cheatsheet](9-quick-reference-cheatsheet.md)

---

**Part 5 · Terraform Code Walkthrough** · [← Index](README.md)

---

## 5. Terraform Code Walkthrough

Let's walk through a realistic, minimal example of the Terraform code used in a DataNeurus ML project. Every block is explained in plain English.

### 5.1 Provider Configuration

```hcl
# terraform/main.tf

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.5"
}

provider "google" {
  project = local.config.project_id
  region  = local.config.region
}
```

> 📖 **Explanation:**
> - `terraform {}` block declares which providers (cloud APIs) we need. Think of providers as plugins.
> - `provider "google"` configures the GCP plugin. We tell it *which project* to use and *which region*.
> - `local.config.project_id` and `local.config.region` come from `config.tf` — which in turn reads `config.yaml`.

---

### 5.2 GCS Bucket — Data Storage

```hcl
resource "google_storage_bucket" "data" {
  name          = "${local.config.prefix}-${local.config.environment}-data-${local.config.project_id}"
  location      = local.config.region
  storage_class = "STANDARD"
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = local.config.data_retention_days  # e.g., 90 days
    }
    action {
      type = "Delete"
    }
  }

  labels = local.config.labels
}
```

> 📖 **Explanation line by line:**
> - `resource "google_storage_bucket" "data"` — creates a GCS bucket. `"data"` is our local name for it in Terraform.
> - `name` — the globally unique name. We build it from prefix + env + "data" + project_id to ensure uniqueness.
> - `location` — GCP region from config.
> - `uniform_bucket_level_access` — security best practice: bucket-level permissions instead of per-object.
> - `lifecycle_rule` — automatically deletes objects older than `data_retention_days`. No manual cleanup needed.
> - `labels` — metadata tags for cost tracking and organization.

---

### 5.3 BigQuery Dataset and Table

```hcl
resource "google_bigquery_dataset" "dataset" {
  dataset_id                  = local.config.dataset_id
  location                    = local.config.region
  delete_contents_on_destroy  = true
  labels                      = local.config.labels
}

resource "google_bigquery_table" "table" {
  dataset_id         = google_bigquery_dataset.dataset.dataset_id  # References the dataset above
  table_id           = local.config.table_id
  deletion_protection = false

  schema = jsonencode(local.config.table_schema)  # Schema comes from config.yaml!
}
```

> 📖 **Explanation:**
> - `google_bigquery_dataset.dataset` creates the container (like a database schema).
> - `google_bigquery_table.table` creates the table inside it.
> - Notice `dataset_id = google_bigquery_dataset.dataset.dataset_id` — this is how Terraform resources **reference each other**. Terraform knows to create the dataset first.
> - `jsonencode(local.config.table_schema)` converts the YAML-defined schema into JSON. Your schema is defined in `config.yaml` — no duplication.

---

### 5.4 Artifact Registry

```hcl
resource "google_artifact_registry_repository" "repo" {
  location      = local.config.region
  repository_id = "${local.config.prefix}-${local.config.environment}-repo"
  format        = "DOCKER"
  labels        = local.config.labels
}
```

> 📖 **Explanation:**
> - Creates a Docker image registry in GCP (where CI/CD will push built images).
> - `format = "DOCKER"` — this is a Docker registry, not Maven or npm.
> - Named with prefix + env (e.g., `mlapp-dev-repo`).

---

### 5.5 Service Accounts and IAM

```hcl
resource "google_service_account" "cicd" {
  account_id   = "${local.config.prefix}-${local.config.environment}-cicd"
  display_name = "CI/CD Service Account (${local.config.environment})"
}

resource "google_service_account" "runtime" {
  account_id   = "${local.config.prefix}-${local.config.environment}-runtime"
  display_name = "Cloud Run Runtime SA (${local.config.environment})"
}

# Grant CI/CD SA the roles defined in config.yaml (varies by env!)
resource "google_project_iam_member" "cicd_roles" {
  for_each = toset(local.config.cicd_roles)

  project = local.config.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cicd.email}"
}
```

> 📖 **Explanation:**
> - **Service accounts** are identities for non-human actors (CI/CD pipelines, Cloud Run services).
> - `cicd` SA runs the GitHub Actions jobs. `runtime` SA runs the deployed Cloud Run service.
> - `for_each = toset(local.config.cicd_roles)` creates one IAM binding for each role listed in `config.yaml`.
> - Because `cicd_roles` is different for dev/qa vs prod (prod has tighter permissions), the IAM automatically adjusts per environment. No extra code needed.

---

### 5.6 Outputs

```hcl
output "project_id"              { value = local.config.project_id }
output "region"                  { value = local.config.region }
output "artifact_repo_url"       { value = "${local.config.region}-docker.pkg.dev/${local.config.project_id}/${google_artifact_registry_repository.repo.repository_id}" }
output "artifacts_bucket"        { value = google_storage_bucket.artifacts.name }
output "data_bucket"             { value = google_storage_bucket.data.name }
output "dataset_id"              { value = google_bigquery_dataset.dataset.dataset_id }
output "table_id"                { value = google_bigquery_table.table.table_id }
output "cicd_service_account"    { value = google_service_account.cicd.email }
output "runtime_service_account" { value = google_service_account.runtime.email }
```

> 📖 **Explanation:**
> - Outputs are values Terraform exposes after a successful `apply`.
> - These are captured into `terraform-output.json` and read by CI/CD.
> - **No secrets here** — just resource names and IDs.

---

[← Previous: Terraform Project Structure](4-terraform-project-structure.md) · [Index](README.md) · [Next: Terraform Workflow →](6-terraform-workflow.md)
