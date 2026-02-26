## ML App on GCP — Infra, Pipeline, and Cloud Run Deploy

This repository contains a **complete ML application stack on Google Cloud Platform (GCP)**:

- **Infrastructure** with Terraform (buckets, BigQuery, Artifact Registry, service accounts, IAM).
- **ML training pipeline** in Python (data generation → BigQuery → GCS → feature engineering → training → model artifact in GCS).
- **Inference API** using FastAPI, containerized with Docker and deployed to **Cloud Run**.

The **single source of truth** for all environments is the root **`config.yaml`**. You only edit that file for both **Terraform** and **ML code**.

---

## Central configuration: `config.yaml` (all environments)

**`config.yaml`** at the repo root holds configuration for **dev**, **qa**, and **prod** in one place:

- **`active_env`**: default environment for local runs (e.g. `"dev"`). CI overrides this; you generally do **not** edit it manually for prod.
- **`environments.dev` / `environments.qa` / `environments.prod`**: each block is a full, self-contained config (project ID, region, buckets, BigQuery dataset/table/schema, ML paths, IAM roles, Cloud Run sizing, CI/CD promotion flags, etc.).

**How different consumers use `config.yaml`:**

| Consumer | How it selects and uses config |
|----------|--------------------------------|
| **Terraform** | Uses `active_env` from the file by default, or an override via `-var="active_env=qa"`. `config.tf` reads `environments[active_env]` and exposes `local.config.*`. No per-environment file edits required. |
| **ML code** | Uses the `ACTIVE_ENV` environment variable (CI sets from branch), or falls back to `active_env` in the file. `config_loader.py` loads `environments[ACTIVE_ENV]` and derives additional values (buckets, service accounts, `feature_columns`, etc.). |
| **CI/CD** | GitHub Actions runs on `dev`, `qa`, and `prod` branches. It sets `ACTIVE_ENV=${{ github.ref_name }}` so the pipeline and deploy jobs use the correct environment block. It also reads `terraform/terraform-output.json` generated for that environment. |

**Execution model (high level):**

1. **Edit only `config.yaml`** — add/change keys under `environments.dev` / `.qa` / `.prod`. Optionally set `active_env` for local default behavior.
2. **Terraform** — runs with `terraform apply` (or `terraform apply -var="active_env=qa"` for QA). The environment is explicit; the file content stays shared.
3. **ML pipeline (local)** — reads `active_env` from the file unless `ACTIVE_ENV` is set in your shell.
4. **CI/CD** — branch name (`dev` / `qa` / `prod`) determines `ACTIVE_ENV` and therefore which environment block is used.

This keeps **all environments aligned** and avoids drift because there is exactly **one config file**.

---

## What this repo provisions and runs

| Part | Purpose |
|------|--------|
| **Terraform** | Creates Artifact Registry, BigQuery dataset + table, two GCS buckets (data + artifacts), and two service accounts (CI/CD and runtime) with IAM. All inputs come from `config.yaml`. **Terraform intentionally does not create or manage Cloud Run.** |
| **ML pipeline** | Generates synthetic or source data → writes to BigQuery → exports to GCS → cleans/transforms → trains a model → writes a **versioned model artifact** to GCS. Uses `config.yaml` via `config_loader.py`. |
| **Inference API** | FastAPI app (`inference.py`) that loads the **latest model** from GCS and exposes `/predict`. Packaged via `Dockerfile` (which copies `config.yaml`), then deployed to Cloud Run. |
| **CI/CD** | GitHub Actions pipeline that runs tests, executes the ML pipeline (using `terraform/terraform-output.json`), builds the Docker image, and deploys to Cloud Run. The only secret required is `GCP_SA_KEY`. **Cloud Run is created/updated exclusively via `gcloud run deploy` in CI/CD; Terraform never touches Cloud Run.** |

---

## Repository layout

```text
.
├── config.yaml               # Central config. Edit only this for Terraform + ML.
├── command_mark.md           # Step-by-step: auth, APIs, terraform, terraform-output.json
├── terraform/                # GCP infra (reads config.yaml)
│   ├── config.tf             # Loads config.yaml → local.config
│   ├── main.tf               # Resources + outputs
│   ├── terraform-output.json # Committed after apply; CI/CD reads this
│   └── config-generator/     # Optional: env export from config (no GCP)
├── ML-code/                  # Pipeline + inference (reads config.yaml)
│   ├── config_loader.py      # Loads config.yaml; derives feature_columns, buckets, SAs
│   ├── run_pipeline.py       # Full pipeline entrypoint
│   ├── inference.py          # FastAPI + /predict
│   └── requirements.txt
├── tests/
├── frontend/
├── .github/
│   └── workflows/
│       └── cicd.yml
├── Dockerfile                # Cloud Run image (copies config.yaml)
└── new-project-template/     # Copy this folder to start a new project (see its README)
    ├── README.md             # How to use the template
    ├── config.yaml           # Template: replace YOUR_PROJECT_ID_* with your GCP project IDs
    └── terraform/            # Terraform code only (no state, no .terraform)
        ├── config.tf
        ├── main.tf
        └── config-generator/
```

