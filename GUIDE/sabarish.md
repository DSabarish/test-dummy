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

## 1. Introduction

### 1.1 What is CI/CD?

**CI/CD** stands for **Continuous Integration / Continuous Delivery (or Deployment)**. It is a set of practices and tools that automate the software lifecycle — from writing code to testing it, to deploying it to production.

```
Developer writes code
        │
        ▼
┌───────────────────┐
│  Push to GitHub   │  ◄── Triggers the CI/CD pipeline automatically
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  CI: Test & Build │  ◄── Run tests, lint, validate
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  CD: Deploy       │  ◄── Push to Cloud Run, update containers, etc.
└───────────────────┘
        │
        ▼
    ✅ Live in production
```

Think of CI/CD as a **robot colleague** that automatically checks your work and deploys it every time you push code — removing the need for manual, error-prone steps.

---

### 1.2 Why CI/CD is Important for ML/AI/Data Projects

ML/AI/Data projects are uniquely complex. Unlike a traditional web app, they involve:

- **Data pipelines** that pull from multiple sources
- **Model training** runs that depend on GCS buckets, BigQuery datasets, and service accounts existing *before* the code runs
- **Multiple environments** — dev, qa, and prod — each with different projects, permissions, and resources
- **Frequent iteration** — data scientists push code daily; infrastructure must keep up

> ⚠️ **Without CI/CD**, every model update or pipeline change requires:
> - Manual SSH into a server
> - Running scripts by hand
> - Hoping nothing was forgotten
> - Praying the environment is the same as last week

CI/CD solves this by making deployments **repeatable, automated, and auditable**. Every change is tracked in Git, every deploy is logged, and every failure is caught early.

---

### 1.3 Common Problems When Using CI/CD Alone

CI/CD is excellent at automating *application* deployment — but it was not designed to manage *infrastructure*. When teams try to use CI/CD alone (without a tool like Terraform), they hit a familiar set of problems:

#### ❌ Problem 1: Manual Infrastructure Creation

```
Engineer A: "I'll just create the BigQuery dataset manually in the console."
Engineer B (3 months later): "Wait, why does prod have a dataset called 'training_v2_old'?"
```

Manually created resources are not tracked anywhere. They exist in the cloud but not in code.

#### ❌ Problem 2: Configuration Drift

Drift happens when the **actual state** of your infrastructure slowly diverges from the **expected state**. Example:

- You intended `dev` and `prod` to have identical bucket configurations
- Someone adds a lifecycle rule to `prod` via the console
- Now `dev` and `prod` are different — but nobody knows
- A bug appears in `prod` that doesn't happen in `dev`

Drift is **silent and cumulative**. It builds up over months until something breaks.

#### ❌ Problem 3: Reproducibility Issues

> "It works on my machine (and in dev). I have no idea why prod is broken."

If infrastructure was created by hand, spinning up a new environment means following a checklist — and checklists drift too. You may forget a permission, a bucket, or a BigQuery table schema. The new environment is never *exactly* like the original.

#### ❌ Problem 4: No Audit Trail

Who created that service account? When was that IAM role added? Why does `qa` have admin permissions? If infrastructure is managed manually, **there is no history**. With Terraform, every infrastructure change is a Git commit.

#### ❌ Problem 5: Onboarding New Projects is Slow

Starting a new ML project means:
1. Manually creating a GCP project
2. Enabling APIs one by one
3. Creating buckets, datasets, service accounts
4. Writing down the steps (probably imperfectly)
5. Repeating for dev, qa, prod

This takes days. With Terraform, it takes minutes.

---

### 1.4 How Terraform Complements CI/CD

Terraform fills the gap that CI/CD leaves open: **infrastructure management**.

```
┌─────────────────────────────────────────────────────────────┐
│                    DataNeurus Platform                       │
├─────────────────────────────┬───────────────────────────────┤
│         TERRAFORM           │           CI/CD               │
│   "Build the foundation"    │   "Deploy what runs on it"    │
├─────────────────────────────┼───────────────────────────────┤
│  • GCS Buckets              │  • Run ML pipeline            │
│  • BigQuery datasets/tables │  • Build Docker image         │
│  • Artifact Registry        │  • Deploy to Cloud Run        │
│  • Service Accounts + IAM   │  • Run tests                  │
│  • APIs enabled             │  • Promote dev → qa → prod    │
└─────────────────────────────┴───────────────────────────────┘
```

Together, they form a **complete, automated system** where:

