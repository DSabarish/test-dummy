# ML App on GCP — Infra + Pipeline + Deploy

A single repo that provisions **GCP infrastructure** (Terraform), runs an **ML training pipeline** (Python), and **deploys an inference API** (Cloud Run). **One file configures everything:** root **`config.yaml`** is the only place you edit for both Terraform and ML.

---

## Central configuration: one file, all environments

**`config.yaml`** at the repo root holds **one file, all environments** (dev, qa, prod):

- **`active_env`** — which block is used (e.g. `"dev"`). Override at run time so the file stays untouched.
- **`environments.dev` / `environments.qa` / `environments.prod`** — each block is a full config (project_id, region, buckets, BigQuery, schema, ML paths, etc.). Diff between envs is visible side-by-side.

| Consumer | How it selects and uses config |
|----------|--------------------------------|
| **Terraform** | Uses **`active_env`** from file, or override with **`-var="active_env=qa"`**. `config.tf` reads `environments[active_env]` and exposes `local.config.*`. No file edit needed per env. |
| **ML code** | Uses **`ACTIVE_ENV`** env var (CI sets from branch) or **`active_env`** in file. `config_loader.py` loads `environments[ACTIVE_ENV]`, then adds computed keys (buckets, SAs, feature_columns). |
| **CI/CD** | Workflow runs on **dev, qa, prod** branches. Sets **`ACTIVE_ENV=${{ github.ref_name }}`** so pipeline and deploy use the correct env block. Reads **`terraform/terraform-output.json`** (per-branch; generated after apply for that env). |

**Execution logic:**

1. **Edit only `config.yaml`** — add or change keys inside `environments.dev` / `.qa` / `.prod`. Optionally set `active_env` for local defaults.
2. **Terraform** — `terraform apply` (or `apply -var="active_env=qa"` for qa). No file modification; env is explicit.
3. **ML pipeline** — Locally uses `active_env` in file; in CI uses `ACTIVE_ENV` from branch.
4. **CI/CD** — Branch name = env. Each branch should have its own `terraform-output.json` (from apply for that env).

Single source of truth; no drift between envs because all three are in one file.

---

## What this repo does

| Part | Purpose |
|------|--------|
| **Terraform** | Creates Artifact Registry, BigQuery (dataset + table), two GCS buckets (data + artifacts), and two service accounts (CI/CD + runtime) with IAM. All inputs from `config.yaml`. **Terraform does not create or manage Cloud Run.** |
| **ML pipeline** | Generate data → write to BigQuery → export to GCS → clean → transform → train → save model to GCS (versioned). Uses `config.yaml` via `config_loader.py`. |
| **Inference API** | FastAPI app that loads the latest model from GCS and exposes `/predict`. Packaged in Docker (includes `config.yaml`), deployed to Cloud Run. |
| **CI/CD** | GitHub Actions: test → pipeline (using `terraform/terraform-output.json`) → build image → deploy to Cloud Run. Only `GCP_SA_KEY` is a GitHub secret. **Cloud Run is created/updated exclusively via `gcloud run deploy` in CI/CD; Terraform never touches Cloud Run.** |

---

## Repo layout

```
.
├── config.yaml              # Central config. Edit only this for Terraform + ML.
├── command_mark.md          # Step-by-step: auth, APIs, terraform, terraform-output.json
├── terraform/               # GCP infra (reads config.yaml)
│   ├── config.tf            # Loads config.yaml → local.config
│   ├── main.tf              # Resources + outputs
│   ├── terraform-output.json # Committed after apply; CI/CD reads this
│   └── config-generator/   # Optional: env export from config (no GCP)
├── ML-code/                 # Pipeline + inference (read config.yaml)
│   ├── config_loader.py     # Loads config.yaml; derives feature_columns, buckets, SAs
│   ├── run_pipeline.py     # Full pipeline
│   ├── inference.py        # FastAPI + /predict
│   └── requirements.txt
├── tests/
├── frontend/
├── .github/
│   └── workflows/
│       └── cicd.yml
├── Dockerfile               # Cloud Run image (copies config.yaml)
└── new-project-template/   # Copy this folder to start a new project (see its README)
    ├── README.md            # How to use the template
    ├── config.yaml          # Template: replace YOUR_PROJECT_ID_* with your GCP project IDs
    └── terraform/           # Terraform code only (no state, no .terraform)
        ├── config.tf
        ├── main.tf
        └── config-generator/
```

