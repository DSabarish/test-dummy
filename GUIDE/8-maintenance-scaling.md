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

**Part 8 · Maintenance & Scaling** · [← Index](README.md)

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
│  │              (Single source of truth)                        │    │
│  └──────────────────┬───────────────────────┬──────────────────┘    │
│                     │                       │                       │
│                     ▼                       ▼                       │
│         ┌────────────────────┐   ┌──────────────────────────┐       │
│         │     TERRAFORM      │   │       ML CODE             │       │
│         │                    │   │  (config_loader.py)       │       │
│         │  Creates infra:    │   │                           │       │
│         │  - GCS buckets     │   │  Uses ACTIVE_ENV to       │       │
│         │  - BigQuery        │   │  load the right env        │       │
│         │  - Artifact Reg.   │   │  block from config.yaml   │       │
│         │  - Service Accts   │   └──────────────────────────┘       │
│         └──────────┬─────────┘                                      │
│                    │ terraform output -json                          │
│                    ▼                                                 │
│         ┌────────────────────┐                                      │
│         │ terraform-output   │◄── Committed to Git repo             │
│         │     .json          │    No secrets inside                  │
│         └──────────┬─────────┘                                      │
│                    │ CI/CD reads this file                          │
│                    ▼                                                 │
│         ┌────────────────────┐                                      │
│         │   GITHUB ACTIONS   │◄── Only secret: GCP_SA_KEY           │
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

[← Previous: CI/CD Integration](7-cicd-integration.md) · [Index](README.md) · [Next: Quick Reference Cheatsheet →](9-quick-reference-cheatsheet.md)