1. **Terraform** creates and maintains the cloud infrastructure
2. **Terraform outputs** (non-secret values like bucket names, project IDs) are passed to CI/CD
3. **CI/CD** uses those values to run pipelines and deployments

> 💡 **The key insight:** Terraform is *not* a replacement for CI/CD. It is the layer underneath it. CI/CD deploys *applications*. Terraform manages the *infrastructure those applications run on*.

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

## 3. Responsibility Split: Terraform vs CI/CD

One of the most important architectural decisions in any DataNeurus project is understanding **who owns what**. Blurring this boundary leads to confusion, duplication, and fragility.

### 3.1 The Core Principle

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│   TERRAFORM = "Build the stage"                              │
│   CI/CD     = "Run the show"                                 │
│                                                              │
│   Terraform creates the INFRASTRUCTURE.                      │
│   CI/CD uses that infrastructure to run APPLICATIONS.        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Responsibility Comparison Table

| Concern | Owner | Why |
|---|---|---|
| GCS Bucket (data) | **Terraform** | Persistent resource, needs state tracking |
| GCS Bucket (artifacts) | **Terraform** | Persistent resource, needs state tracking |
| BigQuery Dataset | **Terraform** | Persistent resource, schema-managed |
| BigQuery Table | **Terraform** | Schema lives in `config.yaml`, managed declaratively |
| Artifact Registry (Docker repo) | **Terraform** | Persistent resource |
| Service Accounts | **Terraform** | IAM is security-critical; must be versioned |
| IAM Roles & Bindings | **Terraform** | Security policy must be auditable |
| GCP APIs (enablement) | **Terraform** | One-time setup, tracked in state |
| Cloud Run Service | **CI/CD** | Application concern; image changes with every deploy |
| Docker image build | **CI/CD** | App-layer concern |
| Docker image push | **CI/CD** | App-layer concern |
| ML Pipeline execution | **CI/CD** | Operational/application concern |
| Running `pytest` | **CI/CD** | Testing is a CI/CD responsibility |
| Branch promotion (dev→qa→prod) | **CI/CD** | Workflow automation |
| Generating `terraform-output.json` | **Both** | Terraform produces it; CI/CD consumes it |

### 3.3 The Bridge: `terraform-output.json`

The handoff between Terraform and CI/CD happens through a **committed output file**:


![picture1](picture1.png)

---

```
┌─────────────────────┐          ┌──────────────────────────┐
│     TERRAFORM       │          │         CI/CD            │
│                     │  outputs │                          │
│  - Creates bucket   │ ──────►  │  - Reads bucket name     │
│  - Creates dataset  │  .json   │  - Reads dataset ID      │
│  - Creates SA       │  file    │  - Reads SA email        │
│  - Creates repo URL │          │  - Deploys Cloud Run     │
└─────────────────────┘          └──────────────────────────┘
         │                                    │
         └────────── Only secret ─────────────┘
                    = GCP_SA_KEY
```

`terraform/terraform-output.json` is:
- Generated by `terraform output -json > terraform-output.json`
- Committed to the repo (it contains **no secrets** — only names and IDs)
- Read by CI/CD jobs to avoid duplicating config in GitHub Secrets

> ✅ **This is the only "bridge" between Terraform and CI/CD. No other values should be hardcoded in GitHub Secrets (except `GCP_SA_KEY`).**

---

## 4. Terraform Project Structure

### 4.1 Standard Terraform Project Structure

Most Terraform tutorials and projects use this conventional layout:

```
terraform/
├── main.tf              # Resource definitions
├── variables.tf         # Variable declarations
├── terraform.tfvars     # Variable values
├── outputs.tf           # Output values
├── backend.tf           # Remote state configuration
└── provider.tf          # Provider (GCP, AWS, etc.)
```

| File | Purpose |
|---|---|
| `main.tf` | Where you define resources (buckets, databases, IAM) |
| `variables.tf` | Declares the inputs your Terraform accepts |
| `terraform.tfvars` | Sets the values for those variables (often gitignored for secrets) |
| `outputs.tf` | Declares values to expose after apply (e.g., bucket names) |
| `backend.tf` | Configures remote state storage (e.g., GCS bucket for `.tfstate`) |
| `provider.tf` | Configures the cloud provider (Google, AWS, Azure) |

#### The Problem with the Standard Approach for Multi-Environment Projects

With the standard approach, managing dev/qa/prod typically means one of:

**Option A: Multiple directories** (lots of duplication)
```
terraform/
├── dev/
│   ├── main.tf      # 200 lines
│   ├── variables.tf # 50 lines
│   └── tfvars       # dev values
├── qa/
│   ├── main.tf      # 200 lines — same as dev!
│   └── ...
└── prod/
    ├── main.tf      # 200 lines — same again!
    └── ...
```

**Option B: Workspaces** (complex, confusing for beginners)

Both options lead to drift between environments, duplication, and confusion.

---

### 4.2 The DataNeurus Improved Approach: Single Config File

We solve this with a **single `config.yaml` at the repo root** that holds all three environments:

```
project-root/
├── config.yaml              ◄── 🌟 ONE file, ALL environments
├── terraform/
│   ├── config.tf            ◄── Reads config.yaml, exposes local.config
│   ├── main.tf              ◄── Resources defined once, driven by local.config
│   └── terraform-output.json  ◄── Committed after apply; CI/CD reads this
└── ML-code/
    └── config_loader.py     ◄── Python reads the same config.yaml
```

#### How `config.yaml` Is Structured

```yaml
# The active environment for local runs. CI/CD overrides via branch name.
active_env: "dev"

environments:
  dev:
    project:
      project_id: "my-company-dev-001"
      region: "asia-south1"
      environment: "dev"
      prefix: "mlapp"

    terraform:
      labels:
        managed_by: "terraform"
        env: "dev"
      artifacts_retention_days: 30
      data_retention_days: 90
      cicd_roles:
        - "roles/storage.admin"
        - "roles/artifactregistry.admin"
        - "roles/bigquery.dataEditor"

    shared:
      dataset_id: "training_dataset_dev"
      table_id: "features_table"
      table_schema:
        - name: "feature_a"
          type: "FLOAT64"
        - name: "target"
          type: "INT64"

    ml:
      model_path: "models/latest"
      data_path: "data/raw"

    cicd:
      push_to_next_branch: true
      next_branch_name: "qa"

  qa:
    project:
      project_id: "my-company-qa-001"
      # ... same structure, different values ...

  prod:
    project:
      project_id: "my-company-prod-001"
      # ... same structure, tighter IAM roles ...
    cicd:
      push_to_next_branch: false   # End of the promotion chain
      next_branch_name: ""
```

#### How `config.tf` Reads It

```hcl
# terraform/config.tf

variable "active_env" {
  description = "Override the active environment. If empty, uses active_env from config.yaml."
  type        = string
  default     = ""
}

locals {
  _raw = yamldecode(file("../config.yaml"))
  _env = coalesce(var.active_env, local._raw.active_env)
  _cfg = local._raw.environments[local._env]

  config = {
    project_id              = local._cfg.project.project_id
    region                  = local._cfg.project.region
    environment             = local._cfg.project.environment
    prefix                  = local._cfg.project.prefix
    dataset_id              = local._cfg.shared.dataset_id
    table_id                = local._cfg.shared.table_id
    table_schema            = local._cfg.shared.table_schema
    cicd_roles              = local._cfg.terraform.cicd_roles
    artifacts_retention_days = local._cfg.terraform.artifacts_retention_days
    # ... and so on
  }
}
```

#### Benefits of This Approach

| Concern | Standard Approach | DataNeurus Approach |
|---|---|---|
| Number of config files | 3+ (one per env) | 1 (`config.yaml`) |
| Seeing dev vs prod differences | Open two files, compare | Visible side-by-side in one file |
| Risk of env drift | High | Low — all envs are in one place |
| Switching environments | Change directory or workspace | `terraform apply -var="active_env=qa"` |
| ML code reads same config? | No — separate config needed | Yes — `config_loader.py` reads same file |

---

### 4.3 Environment Selection

| Who runs it | How environment is selected |
|---|---|
| **Terraform (local)** | `active_env` in `config.yaml` (default), or `-var="active_env=qa"` (override) |
| **Terraform (CI/CD)** | `-var="active_env=${{ github.ref_name }}"` (branch name = env) |
| **ML code (local)** | `active_env` in `config.yaml` |
| **ML code (CI/CD)** | `ACTIVE_ENV` environment variable set from branch name |

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

## 6. Terraform Workflow

The Terraform workflow follows four core commands. Here is a detailed walkthrough of each.

