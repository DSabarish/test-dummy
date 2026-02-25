# Terraform Implementation Guide <img src="./logo.png" alt="DataNeurus logo" align="right" width="150" />

## Terraform + CI/CD: Infrastructure as Code for ML/AI/Data Projects

> **Document Type:** Internal Engineering Reference  
> **Audience:** Engineers new to Infrastructure as Code (beginner → intermediate)  
> **Status:** 🟢 Active Template — Reusable across all DataNeurus projects  
> **Last Updated:** 2025

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

**Part 2 · Why Terraform Instead of Python + GCP SDK** · [← Index](README.md)

---

## 2. Why Terraform Instead of Python + GCP SDK

When engineers first encounter cloud infrastructure, a natural question arises:

> "I already know Python. Can't I just use `google-cloud-storage` and `google-cloud-bigquery` to create my buckets and datasets?"

The short answer is: **yes, technically — but it leads to serious problems at scale.** Here's why.

---

### 2.1 Imperative vs Declarative Infrastructure

This is the most fundamental difference.

#### Imperative (Python + GCP SDK) — "Tell me *how* to do it"

```python
# Imperative: step-by-step instructions
bucket = storage.Bucket("my-bucket")
bucket.storage_class = "STANDARD"
bucket.location = "asia-south1"
client.create_bucket(bucket)
```

You are writing a *procedure*. You must handle every case:
- What if the bucket already exists?
- What if the creation fails halfway through?
- What if someone deletes the bucket outside your script?
- How do you update it without destroying it?

#### Declarative (Terraform) — "Tell me *what* you want"

```hcl
# Declarative: describe the desired end state
resource "google_storage_bucket" "data" {
  name     = "mlapp-dev-data-my-project"
  location = "asia-south1"
  storage_class = "STANDARD"
}
```

You are describing *what the world should look like*. Terraform figures out *how* to get there. It handles:
- Already exists → do nothing or update
- Partially failed → roll back safely
- Deleted outside Terraform → recreate it
- Need to update → compute minimal diff and apply

| | Imperative (Python) | Declarative (Terraform) |
|---|---|---|
| You specify | *How* to do it | *What* you want |
| Idempotency | Manual (you write the checks) | Built-in |
| Handles existing resources | Manual | Automatic |
| Diff detection | Manual | Built-in (`plan`) |
| State tracking | None | `.tfstate` file |

> 💡 **Idempotency** means running the same command twice gives the same result. "Create bucket if not exists" is idempotent. "Create bucket" is not — it fails the second time.

---

### 2.2 State Management

Terraform maintains a **state file** (`terraform.tfstate`) that records every resource it has ever created. This file is the single source of truth for "what Terraform knows about the world."

```
┌─────────────────────────────────────────────────────┐
│                  Terraform State                     │
│                                                     │
│  google_storage_bucket.data:                        │
│    name     = "mlapp-dev-data-my-project"           │
│    location = "asia-south1"                         │
│    id       = "mlapp-dev-data-my-project"           │
│                                                     │
│  google_bigquery_dataset.dataset:                   │
│    dataset_id = "training_dataset_dev"              │
│    location   = "asia-south1"                       │
│    id         = "projects/my-project/datasets/..."  │
└─────────────────────────────────────────────────────┘
```

Without state management (as with Python scripts), you have no memory of what was created, how it was configured, or how to modify it safely. Python scripts operate blindly.

---

### 2.3 Drift Detection

Terraform can detect when the real world has diverged from your declared state:

```bash
terraform plan
```

```
# google_storage_bucket.data will be updated in-place
  ~ resource "google_storage_bucket" "data" {
      ~ storage_class = "STANDARD" -> "NEARLINE"  # Someone changed this in the console!
    }
```

This is **drift detection**. Terraform shows you exactly what changed and lets you decide whether to revert it or update your code to match.

Python scripts have no equivalent. You would have to write your own comparison logic.

---

### 2.4 Reproducibility

With Terraform, creating the exact same infrastructure in a new project is a single command:

```bash
terraform apply -var="active_env=prod"
```

With Python scripts, you would need to:
1. Run scripts in the right order
2. Handle errors and partial states
3. Ensure environment variables are set correctly
4. Hope nothing changed since the scripts were written

---

### 2.5 Team Collaboration

Terraform code lives in Git. Multiple engineers can:
- Review infrastructure changes in pull requests, just like application code
- See the full history of every infrastructure change
- Propose changes via branches and merge requests
- Know exactly what changed and why (from commit messages)

Python scripts can live in Git too, but without state management, two engineers running the same script can create duplicate resources or race conditions.

---

### 2.6 When Python/GCP SDK is Still the Right Choice

> **Terraform is not for everything.** Here is a clear guide on when to use each:

| Use Case | Tool | Why |
|---|---|---|
| Creating GCS buckets, BQ datasets, IAM | **Terraform** | Declarative, stateful, reproducible |
| Enabling GCP APIs | **Terraform** | Idempotent, tracked |
| Uploading data to GCS | **Python + SDK** | Operational task, not infrastructure |
| Querying BigQuery | **Python + SDK** | Data task, not infrastructure |
| Training a model | **Python** | Application logic |
| Running ML pipelines | **Python + CI/CD** | Application automation |
| Dynamic resource creation (e.g., creating 100 tables based on data) | **Python + SDK** | Terraform is not built for data-driven loops |
| One-off emergency fixes | **gcloud CLI** | Speed over process |

> 📌 **Rule of thumb:** If a resource needs to *persist* across runs and *be tracked*, use Terraform. If it is *transient* or *data-driven*, use Python.

---

[← Previous: Introduction](1-introduction.md) · [Index](README.md) · [Next: Responsibility Split →](3-responsibility-split-terraform-cicd.md)
