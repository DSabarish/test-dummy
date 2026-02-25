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

**Part 6 · Terraform Workflow** · [← Index](README.md)

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

[← Previous: Terraform Code Walkthrough](5-terraform-code-walkthrough.md) · [Index](README.md) · [Next: CI/CD Integration →](7-cicd-integration.md)