### 6.1 Workflow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   TERRAFORM WORKFLOW                            │
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐  │
│   │   INIT   │───►│   PLAN   │───►│  APPLY   │───►│OUTPUTS  │  │
│   └──────────┘    └──────────┘    └──────────┘    └─────────┘  │
│   Download        Preview          Create/Update  Export JSON  │
│   providers       changes          resources      for CI/CD    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 6.2 `terraform init` — Initialize the Working Directory

```bash
cd terraform/
terraform init -reconfigure
```

**What it does internally:**
1. Downloads the **Google provider plugin** (the GCP API adapter)
2. Sets up the local working directory (`.terraform/` folder)
3. Configures the **backend** (where state is stored)
4. `-reconfigure` forces re-initialization, useful when switching projects

**When to run it:**
- First time setting up
- After changing provider versions
- After switching GCP projects (use `-reconfigure`)

**Expected output:**
```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/google versions matching "~> 5.0"...
- Installing hashicorp/google v5.20.0...

Terraform has been successfully initialized!
```

> ⚠️ If you switch from one GCP project to another, always run `terraform init -reconfigure` and delete `terraform.tfstate` first (if you want a clean slate).

---

### 6.3 `terraform plan` — Preview Changes (Non-destructive)

```bash
terraform plan -var="active_env=dev"
```

**What it does internally:**
1. Reads your `.tf` files
2. Reads the current state (from `terraform.tfstate`)
3. Calls GCP APIs to check the **real current state** of resources
4. Computes the **diff** between desired and actual
5. Prints a human-readable summary of what *would* change

**Always run this before apply.** It is completely safe — it changes nothing.

**Reading the plan output:**

```
  # google_storage_bucket.data will be created
  + resource "google_storage_bucket" "data" {
      + name     = "mlapp-dev-data-my-project-001"
      + location = "asia-south1"
      ...
    }

  # google_bigquery_dataset.dataset will be updated in-place
  ~ resource "google_bigquery_dataset" "dataset" {
      ~ description = "old description" -> "new description"
    }

Plan: 3 to add, 1 to change, 0 to destroy.
```

| Symbol | Meaning |
|---|---|
| `+` | Resource will be **created** |
| `~` | Resource will be **updated** (in-place) |
| `-` | Resource will be **destroyed** |
| `-/+` | Resource will be **destroyed and recreated** (careful!) |

---

### 6.4 `terraform apply` — Create or Update Infrastructure

```bash
terraform apply -var="active_env=dev"
```

**What it does internally:**
1. Runs `plan` one more time
2. Displays the plan and asks for confirmation
3. You type `yes` to proceed
4. Calls GCP APIs to create/update/delete resources
5. Saves the new state to `terraform.tfstate`

**After apply, generate the outputs file:**

```bash
# From terraform/ directory
terraform output -json > terraform-output.json

# Then commit it
git add terraform-output.json
git commit -m "chore: update Terraform outputs for CI/CD [dev]"
git push
```

> 🔴 **Critical:** `terraform-output.json` must be committed and up to date. If it is missing or stale, CI/CD jobs will fail. **Do not add it to `.gitignore`.**

---

### 6.5 `terraform destroy` — Tear Down Infrastructure

```bash
terraform destroy -var="active_env=dev"
```

**What it does:**
- Destroys **all resources** tracked in the state file for the target environment
- Asks for confirmation (type `yes`)
- Use with extreme caution in qa/prod

**When you would use it:**
- Decommissioning a dev environment
- Starting fresh after a botched setup
- Cleaning up a temporary test environment

> ⚠️ **Never run destroy on prod without explicit approval and a backup plan.**

---

### 6.6 Handling "Already Exists" Errors (409)

Sometimes you run `terraform apply` on a project that already has resources (e.g., created manually or by a previous run). You'll see:

```
Error: Error creating Bucket: googleapi: Error 409: ... already exists
```

**Solution: Import the existing resource into Terraform state:**

```bash
# Tell Terraform: "This existing GCP resource belongs to this Terraform resource"
terraform import google_storage_bucket.data mlapp-dev-data-my-project-001
terraform import google_bigquery_dataset.dataset projects/my-project-001/datasets/training_dataset_dev

# Then apply as normal (Terraform will update to match config, not recreate)
terraform apply -var="active_env=dev"
```

After importing, Terraform "knows" about the existing resource and will manage it going forward.

---

## 7. CI/CD Integration

### 7.1 How GitHub Actions Integrates with Terraform

The DataNeurus CI/CD pipeline is designed around a critical principle:

> **Terraform changes are reviewed before they are applied, just like application code.**

This is achieved through the **Pull Request → Plan, Merge → Apply** pattern.

