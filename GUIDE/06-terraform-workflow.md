# Terraform Implementation Guide <img src="./logo.png" alt="DataNeurus logo" align="right" width="150" />

## Terraform + CI/CD: Infrastructure as Code for ML/AI/Data Projects

> **Document Type:** Internal Engineering Reference  
> **Audience:** Engineers new to Infrastructure as Code (beginner → intermediate)  
> **Status:** 🟡 Active Template — Under Review  
> **Last Updated:** 26-02-2026

---

## Table of Contents

1. [Introduction](01-introduction.md)
2. [Why Terraform Instead of Python + GCP SDK](02-why-terraform-python-gcp-sdk.md)
3. [Responsibility Split: Terraform vs CI/CD](03-responsibility-split-terraform-cicd.md)
4. [Terraform Project Structure](04-terraform-project-structure.md)
5. [Terraform Code Walkthrough](05-terraform-code-walkthrough.md)
6. [Terraform Workflow](06-terraform-workflow.md)
7. [CI/CD Integration](07-cicd-integration.md)
8. [Maintenance & Scaling](08-maintenance-scaling.md)
9. [Quick Reference Cheatsheet](09-quick-reference-cheatsheet.md)
10. [End-to-End Flowchart (Terraform + CI/CD)](10-terraform-cicd-flowchart.md)

---

**Part 6 · Terraform Workflow** · [← Index](README.md)

---

## 6. Terraform Workflow

The Terraform workflow follows four core commands. Here is a detailed walkthrough of each.

### 6.1 Workflow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   TERRAFORM WORKFLOW                            │
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐   │
│   │   INIT   │───►│   PLAN   │───►│  APPLY   │───►│OUTPUTS  │   │
│   └──────────┘    └──────────┘    └──────────┘    └─────────┘   │
│   Download        Preview          Create/Update  Export JSON   │
│   providers       changes          resources      for CI/CD     │
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
terraform import google_storage_bucket.data <GCS_BUCKET_NAME>   # e.g. mlapp-dev-data-my-project-001
terraform import google_bigquery_dataset.dataset projects/my-project-001/datasets/training_dataset_dev

# Then apply as normal (Terraform will update to match config, not recreate)
terraform apply -var="active_env=dev"
```

After importing, Terraform "knows" about the existing resource and will manage it going forward.

---

### 6.7 Full execution script (PowerShell)

Use this end-to-end script on Windows when setting up a new project or recovering from auth issues. Set `$PROJECT_ID` to match `config.yaml` (e.g. `environments.dev.project_id`). Run from **repo root** (so `terraform/` and `config.yaml` are in place).

```powershell
############################################
FULL EXECUTION SCRIPT
############################################

$PROJECT_ID = "YOUR_PROJECT_ID_DEV"   # Must match config.yaml
echo $PROJECT_ID

# STEP 1 — Environment & tools
terraform -version
gcloud version
$env:GOOGLE_APPLICATION_CREDENTIALS = ""  # de-initialise

# STEP 2 — Authentication & project setup
gcloud auth application-default revoke
gcloud auth login
gcloud auth application-default login
gcloud config set project $PROJECT_ID
gcloud auth application-default set-quota-project $PROJECT_ID

# Verification ("Big Three")
gcloud auth list
gcloud config get-value project
cat $env:APPDATA\gcloud\application_default_credentials.json

# STEP 3 — Enable required APIs
gcloud services enable artifactregistry.googleapis.com --project $PROJECT_ID
gcloud services enable bigquery.googleapis.com         --project $PROJECT_ID
gcloud services enable iam.googleapis.com             --project $PROJECT_ID
gcloud services enable run.googleapis.com             --project $PROJECT_ID
gcloud services enable storage.googleapis.com          --project $PROJECT_ID

# STEP 4 — Prepare Terraform
cd terraform
# Optional when switching project: rm terraform.tfstate, terraform.tfstate.backup
terraform init -reconfigure

# STEP 5 — Plan
terraform plan -var="active_env=dev"

# STEP 6 — Apply
terraform apply -var="active_env=dev"
# Type 'yes' when prompted

# STEP 7 — Export outputs for CI/CD and ML
terraform output -json > terraform-output.json
cd ..
# Commit terraform-output.json
```

**Expected outputs:** `artifact_repo_url`, `artifacts_bucket`, `cicd_service_account`, `data_bucket`, `dataset_id`, `project_id`, `region`, `runtime_service_account`, `table_id`.

---

[← Previous: Terraform Code Walkthrough](05-terraform-code-walkthrough.md) · [Index](README.md) · [Next: CI/CD Integration →](07-cicd-integration.md)
