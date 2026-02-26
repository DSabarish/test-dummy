# New project template — Setting up GCP ML infra

Use this folder to **start a new project** from the same Terraform and config pattern. It contains only the code and a config template; no state or cache.

---

## What’s in this folder

```
new-project-template/
├── README.md           ← You are here (how to use)
├── config.yaml         ← Edit this: set YOUR project IDs and env values
├── .github/
│   └── workflows/
│       └── cicd.yml    ← Runs ML-code/run_pipeline.py (test + pipeline + deploy)
├── ML-code/            ← Template scripts: print config vars to show they are callable
│   ├── config_loader.py   Loads config.yaml (use cfg['project_id'] etc.)
│   ├── run_pipeline.py    Print-only; replace with your real pipeline
│   └── requirements.txt  pyyaml only (add pandas, sklearn, etc. when you add ML)
└── terraform/
    ├── config.tf       ← Reads config.yaml from parent folder
    ├── main.tf         ← GCP resources (buckets, BigQuery, IAM, Artifact Registry)
    └── config-generator/   ← Optional: export env file from config (no GCP)
        └── main.tf
```

- **ML-code:** Template Python scripts with **commented variables** you can use (`project_id`, `data_bucket`, `dataset_id`, etc.). `run_pipeline.py` only **prints** those values from `config.yaml` (and from CI env when Terraform outputs are loaded) so you see they are properly callable. Replace with your real ML steps.
- **.github/workflows/cicd.yml:** Runs `run_pipeline.py` in the **test** job (config check) and **pipeline** job (with Terraform outputs and GCP auth), then **deploy** (Cloud Run). You need `terraform-output.json` committed and **GCP_SA_KEY** in GitHub Secrets for pipeline/deploy to succeed.

**Not included (on purpose):** `.terraform/`, `*.tfstate`, `terraform-output.json`. You will create these when you run Terraform in the new project.

---

## How to use this template

### New repo from this template

1. **Copy this whole folder** into your new repo’s root (or create a new repo and copy the contents so that `config.yaml` and `terraform/` sit at the **root** of the repo).

   Result should look like:
   ```
   your-new-repo/
   ├── config.yaml      ← from this template (then edit)
   ├── .github/workflows/cicd.yml
   ├── ML-code/
   │   ├── config_loader.py
   │   ├── run_pipeline.py
   │   └── requirements.txt
   └── terraform/
       ├── config.tf
       ├── main.tf
       └── config-generator/
   ```

2. **Edit `config.yaml`** (at repo root):
   - Replace `YOUR_PROJECT_ID_DEV`, `YOUR_PROJECT_ID_QA`, `YOUR_PROJECT_ID_PROD` with your real GCP project IDs.
   - Adjust `region`, `prefix`, `dataset_id`, `table_id` if needed.
   - Keep the same structure (environments.dev / .qa / .prod).

3. **Authenticate and enable APIs** (once per project):
   ```bash
   gcloud auth login

   gcloud auth application-default login
   
   $PROJECT_ID="sabs-dev5-100"
   echo $PROJECT_ID
   
   gcloud config set project $PROJECT_ID
   
   gcloud services enable artifactregistry.googleapis.com bigquery.googleapis.com iam.googleapis.com run.googleapis.com storage.googleapis.com --project $PROJECT_ID
   
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com bigquery.googleapis.com iam.googleapis.com --project $PROJECT_ID
   ```
   Repeat for qa/prod if you use separate projects.

4. **Run Terraform** (from repo root):
   ```bash
   cd terraform
   terraform -version
   terraform init
         or
   terraform init -reconfigure
   terraform plan -var="active_env=dev"
   terraform apply -var="active_env=dev"
   > yes
   ```
   For qa/prod: run again with `-var="active_env=qa"` and `-var="active_env=prod"`.

5. **Export outputs for CI/CD and ML**:
   ```bash
   terraform output -json > terraform-output.json
   ```
   Commit `terraform-output.json` (no secrets; CI/CD and pipelines read it).

6. If you use **GitHub Actions**: add the new project’s CI/CD service account key as **GCP_SA_KEY** in GitHub Secrets. The workflow runs **test** (config check via `run_pipeline.py`), **pipeline** (same script with Terraform outputs), and **deploy** (Cloud Run). For deploy you also need a **Dockerfile** at repo root that builds your app image.

7. **Local check:** From repo root, `pip install -r ML-code/requirements.txt` then `python ML-code/run_pipeline.py` to confirm config vars print correctly.

---

## Terraform: cautions and good practices

**Cautions when working with Terraform**

- **State and backend:** Do **not** commit `*.tfstate` or `.terraform/`. They contain paths, IDs, and (in some setups) secrets. This template uses local state; for teams, use a remote backend (e.g. GCS bucket) and lock it.
- **`active_env`:** Always pass `-var="active_env=dev"` (or qa/prod) on `plan` and `apply`. Wrong env = wrong project and possible production changes.
- **Destructive options:** `bucket_force_destroy: true` and `dataset_delete_on_destroy: true` in config allow Terraform to delete data when you destroy. Use only in dev; keep them `false` in qa/prod.
- **Plan before apply:** Run `terraform plan -var="active_env=..."` and review the diff before every `apply`. Avoid applying blindly in CI without reviewing.
- **No manual drift:** Prefer changing infra via Terraform (edit `.tf` or `config.yaml`, then plan/apply). Manual changes in GCP console will be overwritten or cause drift.