---

### 7.2 The Full CI/CD Workflow

```
┌──────────────────────────────────────────────────────────────────────┐
│                   GITHUB ACTIONS WORKFLOW                            │
│                                                                      │
│  Trigger: push to dev / qa / prod                                    │
│                                                                      │
│  ┌─────────┐    ┌──────────────┐    ┌────────────────┐              │
│  │  test   │───►│   pipeline   │───►│    deploy      │              │
│  │         │    │              │    │                │              │
│  │ pytest  │    │ Load outputs │    │ Load outputs   │              │
│  │         │    │ Auth to GCP  │    │ Auth to GCP    │              │
│  └─────────┘    │ Run ML code  │    │ Build Docker   │              │
│                 └──────────────┘    │ Push to AR     │              │
│                                     │ gcloud run     │              │
│                                     │ deploy         │              │
│                                     └────────────────┘              │
│                                              │                      │
│                                              ▼                      │
│                                     ┌────────────────┐              │
│                                     │   push-code    │              │
│                                     │ (dev → qa →    │              │
│                                     │  prod chain)   │              │
│                                     └────────────────┘              │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 7.3 How CI/CD Reads Terraform Outputs

Each job starts by loading infrastructure values from `terraform/terraform-output.json`:

```yaml
# .github/workflows/cicd.yml (simplified)

jobs:
  pipeline:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set environment from branch
        run: echo "ACTIVE_ENV=${{ github.ref_name }}" >> $GITHUB_ENV

      - name: Load Terraform outputs
        run: |
          python3 - <<'EOF'
          import json, os

          # Read terraform-output.json (committed to repo, no secrets)
          with open("terraform/terraform-output.json", "r", encoding="utf-8-sig") as f:
              outputs = json.load(f)

          # Write to GITHUB_ENV so subsequent steps can use them
          with open(os.environ["GITHUB_ENV"], "a") as env_file:
              env_file.write(f"GCP_PROJECT={outputs['project_id']['value']}\n")
              env_file.write(f"DATA_BUCKET={outputs['data_bucket']['value']}\n")
              env_file.write(f"ARTIFACTS_BUCKET={outputs['artifacts_bucket']['value']}\n")
              env_file.write(f"DATASET_ID={outputs['dataset_id']['value']}\n")
              env_file.write(f"TABLE_ID={outputs['table_id']['value']}\n")
          EOF

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}  # The ONLY secret

      - name: Run ML Pipeline
        run: python ML-code/run_pipeline.py
        env:
          ACTIVE_ENV: ${{ env.ACTIVE_ENV }}
          GCP_PROJECT: ${{ env.GCP_PROJECT }}
          DATA_BUCKET: ${{ env.DATA_BUCKET }}
```

---

### 7.4 The Deploy Job: Cloud Run via CI/CD

```yaml
  deploy:
    needs: pipeline
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Load Terraform outputs
        run: |
          # (same pattern as pipeline job)
          # Exports: GCP_PROJECT, REGION, ARTIFACT_REPO_URL, RUNTIME_SERVICE_ACCOUNT

      - name: Auth to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Setup gcloud
        uses: google-github-actions/setup-gcloud@v2

      - name: Authenticate Docker to Artifact Registry
        run: gcloud auth configure-docker ${{ env.REGION }}-docker.pkg.dev

      - name: Build and Push Docker Image
        run: |
          IMG="${{ env.ARTIFACT_REPO_URL }}/app:${{ github.sha }}"
          docker build -t "$IMG" .
          docker push "$IMG"
          echo "IMAGE=$IMG" >> $GITHUB_ENV

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy app \
            --image "${{ env.IMAGE }}" \
            --region "${{ env.REGION }}" \
            --platform managed \
            --allow-unauthenticated \
            --service-account "${{ env.RUNTIME_SERVICE_ACCOUNT }}" \
            --set-env-vars "GCP_PROJECT=${{ env.GCP_PROJECT }},ACTIVE_ENV=${{ env.ACTIVE_ENV }}"
```

> 💡 **Notice:** Cloud Run is deployed **only via `gcloud run deploy`**. Terraform never touches Cloud Run. This is an intentional architectural boundary. Cloud Run is an "application concern" — it changes with every code push. Terraform manages "infrastructure" — things that persist and are shared.

---

### 7.5 Pull Request → Plan (Recommended Addition)

For teams wanting even more safety, add a Terraform plan step on Pull Requests:

```yaml
# Triggered on pull requests targeting dev/qa/prod
on:
  pull_request:
    branches: [dev, qa, prod]

