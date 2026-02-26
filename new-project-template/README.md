# GCP ML Infrastructure Setup <img src=".\logo.png" alt="DataNeurus logo" align="right" width="150" />

```powershell
############################################
#  GOLDEN PATH — FULL EXECUTION SCRIPT
#
# WHAT THIS DOES:
#   Sets up GCP infrastructure (Cloud Run, BigQuery,
#   Artifact Registry, IAM) for a new ML project
#   using Terraform. Run top-to-bottom, once per env.
#
# PREREQUISITES:
#   - Terraform installed  → https://developer.hashicorp.com/terraform/install
#   - gcloud CLI installed → https://cloud.google.com/sdk/docs/install
#   - A GCP project already created
############################################


# ══════════════════════════════════════════════════
# 🔹 PROJECT VARIABLE
#
# Set your real GCP project ID here.
# Every command below automatically uses this value.
# Change it when switching to a different project.
# ══════════════════════════════════════════════════
$PROJECT_ID = "sabs-dev5-100"
echo $PROJECT_ID


# ══════════════════════════════════════════════════
# 🔹 STEP 1 — Verify Environment & Tools
#
# Confirms Terraform and gcloud are installed.
# If either command errors, install the tool first
# before continuing.
# ══════════════════════════════════════════════════
terraform -version
gcloud version

# WHY: A stale GOOGLE_APPLICATION_CREDENTIALS env var
# can silently point to the wrong key file, causing
# auth failures. Clear it so gcloud uses ADC instead.
$env:GOOGLE_APPLICATION_CREDENTIALS=""


# ══════════════════════════════════════════════════
# 🔹 STEP 2 — Authentication & Project Setup
#
# Fully resets auth state so credentials are tied
# to THIS project only — not a previous session.
# ══════════════════════════════════════════════════

# 1. Revoke any existing Application Default Credentials.
#    WHY: Old sessions from a different project can
#    cause Terraform to deploy to the wrong project.
gcloud auth application-default revoke

# 2. Log in fresh (two commands needed):
#    - auth login         → for gcloud CLI commands
#    - application-default login → for Terraform & SDKs
gcloud auth login
gcloud auth application-default login

# 3. Lock gcloud and ADC to the target project.
#    WHY: Forces all API calls to bill and deploy
#    to $PROJECT_ID, not your personal default project.
echo $PROJECT_ID
gcloud config set project $PROJECT_ID
gcloud auth application-default set-quota-project $PROJECT_ID

# 4. THE "BIG THREE" — Verify everything is correct.
#    Run these and confirm before continuing:
#     auth list         → your email is ACTIVE
#     get-value project → shows $PROJECT_ID
#     cat credentials   → quota_project_id = $PROJECT_ID
gcloud auth list
gcloud config get-value project
cat $env:APPDATA\gcloud\application_default_credentials.json


# ══════════════════════════════════════════════════
# 🔹 STEP 3 — Enable Required GCP APIs
#
# GCP resources can't be created until their APIs
# are enabled. This is a one-time step per project.
# Safe to re-run — enabling an already-enabled API
# is a no-op.
# ══════════════════════════════════════════════════

# Enable individually (explicit, easy to debug):
gcloud services enable artifactregistry.googleapis.com --project $PROJECT_ID
gcloud services enable bigquery.googleapis.com --project $PROJECT_ID
gcloud services enable iam.googleapis.com --project $PROJECT_ID

# Enable all at once (final authoritative command):
gcloud services enable run.googleapis.com artifactregistry.googleapis.com bigquery.googleapis.com iam.googleapis.com --project $PROJECT_ID


# ══════════════════════════════════════════════════
# 🔹 STEP 4 — Prepare Terraform
#
# Navigate into the terraform/ folder and wipe any
# old state to prevent cross-project contamination.
# ══════════════════════════════════════════════════
cd terraform

# WHY remove state files: If you previously ran
# Terraform against a different project, stale state
# will confuse Terraform about what already exists.
# -ErrorAction SilentlyContinue = silently skip if
# the file doesn't exist yet.
rm terraform.tfstate        -ErrorAction SilentlyContinue
rm terraform.tfstate.backup -ErrorAction SilentlyContinue

# Download providers and set up the backend.
# -reconfigure forces a clean init, ignoring any
# cached backend config from a previous project.
terraform init -reconfigure


# ══════════════════════════════════════════════════
# 🔹 STEP 5 — Plan (Dry Run — No Changes Made)
#
# Shows exactly what Terraform WILL create/change
# before touching anything real.
# VERIFY:
#    Every resource shows project = $PROJECT_ID
#    Plan summary counts look right (no surprises)
# ══════════════════════════════════════════════════
terraform plan -var="active_env=dev"


# ══════════════════════════════════════════════════
# 🔹 STEP 6 — Apply (Creates Real GCP Resources)
#
# Executes the plan. Type 'yes' when prompted.
#
# To deploy other environments, re-run with:
#   terraform apply -var="active_env=qa"
#   terraform apply -var="active_env=prod"
# ══════════════════════════════════════════════════
terraform apply -var="active_env=dev"


# ══════════════════════════════════════════════════
# 🔹 STEP 7 — Export Terraform Outputs
#
# Saves resource names (bucket names, dataset IDs,
# Cloud Run URLs, etc.) to a JSON file.
# WHY: CI/CD pipelines and run_pipeline.py read this
# file to know WHERE to connect. No secrets are
# included — safe to commit to Git.
# ══════════════════════════════════════════════════
terraform output -json > terraform-output.json

# Commit terraform-output.json to your repo so
# GitHub Actions can use it in pipeline/deploy jobs.


############################################
# 🔹 DONE — INFRA DEPLOYED TO $PROJECT_ID
############################################


# ══════════════════════════════════════════════════
# 🔹 POST-SETUP CHECKLIST
# ══════════════════════════════════════════════════

# ── GitHub Actions Setup ──────────────────────────
# Add your CI/CD service account key to GitHub:
#   Repo → Settings → Secrets → New secret
#   Name: GCP_SA_KEY  |  Value: <contents of key JSON>
#
# The workflow runs 3 jobs automatically on push:
#   test     → python ML-code/run_pipeline.py (config check)
#   pipeline → same script but with Terraform outputs + GCP auth
#   deploy   → builds & pushes Docker image to Cloud Run
#
# ⚠️  deploy job also requires a Dockerfile at repo root.

# ── Local Smoke Test ─────────────────────────────
# Run from the repo ROOT (not terraform/) to confirm
# config.yaml loads and all vars print correctly:
pip install -r ML-code/requirements.txt
python ML-code/run_pipeline.py


# ══════════════════════════════════════════════════
# 🔹 TERRAFORM CAUTIONS & GOOD HABITS
# ══════════════════════════════════════════════════

# ⚠️  CAUTIONS — things that cause real damage if ignored:
#
#   ✗ Never commit *.tfstate or .terraform/ to Git
#     → State files can contain secrets; use a remote backend
#   ✗ Always pass -var="active_env=dev|qa|prod" on plan & apply
#     → Without it, Terraform uses the wrong env defaults
#   ✗ Never manually change infra in the GCP Console
#     → Terraform won't know, causing drift and broken applies
#   ✗ Read the plan output before every apply
#     → A "destroy" line in the plan means data loss
#   ✗ Be extremely careful with destroy in qa/prod
#     → Only use destroy freely in dev

#  GOOD HABITS — do these every time:
#
#   ✓ Run once per env: dev → qa → prod (never skip envs)
#   ✓ After every apply: terraform output -json > terraform-output.json
#     then commit the file so CI/CD stays in sync
#   ✓ Pin Terraform and provider versions in config.tf
#     so all teammates use identical tooling
#   ✓ Make small, reviewable changes — one resource at a time
#   ✓ Use a dedicated GCS bucket as a remote backend to store
#     all tfstate files (one per env/project), and always
#     check that state before applying changes
```