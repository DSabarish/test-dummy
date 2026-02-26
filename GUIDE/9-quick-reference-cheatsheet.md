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
10. [End-to-End Flowchart (Terraform + CI/CD)](10-terraform-cicd-flowchart.md)

---

**Part 9 · Quick Reference Cheatsheet** · [← Index](README.md)

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

# ── GOLDEN PATH — FULL EXECUTION (PowerShell, Windows) ────────────────
# Run from repo root. Set $PROJECT_ID to match config.yaml (e.g. environments.dev.project_id).
# See also: [6. Terraform Workflow](6-terraform-workflow.md#67-golden-path--full-execution-script-powershell)

$PROJECT_ID = "YOUR_PROJECT_ID_DEV"
$env:GOOGLE_APPLICATION_CREDENTIALS = ""
gcloud auth application-default revoke; gcloud auth login; gcloud auth application-default login
gcloud config set project $PROJECT_ID; gcloud auth application-default set-quota-project $PROJECT_ID
gcloud services enable artifactregistry.googleapis.com bigquery.googleapis.com iam.googleapis.com run.googleapis.com storage.googleapis.com --project $PROJECT_ID
cd terraform; terraform init -reconfigure; terraform plan -var="active_env=dev"; terraform apply -var="active_env=dev"
terraform output -json > terraform-output.json; cd ..

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

**DataNeurus Engineering**  
For questions about this template, open an issue in the `dataneurus/ml-template` repo or reach out in the `#infrastructure` Slack channel.

---

[← Previous: Maintenance & Scaling](8-maintenance-scaling.md) · [Index](README.md) · [Next: End-to-End Flowchart (Terraform + CI/CD) →](10-terraform-cicd-flowchart.md)