**Good practices to follow**

- **One apply per env:** Run `terraform apply` separately for dev, qa, and prod with the correct `active_env`. Do not apply once and assume all envs are in sync.
- **Commit `terraform-output.json`:** After the first apply (and after any change that affects outputs), run `terraform output -json > terraform-output.json` and commit it so CI/CD and ML code see current bucket names, project ID, etc.
- **Pin provider versions:** Keep required provider versions in `config.tf` (or `versions.tf`) so everyone and CI use the same Terraform/provider versions.
- **Small, reviewable changes:** Prefer small Terraform changes and review them like code. Use meaningful commit messages (e.g. "add qa bucket lifecycle rule").
- **Backup state (if local):** If you use local state, back up the state file and `.terraform.lock.hcl` before big changes. Prefer a remote backend for anything shared or production.

---

## Troubleshooting

**`oauth2: cannot fetch token: 400 Bad Request` / `Invalid grant: account not found`**

Terraform is using invalid or expired Google Cloud credentials. Re-authenticate with the account that has access to your GCP project:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID_DEV
```

Use the same Google account that is a member of the GCP project. If you changed your Google password or revoked app access, you must run these commands again. Then retry `terraform plan` and `terraform apply`.

---

## Golden path — full execution script (PowerShell)

Run this end-to-end on Windows (PowerShell) after editing `config.yaml` with your project ID. Replace `YOUR_PROJECT_ID_DEV` and `YOUR_EMAIL@gmail.com` with your values.

```powershell
############################################
# GOLDEN PATH — FULL EXECUTION SCRIPT
############################################

# -------------------------------
# PROJECT VARIABLE (must match config.yaml environments.dev.project_id)
# -------------------------------
$PROJECT_ID = "YOUR_PROJECT_ID_DEV"
echo $PROJECT_ID

# -------------------------------
# STEP 1 — Environment & tools
# -------------------------------
terraform -version
gcloud version

# Clear any manually set credentials path (use gcloud default)
$env:GOOGLE_APPLICATION_CREDENTIALS = ""

# -------------------------------
# STEP 2 — Authentication & project setup
# -------------------------------
gcloud auth application-default revoke
gcloud auth login
gcloud auth application-default login

gcloud config set project $PROJECT_ID
gcloud auth application-default set-quota-project $PROJECT_ID

# Verification ("Big Three")
gcloud auth list
gcloud config get-value project
cat $env:APPDATA\gcloud\application_default_credentials.json

# -------------------------------
# STEP 3 — Enable required APIs
# -------------------------------
gcloud services enable artifactregistry.googleapis.com --project $PROJECT_ID
gcloud services enable bigquery.googleapis.com         --project $PROJECT_ID
gcloud services enable iam.googleapis.com             --project $PROJECT_ID
gcloud services enable run.googleapis.com              --project $PROJECT_ID
gcloud services enable storage.googleapis.com          --project $PROJECT_ID

# Optional: grant your user "act as" the runtime SA (for local Cloud Run testing)
# gcloud projects add-iam-policy-binding $PROJECT_ID `
#   --member="user:YOUR_EMAIL@gmail.com" `
#   --role="roles/iam.serviceAccountUser"

# Optional: let CICD SA act as runtime SA (needed for deploy)
# Run after first terraform apply (replace with your project ID and SA names)
# gcloud iam service-accounts add-iam-policy-binding `
#   mlapp-dev-runtime@$PROJECT_ID.iam.gserviceaccount.com `
#   --member="serviceAccount:mlapp-dev-cicd@$PROJECT_ID.iam.gserviceaccount.com" `
#   --role="roles/iam.serviceAccountUser"

# -------------------------------
# STEP 4 — Prepare Terraform
# -------------------------------
cd terraform

# Wipe old state only if switching project (prevents cross-project issues)
# rm terraform.tfstate -ErrorAction SilentlyContinue
# rm terraform.tfstate.backup -ErrorAction SilentlyContinue

terraform init -reconfigure

# -------------------------------
# STEP 5 — Plan
# -------------------------------
terraform plan -var="active_env=dev"
# Verify: all resources show project = "$PROJECT_ID"

# -------------------------------
# STEP 6 — Apply
# -------------------------------
terraform apply -var="active_env=dev"
# Type 'yes' when prompted

# -------------------------------
# STEP 7 — Export outputs for CI/CD and ML
# -------------------------------
terraform output -json > terraform-output.json
cd ..
# Commit terraform-output.json

############################################
# DONE — Infra deployed to $PROJECT_ID
############################################
```

**Expected outputs (example):** `artifact_repo_url`, `artifacts_bucket`, `cicd_service_account`, `data_bucket`, `dataset_id`, `project_id`, `region`, `runtime_service_account`, `table_id`.