---

## Quick start

### 1. Configure (only place you edit for infra + ML)

Edit **`config.yaml`** at repo root. Structure:

- **`active_env`** — default env for local runs (`"dev"` | `"qa"` | `"prod"`). CI overrides via branch; do not edit manually for prod.
- **`environments.dev` / `.qa` / `.prod`** — each block has **five sections**: (1) Project & env (2) Terraform only (labels, retention, IAM) (3) Shared (BQ dataset/table/schema) (4) ML only (GCS paths) (5) **CI/CD** (`push_to_next_branch`, `next_branch_name`). IAM (`cicd_roles`, `runtime_roles`) is explicit per env; prod uses tightened roles (e.g. `storage.objectAdmin`, `artifactregistry.writer`). **Promotion chain:** dev → qa → prod; prod has `push_to_next_branch: false` (end of chain).

**Selecting env:** Terraform: `terraform apply -var="active_env=qa"`. ML locally: uses `active_env` in file. CI: sets `ACTIVE_ENV` from branch name (dev/qa/prod).

### 2. Provision infra

From repo root. Use **`-var="active_env=..."`** to target an environment (omit to use `active_env` in config.yaml):

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

cd terraform
terraform init -reconfigure
terraform plan -var="active_env=dev"    # or qa / prod
terraform apply -var="active_env=dev"   # type yes

# Export outputs for CI/CD (then commit). Repeat per env; each branch should have its env's outputs.
terraform output -json > terraform-output.json
```

**command_mark.md** has the full sequence (APIs, IAM, 409 handling).

### 3. Run ML pipeline locally

Pipeline reads **config.yaml** via `config_loader.py`. It uses **`active_env`** in the file (or set **`ACTIVE_ENV`** in the shell to override):

```bash
pip install -r ML-code/requirements.txt
python ML-code/run_pipeline.py   # uses active_env from config.yaml
# Or: ACTIVE_ENV=qa python ML-code/run_pipeline.py
```

### 4. Run inference API locally

```bash
cd ML-code
uvicorn inference:app --reload --port 8080
```

Uses latest model from GCS; config from **config.yaml**.

### 5. CI/CD (GitHub Actions)

Workflow runs on push to **dev**, **qa**, or **prod**. Branch name = environment:

1. **Set ACTIVE_ENV** from branch (e.g. `dev` → `ACTIVE_ENV=dev`).
2. **test** → `pytest tests/`
3. **pipeline** → loads `terraform/terraform-output.json` → env vars; runs `run_pipeline.py` with `ACTIVE_ENV` so config uses the right env block.
4. **deploy** → same outputs → build image (with `config.yaml` in image) → deploy to Cloud Run for that env using `gcloud run deploy`.

**Cloud Run ownership and config:**

- **Infra (Terraform):**
  - Manages Artifact Registry, BigQuery, GCS buckets, IAM, and service accounts (including the Cloud Run runtime SA).
  - Exposes non-secret values (project, region, buckets, artifact repo URL, runtime SA) via `terraform/terraform-output.json`, which CI/CD reads.
  - **Does not create or update Cloud Run services.**
- **App (CI/CD):**
  - `deploy` job is the **only place** that creates/updates the Cloud Run service via `gcloud run deploy`.
  - Flags such as **`--min-instances`**, **`--max-instances`**, **`--cpu`**, **`--memory`**, **`--timeout`**, and **`--concurrency`** are wired from `config.yaml` under each env's `cloud_run` block (dev/qa/prod can be tuned independently for usage and traffic).
  - This keeps **infrastructure** (Terraform) and **application runtime** (Cloud Run) concerns clearly separated, while still using `config.yaml` as the single source of truth for per-environment sizing.

**Secrets:** Only **GCP_SA_KEY**. Each branch should have its own **`terraform-output.json`** (from `terraform apply -var="active_env=<branch>"`). **Push-code:** After deploy, the workflow reads **per-env** `push_to_next_branch` and `next_branch_name` from `config.yaml` (dev→qa, qa→prod; prod has `push_to_next_branch: false`). If `next_branch_name` is empty or env is missing in config, push is skipped.

---

## Config flow (single source of truth)

**`config.yaml`** has **`active_env`** and **`environments.{dev,qa,prod}`**. Terraform and ML both read from it; no other config files.

**Flow:**

```
config.yaml (active_env + environments.dev|qa|prod)
       │
       ├── Terraform (config.tf)
       │   active_env from -var or file → environments[active_env] → local.config.*
       │
       └── ML (config_loader.py)
           ACTIVE_ENV env var or active_env in file → environments[ACTIVE_ENV]
           → feature_columns, data_bucket, artifacts_bucket, SAs, artifact_repo_url