---

## Quick start

### 1. Configure `config.yaml` (single place for infra + ML)

Edit **`config.yaml`** at the repo root.

- **`active_env`**: default environment for local runs (`"dev"` / `"qa"` / `"prod"`). CI overrides via branch name; avoid manually setting this to `prod`.
- **`environments.dev` / `.qa` / `.prod`**: each block typically includes:
  - **Project & env metadata**: `project_id`, `region`, labels, prefixes.
  - **Terraform-only settings**: lifecycle rules, retention, IAM role lists (`cicd_roles`, `runtime_roles`).
  - **Shared data settings**: BigQuery dataset/table names and schema.
  - **ML-only settings**: GCS paths for data and artifacts, model locations.
  - **CI/CD settings**: `push_to_next_branch`, `next_branch_name`, and Cloud Run sizing under a `cloud_run` block.

**Promotion chain:** dev → qa → prod. Typically prod has `push_to_next_branch: false` as the end of the promotion chain.

**Environment selection:**

- **Terraform**: `terraform apply -var="active_env=qa"`.
- **ML local**: uses `active_env` from the file unless overridden with `ACTIVE_ENV`.
- **CI**: sets `ACTIVE_ENV` from the branch name (`dev` / `qa` / `prod`).

### 2. Provision infrastructure with Terraform

From the repo root, use **`-var="active_env=..."`** to target a specific environment (or omit it to use `active_env` in `config.yaml`):

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

cd terraform
terraform init -reconfigure
terraform plan -var="active_env=dev"    # or qa / prod
terraform apply -var="active_env=dev"   # type yes when prompted

# Export outputs for CI/CD (then commit). Repeat per env; each branch should have its own outputs.
terraform output -json > terraform-output.json
```

**Golden path (PowerShell, full script):**  
For a single copy‑paste flow (auth, APIs, init, plan, apply, outputs), see:

- **`new-project-template/README.md`** → `# golden-path--full-execution-script-powershell`
- **`GUIDE/6-terraform-workflow.md`** → `#67-golden-path--full-execution-script-powershell`

The **`command_mark.md`** file in the root has the full sequence including required APIs, IAM, and handling `409` conflicts.

### 3. Run the ML pipeline locally

The pipeline reads **`config.yaml`** through `config_loader.py`. It uses **`active_env`** in the file unless you override it with `ACTIVE_ENV`:

```bash
pip install -r ML-code/requirements.txt
python ML-code/run_pipeline.py   # uses active_env from config.yaml
# Or: ACTIVE_ENV=qa python ML-code/run_pipeline.py
```

### 4. Run the inference API locally

```bash
cd ML-code
uvicorn inference:app --reload --port 8080
```

The API loads the latest model artifact from GCS and configures itself from **`config.yaml`**.

### 5. CI/CD (GitHub Actions → Cloud Run)

The workflow in `.github/workflows/cicd.yml` runs on pushes to **`dev`**, **`qa`**, and **`prod`** branches. Branch name = environment:

1. **Set `ACTIVE_ENV`** from the branch (e.g. `dev` → `ACTIVE_ENV=dev`).
2. **Test**: run `pytest tests/`.
3. **Pipeline**: load `terraform/terraform-output.json` into environment variables and run `run_pipeline.py` with `ACTIVE_ENV` so the correct environment block is used.
4. **Deploy**: reuse the same outputs, build the Docker image (which includes `config.yaml`), and deploy to Cloud Run for that environment via `gcloud run deploy`.

**Cloud Run ownership and runtime configuration**

- **Infrastructure layer (Terraform)**:
  - Manages Artifact Registry, BigQuery, GCS buckets, IAM, and service accounts (including the Cloud Run runtime service account).
  - Exposes non‑secret values such as `project_id`, `region`, bucket names, artifact registry URL, and runtime service account via `terraform/terraform-output.json`.
  - **Does not create or modify Cloud Run services.**

- **Application layer (CI/CD)**:
  - The **`deploy`** job is the only place that creates/updates the Cloud Run service using `gcloud run deploy`.
  - Cloud Run flags such as `--min-instances`, `--max-instances`, `--cpu`, `--memory`, `--timeout`, and `--concurrency` are wired from `config.yaml` under each environment’s `cloud_run` block, so you can tune dev/qa/prod independently.
  - This cleanly separates **infrastructure** (Terraform) from **application runtime** (Cloud Run) while still using `config.yaml` as the single source of truth.

**Secrets and promotion**

- The only required GitHub secret is **`GCP_SA_KEY`** (a JSON key for the CI/CD service account).
- Each branch should have its own **`terraform-output.json`** (generated via `terraform apply -var="active_env=<branch>"`).
- The workflow reads `push_to_next_branch` and `next_branch_name` from `config.yaml` for the current environment (dev → qa → prod). In prod, this is usually configured to **not** push further (`push_to_next_branch: false`). If `next_branch_name` is empty or the env block is missing, promotion is skipped.

---

## Config flow (single source of truth)

`config.yaml` contains **`active_env`** and **`environments.{dev,qa,prod}`**. Terraform and the ML code both read from it; there are no other primary config files.

