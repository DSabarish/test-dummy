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

**Part 4 · Terraform Project Structure** · [← Index](README.md)

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

### 4.2 Proposed Approach: Single Config File

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

[← Previous: Responsibility Split](3-responsibility-split-terraform-cicd.md) · [Index](README.md) · [Next: Terraform Code Walkthrough →](5-terraform-code-walkthrough.md)