```

- **Terraform:** `config.tf` uses variable **`active_env`** (default from file). `local.config` is built from **`environments[active_env]`**. Override with **`terraform apply -var="active_env=qa"`** — no file edit.
- **ML:** **`config_loader.load_config()`** uses **`ACTIVE_ENV`** (CI) or **`active_env`** in file, then loads **`environments[active_env]`** and adds computed keys.
- **CI:** Workflow sets **`ACTIVE_ENV=${{ github.ref_name }}`** (dev/qa/prod) so the right block is used.

**Optional export:** **terraform/config-generator** (if updated for multi-env) can export env-style file from config; run from that dir with `terraform apply -auto-approve`.

---

## Terraform outputs

After `terraform apply`: `project_id`, `region`, `table_id`, `artifact_repo_url`, `artifacts_bucket`, `data_bucket`, `dataset_id`, `cicd_service_account`, `runtime_service_account`.

CI/CD reads **`terraform/terraform-output.json`**. Generate it with `terraform output -json > terraform-output.json` (from `terraform/`) and commit. Only **GCP_SA_KEY** stays a GitHub secret.

---

## Docs in this repo

| File | Content |
|------|--------|
| **README.md** (this file) | Overview, central config, config flow, layout, quick start, CI/CD. |
| **command_mark.md** | Full runbook: auth, APIs, IAM, terraform, terraform-output.json, 409 handling. |

---

## Using this repo for a new project

**Easiest:** Copy the **`new-project-template/`** folder from this repo. It contains Terraform code, a `config.yaml` template (placeholders like `YOUR_PROJECT_ID_DEV`), and a **README** with step-by-step instructions. Copy its contents to your new repo root, edit `config.yaml` with your project IDs, then run `terraform init` and `apply`.

Alternatively, when **you** want to start a **new project** from this code (e.g. new branch or new repo), use the Terraform and ML code **without** the old project’s state or cache.

**What to use**

- **`terraform/`** — Use the `.tf` files only. **Do not** copy into the new project:
  - `terraform/.terraform/` (cache)
  - `terraform/*.tfstate` and `*.tfstate.backup` (state)
  `.gitignore` already excludes these, so a new branch or clone only has the code. In the new project run `terraform init -reconfigure`, then `plan` and `apply`; you get a new state.

- **`config.yaml`** — **Yes, you need it.** Terraform and ML-code both read it. For the new project, edit `config.yaml`: set the new **`project_id`** (and region, prefix, dataset/table names, etc.) for each environment. That’s the main change for a new GCP project.

- **`terraform-output.json`** — Don’t reuse the old one. After the first `terraform apply` in the new project, run `terraform output -json > terraform-output.json` and commit it.

**Steps for a new project**

1. New branch or new repo from this code (no `.terraform/` or `*.tfstate`; they’re gitignored).
2. Edit **`config.yaml`** with the new project’s `project_id` and env values.
3. In `terraform/`: `terraform init -reconfigure`, then `plan` and `apply` with `-var="active_env=dev"` (and qa/prod if needed).
4. Run `terraform output -json > terraform-output.json`, commit it. If using CI/CD, add **GCP_SA_KEY** for the new project in GitHub Secrets.
5. Use ML-code as usual; it uses `config.yaml` and `terraform-output.json`.

| Item | Use in new project? | Notes |
|------|----------------------|--------|
| `terraform/*.tf` | Yes | Code only; no state, no `.terraform/`. |
| `config.yaml` | Yes | Edit for new `project_id` and env values. |
| `terraform-output.json` | Regenerate | After `apply` in the new project. |
| ML-code/ | Yes | Same code; config drives which project it uses. |

---

## Requirements

- **Terraform** ≥ 1.5
- **Google Cloud** project with billing; gcloud CLI and Application Default Credentials
- **Python** 3.11 (see `ML-code/requirements.txt`)
- **Docker** for building the Cloud Run image (CI/CD or local)