jobs:
  terraform-plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Auth to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Terraform Init
        run: terraform -chdir=terraform init -reconfigure

      - name: Terraform Plan
        run: |
          BRANCH="${{ github.base_ref }}"
          terraform -chdir=terraform plan -var="active_env=$BRANCH"
          # Plan output is shown in the PR for review
```

This means:
- **PR opened** → `terraform plan` runs, shows what infra would change → reviewers can see it
- **PR merged** → `terraform apply` runs (or is run manually by an engineer with the output file)

**Why this prevents accidental infra changes:**
- Infrastructure changes are peer-reviewed, just like code
- No one can accidentally delete a BigQuery dataset by merging a PR without others seeing it in the plan output
- The plan output is a comment on the PR (with additional tooling like Atlantis or Terraform Cloud)

---

### 7.6 Branch = Environment Mapping

The pipeline relies on a convention where **branch name = environment name**:

```
Branch: dev   →  ACTIVE_ENV=dev   →  Uses environments.dev in config.yaml
Branch: qa    →  ACTIVE_ENV=qa    →  Uses environments.qa in config.yaml
Branch: prod  →  ACTIVE_ENV=prod  →  Uses environments.prod in config.yaml
```

**Promotion chain** (configured in `config.yaml`):

```
dev ──► qa ──► prod
         ↑         ↑
    push_to_next  push_to_next
    _branch=true  _branch=false
```

After a successful deploy to `dev`, CI/CD automatically merges code to `qa`. After `qa` succeeds, code is promoted to `prod`. This is the **GitOps promotion pattern**.

> ⚠️ **Guard:** The workflow trigger is restricted to exactly `[dev, qa, prod]`. Feature branches do not trigger the pipeline.

---

## 8. Maintenance & Scaling

### 8.1 Onboarding a New Project

Starting a new DataNeurus ML project with this template:

```
┌─────────────────────────────────────────────────────────────────┐
│              ONBOARDING A NEW PROJECT                           │
│                                                                 │
│  Step 1: Clone the template repo                                │
│    git clone https://github.com/dataneurus/ml-template          │
│                                                                 │
│  Step 2: Edit config.yaml only                                  │
│    - Set project_id for dev/qa/prod                             │
│    - Update dataset/table names                                 │
│    - Update table schema                                        │
│    - Update IAM roles if needed                                 │
│                                                                 │
│  Step 3: Run Terraform for each environment                     │
│    terraform apply -var="active_env=dev"                        │
│    terraform apply -var="active_env=qa"                         │
│    terraform apply -var="active_env=prod"                       │
│                                                                 │
│  Step 4: Export outputs for CI/CD                               │
│    terraform output -json > terraform-output.json               │
│    git add terraform-output.json && git commit && git push      │
│                                                                 │
│  Step 5: Add GCP_SA_KEY to GitHub Secrets                       │
│    (One secret, valid for the cicd service account)             │
│                                                                 │
│  Step 6: Push to dev branch → CI/CD runs automatically          │
│                                                                 │
│  Total time: ~30 minutes (vs days of manual setup)              │
└─────────────────────────────────────────────────────────────────┘
```

---

### 8.2 Creating a New Environment

Need a `staging` environment between `qa` and `prod`?

1. **Add to `config.yaml`:**

```yaml
environments:
  staging:
    project:
      project_id: "my-company-staging-001"
      region: "asia-south1"
      environment: "staging"
    # ... rest of config ...
    cicd:
      push_to_next_branch: true
      next_branch_name: "prod"  # staging → prod now
```

2. **Update the existing qa block:**

```yaml
  qa:
    cicd:
      push_to_next_branch: true
      next_branch_name: "staging"  # qa → staging now
