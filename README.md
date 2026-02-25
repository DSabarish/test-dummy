# ML App on GCP ? Infra + Pipeline + Deploy

A single repo that provisions **GCP infrastructure** (Terraform), runs an **ML training pipeline** (Python), and **deploys an inference API** (Cloud Run). **One file configures everything:** root **`config.yaml`** is the only place you edit for both Terraform and ML.

---

## Central configuration: one file, two consumers

All execution flows from **`config.yaml`** at the repo root:

| Consumer | How it uses config.yaml |
|----------|-------------------------|
| **Terraform** | `terraform/config.tf` reads `config.yaml` and exposes `local.config.*`. Resources (Artifact Registry, BigQuery, GCS, IAM) and outputs are driven entirely from this file. No tfvars. |
| **ML code** | `ML-code/config_loader.py` reads the same `config.yaml`. Pipeline and inference use project, buckets, dataset, table, and feature columns (derived from `table_schema`). |

**Execution logic:**

1. **Edit only `config.yaml`** ? project, region, dataset/table IDs, `table_schema`, retention, IAM roles, etc.
2. **Terraform** ? `terraform plan/apply` uses that config; no `-var-file` or duplicate YAML.
3. **ML pipeline** ? `run_pipeline.py` and all steps use `config_loader.load_config()`; no separate env files or configs.
4. **CI/CD** ? GitHub Actions reads **`terraform/outputs.json`** (generated from the same Terraform that was applied using `config.yaml`). Only **GCP_SA_KEY** is a secret; all other values come from Terraform outputs.

So: **single source of truth = `config.yaml`**. Terraform and ML never diverge because they share the same file.

---

## What this repo does

| Part | Purpose |
|------|--------|
| **Terraform** | Creates Artifact Registry, BigQuery (dataset + table), two GCS buckets (data + artifacts), and two service accounts (CI/CD + runtime) with IAM. All inputs from `config.yaml`. |
| **ML pipeline** | Generate data ? write to BigQuery ? export to GCS ? clean ? transform ? train ? save model to GCS (versioned). Uses `config.yaml` via `config_loader.py`. |
| **Inference API** | FastAPI app that loads the latest model from GCS and exposes `/predict`. Packaged in Docker (includes `config.yaml`), deployed to Cloud Run. |
| **CI/CD** | GitHub Actions: test ? pipeline (using `terraform/outputs.json`) ? build image ? deploy to Cloud Run. Only `GCP_SA_KEY` is a GitHub secret. |

---

## Repo layout

```
.
??? config.yaml              # Central config. Edit only this for Terraform + ML.
??? CONFIG.md                 # How config flows (Terraform vs ML)
??? command_mark.md          # Step-by-step: auth, APIs, terraform, outputs.json
?
??? terraform/                # GCP infra (reads config.yaml)
?   ??? config.tf             # Loads config.yaml ? local.config
?   ??? main.tf                # Resources + outputs
?   ??? outputs.json           # Committed after apply; CI/CD reads this
?   ??? config-generator/      # Optional: env export from config (no GCP)
?
??? ML-code/                  # Pipeline + inference (read config.yaml)
?   ??? config_loader.py      # Loads config.yaml; derives feature_columns, buckets, SAs
?   ??? run_pipeline.py       # Full pipeline
?   ??? inference.py          # FastAPI + /predict
?   ??? requirements.txt
?
??? tests/
??? frontend/
??? .github/workflows/cicd.yml
??? Dockerfile                # Cloud Run image (copies config.yaml)
```

---

## Quick start

### 1. Configure (only place you edit for infra + ML)

Edit **`config.yaml`** at repo root:

- **GCP & naming:** `project_id`, `region`, `environment`, `prefix`
- **BigQuery:** `dataset_id`, `table_id`, `dataset_location`
- **Schema:** `table_schema` (column names and types). The key `target_column` marks the target; all other columns are used as features.
- **Optional:** labels, retention days, `cicd_roles` / `runtime_roles`

See **CONFIG.md** for the full list and how Terraform vs ML use each key.

### 2. Provision infra

From repo root:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

cd terraform
terraform init -reconfigure
terraform plan    # all inputs from config.yaml
terraform apply   # type yes

# Export outputs for CI/CD (then commit)
terraform output -json > outputs.json
```

**command_mark.md** has the full sequence (APIs, IAM, 409 handling).

### 3. Run ML pipeline locally

Pipeline reads **config.yaml** via `config_loader.py` (no separate config):

```bash
pip install -r ML-code/requirements.txt
python ML-code/run_pipeline.py
```

### 4. Run inference API locally

```bash
cd ML-code
uvicorn inference:app --reload --port 8080
```

Uses latest model from GCS; config from **config.yaml**.

### 5. CI/CD (GitHub Actions)

On push to `dev`:

1. **test** ? `pytest tests/`
2. **pipeline** ? loads `terraform/outputs.json` ? env vars; runs `run_pipeline.py` (still uses config.yaml for schema/buckets)
3. **deploy** ? same outputs ? build image (with `config.yaml` in image) ? deploy to Cloud Run

**Secrets:** Only **GCP_SA_KEY** (CI/CD service account JSON). After each `terraform apply`, run `terraform output -json > outputs.json` in `terraform/` and commit so the workflow has project, buckets, dataset, table, region, and runtime SA.

---

## Config flow summary

- **Terraform:** `config.tf` loads `config.yaml` ? `local.config.*` drives all resources and outputs.
- **ML:** `config_loader.py` loads the same `config.yaml` ? derives `feature_columns` from `table_schema`, adds `data_bucket`, `artifacts_bucket`, `artifact_repo_url`, and service account emails.
- **No duplicate config:** no tfvars for normal use, no separate ML YAML. Optional: **terraform/config-generator** can export an env-style file from `config.yaml` only (no GCP calls).

---

## Terraform outputs

After `terraform apply`: `project_id`, `region`, `table_id`, `artifact_repo_url`, `artifacts_bucket`, `data_bucket`, `dataset_id`, `cicd_service_account`, `runtime_service_account`.

CI/CD reads **`terraform/outputs.json`**. Generate it with `terraform output -json > outputs.json` (from `terraform/`) and commit. Only **GCP_SA_KEY** stays a GitHub secret.

---

## Docs in this repo

| File | Content |
|------|--------|
| **README.md** (this file) | Overview, central config, layout, quick start, CI/CD. |
| **CONFIG.md** | Config keys and how Terraform vs ML use them. |
| **command_mark.md** | Full runbook: auth, APIs, IAM, terraform, outputs.json, 409 handling. |

---

## Requirements

- **Terraform** ? 1.5
- **Google Cloud** project with billing; gcloud CLI and Application Default Credentials
- **Python** 3.11 (see `ML-code/requirements.txt`)
- **Docker** for building the Cloud Run image (CI/CD or local)