**High‑level flow:**

```text
config.yaml (active_env + environments.dev|qa|prod)
       │
       ├── Terraform (config.tf)
       │   active_env from -var or file → environments[active_env] → local.config.*
       │
       └── ML (config_loader.py)
           ACTIVE_ENV env var or active_env in file → environments[ACTIVE_ENV]
           → feature_columns, data_bucket, artifacts_bucket, SAs, artifact_repo_url
```

- **Terraform**: `config.tf` defines variable `active_env` (default from file) and constructs `local.config` from `environments[active_env]`. Override with `terraform apply -var="active_env=qa"` without editing the file.
- **ML**: `config_loader.load_config()` uses `ACTIVE_ENV` (in CI) or `active_env` from the file, then loads `environments[active_env]` and computes convenience keys.
- **CI**: the GitHub Actions workflow sets `ACTIVE_ENV=${{ github.ref_name }}` (dev/qa/prod) so the correct environment configuration is used automatically.

**Optional export:**  
The **`terraform/config-generator`** module (if updated for multi‑env) can export an env‑style file from `config.yaml`. Run it from that directory with:

```bash
terraform apply -auto-approve
```

---

## Terraform outputs

After `terraform apply`, the Terraform config exposes outputs such as:

- `project_id`
- `region`
- `table_id`
- `artifact_repo_url`
- `artifacts_bucket`
- `data_bucket`
- `dataset_id`
- `cicd_service_account`
- `runtime_service_account`

CI/CD reads **`terraform/terraform-output.json`**. Generate it from the `terraform/` directory and commit it:

```bash
terraform output -json > terraform-output.json
```

Only **`GCP_SA_KEY`** remains a GitHub secret.

---

## Documentation in this repo

| File | Content |
|------|--------|
| **`README.md`** (this file) | High‑level overview, central config, config flow, layout, quick start, and CI/CD behavior. |
| **`command_mark.md`** | Detailed runbook: authentication, API enablement, IAM setup, Terraform, `terraform-output.json`, and conflict (`409`) handling. |
| **`new-project-template/README.md`** | How to bootstrap a brand‑new project from the template. |

---

## Using this repo as a template for a new project

**Recommended path:** copy the **`new-project-template/`** folder from this repo into a new repository or a clean directory. It contains:

- Terraform code only (no state, no `.terraform/` cache).
- A `config.yaml` template with placeholders like `YOUR_PROJECT_ID_DEV`.
- A dedicated `README` with step‑by‑step instructions.

Update the template’s `config.yaml` with your real GCP project IDs and environment details, then run `terraform init` and `terraform apply`.

If you want to **start a new project from this repo’s current state** (for example, a new branch or a cloned repo), reuse the Terraform and ML code but not the old Terraform state or cache.

**What to reuse vs. regenerate**

- **`terraform/`** — Use the `.tf` files, but **do not** copy:
  - `terraform/.terraform/` (local provider/cache directory)
  - `terraform/*.tfstate` and `terraform/*.tfstate.backup` (state files)

  A fresh branch or clone should only contain code. In the new project, run `terraform init -reconfigure`, then `terraform plan` and `terraform apply` to create a new state.

- **`config.yaml`** — Required. Both Terraform and the ML code read from it. For a new project:
  - Set the new `project_id` and region per environment.
  - Adjust dataset/table names, bucket prefixes, and IAM roles as needed.

- **`terraform-output.json`** — Must be **regenerated**; don’t reuse the old file:
  - After the first `terraform apply` in the new project, run:

    ```bash
    cd terraform
    terraform output -json > terraform-output.json
    ```

  - Commit the new `terraform-output.json` per environment/branch.

**End‑to‑end steps for a new project**

1. Create a new repo or branch from the template or from this code (without `.terraform/` or `*.tfstate`; they are git‑ignored).
2. Edit **`config.yaml`** with the new project’s `project_id`, region, and per‑env values.
3. In `terraform/`, run `terraform init -reconfigure`, then `terraform plan` and `terraform apply -var="active_env=dev"` (repeat for `qa` and `prod` as needed).
4. Run `terraform output -json > terraform-output.json` and commit it. If you use CI/CD, configure **`GCP_SA_KEY`** for the new project in GitHub Secrets.
5. Use the ML code as usual; it derives resource locations from `config.yaml` and `terraform-output.json`.

| Item | Use in new project? | Notes |
|------|----------------------|--------|
| `terraform/*.tf` | Yes | Code only; no `.terraform/` directory, no `*.tfstate`. |
| `config.yaml` | Yes | Update for new `project_id`, region, and env‑specific values. |
| `terraform-output.json` | Regenerate | Run `terraform output -json > terraform-output.json` after `apply`. |
| `ML-code/` | Yes | Reuse; behavior is driven entirely by config + outputs. |

---

## Requirements

- **Terraform** ≥ 1.5
- **Google Cloud** project with billing enabled, `gcloud` CLI installed, and Application Default Credentials configured.
- **Python** 3.11 (see `ML-code/requirements.txt` for exact dependencies).
- **Docker** for building the Cloud Run image (via CI/CD or locally).