```

3. **Apply Terraform for staging:**

```bash
terraform apply -var="active_env=staging"
terraform output -json > terraform-output.json
git add terraform-output.json && git commit -m "chore: add staging environment"
```

4. **Create the GitHub branch:**

```bash
git checkout -b staging
git push -u origin staging
```

Done. The entire promotion chain updates automatically because it reads `config.yaml`.

---

### 8.3 Updating Infrastructure Safely

Changing infrastructure (e.g., updating a BigQuery schema or adding a lifecycle rule):

```
┌─────────────────────────────────────────────────────────────┐
│             SAFE INFRASTRUCTURE UPDATE FLOW                 │
│                                                             │
│   1. Update config.yaml on a feature branch                 │
│                                                             │
│   2. terraform plan -var="active_env=dev"                   │
│      ◄── Review: does the plan look right?                 │
│          Will anything be destroyed unexpectedly?           │
│                                                             │
│   3. Open Pull Request                                      │
│      ◄── Team reviews the plan output                      │
│          Are the changes intentional?                       │
│                                                             │
│   4. terraform apply -var="active_env=dev"  (after review)  │
│                                                             │
│   5. Test in dev — does everything work?                    │
│                                                             │
│   6. Repeat for qa, then prod                               │
│      terraform apply -var="active_env=qa"                   │
│      terraform apply -var="active_env=prod"                 │
│                                                             │
│   7. Commit updated terraform-output.json for each env      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 8.4 Complete System Flowcharts

#### Terraform Workflow

```
                    ┌────────────────────┐
                    │  Edit config.yaml  │
                    └────────┬───────────┘
                             │
                             ▼
                    ┌────────────────────┐
                    │  terraform init    │
                    │  (first time or    │
                    │  project change)   │
                    └────────┬───────────┘
                             │
                             ▼
                    ┌────────────────────┐
                    │  terraform plan    │◄──── Read config.yaml
                    │  -var="active_env  │      Read terraform.tfstate
                    │   =dev"            │      Query GCP APIs
                    └────────┬───────────┘      Compute diff
                             │
                    ┌────────┴───────────┐
                    │  Review plan output │
                    └────────┬───────────┘
                             │
              ┌──────────────┴──────────────┐
              │ Looks good?                  │ Unexpected changes?
              ▼                              ▼
   ┌──────────────────┐            ┌──────────────────┐
   │ terraform apply  │            │ Fix config.yaml  │
   │ -var="active_env │            │ then re-plan     │
   │  =dev"           │            └──────────────────┘
   │ (type 'yes')     │
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │ terraform output │
   │ -json >          │
   │ terraform-output │
   │ .json            │
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │ git commit &     │
   │ push outputs     │
   └──────────────────┘
```

---

#### CI/CD Workflow

```
                    ┌────────────────────┐
                    │  git push to dev   │
                    │  (or qa / prod)    │
                    └────────┬───────────┘
                             │  Triggers GitHub Actions
                             ▼
              ┌──────────────────────────┐
              │       JOB: test          │
              │  pytest tests/           │
              └──────────┬───────────────┘
                         │  Pass?
              ┌──────────┴───────────────┐
              │ Yes                      │ No → Fail, notify
              ▼
              ┌──────────────────────────┐
              │       JOB: pipeline      │
              │  Load terraform outputs  │
              │  Auth to GCP             │
              │  python run_pipeline.py  │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │       JOB: deploy        │
              │  Load terraform outputs  │
              │  Auth to GCP             │
              │  docker build & push     │
              │  gcloud run deploy       │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │     JOB: push-code       │
              │  Read config.yaml        │
              │  push_to_next_branch?    │
              │  Yes → merge to qa       │
              │  No  → done (prod)       │
              └──────────────────────────┘
```

---

#### How Terraform and CI/CD Interact Together

```
┌─────────────────────────────────────────────────────────────────────┐
│                     COMPLETE SYSTEM                                 │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    config.yaml                              │    │
│  │              (Single source of truth)                       │    │
│  └──────────────────┬───────────────────────┬──────────────────┘    │
│                     │                       │                       │
│                     ▼                       ▼                       │
│         ┌────────────────────┐   ┌──────────────────────────┐       │
│         │     TERRAFORM      │   │       ML CODE            │       │
│         │                    │   │  (config_loader.py)      │       │
│         │  Creates infra:    │   │                          │       │
│         │  - GCS buckets     │   │  Uses ACTIVE_ENV to      │       │
│         │  - BigQuery        │   │  load the right env      │       │
│         │  - Artifact Reg.   │   │  block from config.yaml  │       │
│         │  - Service Accts   │   └──────────────────────────┘       │
│         └──────────┬─────────┘                                      │
│                    │ terraform output -json                          │
│                    ▼                                                 │
│         ┌────────────────────┐                                      │
│         │ terraform-output   │◄── Committed to Git repo             │
│         │     .json          │    No secrets inside                 │
│         └──────────┬─────────┘                                      │
│                    │ CI/CD reads this file                          │
│                    ▼                                                 │
│         ┌────────────────────┐                                      │
│         │   GITHUB ACTIONS   │◄── Only secret: GCP_SA_KEY          │
│         │                    │                                      │
│         │  Reads outputs →   │                                      │
│         │  Sets env vars →   │                                      │
│         │  Runs pipeline →   │                                      │
│         │  Deploys Cloud Run │                                      │
│         └────────────────────┘                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 9. Quick Reference Cheatsheet

### Essential Commands

```bash
# ── AUTHENTICATION ──────────────────────────────────────────────────
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default set-quota-project YOUR_PROJECT_ID

# Verify ("The Big Three")
gcloud auth list
gcloud config get-value project
cat $APPDATA/gcloud/application_default_credentials.json   # Windows
cat ~/.config/gcloud/application_default_credentials.json  # Linux/Mac

# ── ENABLE REQUIRED APIs ─────────────────────────────────────────────
gcloud services enable artifactregistry.googleapis.com --project YOUR_PROJECT_ID
gcloud services enable bigquery.googleapis.com         --project YOUR_PROJECT_ID
gcloud services enable iam.googleapis.com              --project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com              --project YOUR_PROJECT_ID

# ── TERRAFORM ────────────────────────────────────────────────────────
cd terraform/

# First time or switching project
terraform init -reconfigure

# Preview changes (ALWAYS do this before apply)
terraform plan -var="active_env=dev"

# Apply (creates/updates infra)
terraform apply -var="active_env=dev"

# Export for CI/CD (ALWAYS do this after apply)
terraform output -json > terraform-output.json

# Destroy (CAREFUL)
terraform destroy -var="active_env=dev"

# ── IMPORT EXISTING RESOURCES ────────────────────────────────────────
terraform import google_storage_bucket.data            BUCKET_NAME
terraform import google_bigquery_dataset.dataset       projects/PROJECT_ID/datasets/DATASET_ID
terraform import google_artifact_registry_repository.repo \
  projects/PROJECT_ID/locations/REGION/repositories/REPO_ID

# ── GIT AFTER TERRAFORM APPLY ────────────────────────────────────────
git add terraform/terraform-output.json
git commit -m "chore: update Terraform outputs for CI/CD [dev]"
git push
```

---

### Decision Tree: Terraform vs Python vs CI/CD

```
Is this a persistent GCP resource (bucket, dataset, IAM)?
    │
    ├── YES → Use TERRAFORM
    │
    └── NO → Is this deploying an application or running a job?
                 │
                 ├── YES → Is it automated and triggered by code push?
                 │              │
                 │              ├── YES → Use CI/CD (GitHub Actions)
                 │              │
                 │              └── NO  → Use Python + GCP SDK (operational task)
                 │
                 └── NO → Is it data processing (uploads, queries)?
                               │
                               └── YES → Use Python + GCP SDK
```

---

### Common Errors and Fixes

| Error | Cause | Fix |
|---|---|---|
| `Error 409: already exists` | Resource exists outside Terraform state | `terraform import` the resource |
| `Error: No credentials found` | Not authenticated | `gcloud auth application-default login` |
| `Error: Project not found` | Wrong project set | `gcloud config set project YOUR_PROJECT_ID` |
| CI/CD fails: `terraform-output.json not found` | File not committed | Run `terraform output -json > terraform-output.json && git commit` |
| CI/CD fails: `Permission denied` | SA missing a role | Add role to `cicd_roles` in `config.yaml` and re-apply Terraform |
| `terraform plan` shows unexpected destroy | Config drift or wrong env | Check `-var="active_env=..."`, review plan carefully |

---

### Architecture Principles (DataNeurus Standards)

> 📌 **These are non-negotiable for all DataNeurus projects using this template:**

1. **One `config.yaml`** to rule them all — no separate configs per environment
2. **Terraform manages infrastructure** — Cloud Run is NOT Terraform's concern
3. **CI/CD manages applications** — pipelines, images, Cloud Run deploys
4. **Only one GitHub Secret** — `GCP_SA_KEY`. Everything else comes from `terraform-output.json`
5. **`terraform-output.json` is committed** — it contains no secrets, only names and IDs
6. **Branch = Environment** — `dev`, `qa`, `prod` branches map 1:1 to environments
7. **Plan before Apply** — always run `terraform plan` and review before applying
8. **Import before Create** — if a resource already exists, import it; don't try to recreate it

---

> **DataNeurus Engineering Team**  
> For questions about this template, open an issue in the `dataneurus/ml-template` repo  
> or reach out in the `#infrastructure` Slack channel.