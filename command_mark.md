# Golden path — full execution script (PowerShell)

Run these blocks **line by line** from the repo root (folder that contains `config.yaml` and `terraform/`).  
Set `$PROJECT_ID` to match `project_id` in `config.yaml`.

---

## 1. Project variable

```powershell
$PROJECT_ID = "sabs-dev2-100"   # must match config.yaml project_id
echo $PROJECT_ID
```

---

## 2. Environment & tools

```powershell
terraform -version
gcloud version

# Clear any manually set credentials path
$env:GOOGLE_APPLICATION_CREDENTIALS = ""
```

---

## 3. Authentication & project setup

```powershell
# 1. Clear old sessions
gcloud auth application-default revoke

# 2. Login fresh
gcloud auth login
gcloud auth application-default login

# 3. Force focus to target project
gcloud config set project $PROJECT_ID
gcloud auth application-default set-quota-project $PROJECT_ID

# 4. Verification (The "Big Three")
gcloud auth list
gcloud config get-value project
cat $env:APPDATA\gcloud\application_default_credentials.json
```

---

## 4. Enable required APIs

```powershell
gcloud services enable artifactregistry.googleapis.com --project $PROJECT_ID
gcloud services enable bigquery.googleapis.com         --project $PROJECT_ID
gcloud services enable iam.googleapis.com              --project $PROJECT_ID
gcloud services enable run.googleapis.com              --project $PROJECT_ID --quiet

# Optional: single combined call
# gcloud services enable run.googleapis.com artifactregistry.googleapis.com bigquery.googleapis.com iam.serviceaccounts.actAs --project $PROJECT_ID --quiet
```

### Optional IAM bindings (edit email and project if needed)

```powershell
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="user:sabsdrive05@gmail.com" `
  --role="roles/iam.serviceAccountUser"

gcloud iam service-accounts add-iam-policy-binding `
  "mlapp-dev-runtime@${PROJECT_ID}.iam.gserviceaccount.com" `
  --member="serviceAccount:mlapp-dev-cicd@${PROJECT_ID}.iam.gserviceaccount.com" `
  --role="roles/iam.serviceAccountUser"
```

---

## 5. Prepare Terraform

```powershell
cd terraform

# When creating NEW infra in a different project: wipe state first
rm terraform.tfstate        -ErrorAction SilentlyContinue
rm terraform.tfstate.backup -ErrorAction SilentlyContinue

# Init (use -reconfigure when switching project)
terraform init -reconfigure
```

---

## 6. Plan

```powershell
terraform plan
# All inputs come from root config.yaml (no -var-file)
```

Verify: all resources show `project = $PROJECT_ID` and plan summary looks correct.

---

## 7. Apply

```powershell
terraform apply
# Type 'yes' when prompted
```

---

## 8. Export outputs for CI/CD

CI/CD reads **`terraform/outputs.json`** (no secrets). After every `terraform apply`, generate and commit it:

```powershell
# From terraform/ directory (you are already there after apply)
terraform output -json > outputs.json
# Then from repo root: git add terraform/outputs.json && git commit -m "chore: update Terraform outputs for CI/CD"
```

If this file is missing, the workflow will fail with a clear error. Do **not** add `terraform/outputs.json` to `.gitignore`.

---

## Done

Infra is deployed to `$PROJECT_ID`. Terraform outputs (e.g. after apply):

- `project_id`, `region`, `table_id`
- `artifact_repo_url`
- `artifacts_bucket`, `data_bucket`
- `dataset_id`
- `cicd_service_account`, `runtime_service_account`

---

## If you get 409 "already exists" errors

### Option A — Generate env file only (no GCP)

```powershell
cd terraform/config-generator
terraform init
terraform apply -auto-approve
# Output: terraform/config-generator/ml_app_env.txt
```

### Option B — Import existing resources into state

Run from `terraform/`. Replace `sabs-1000` with your `$PROJECT_ID` if different.

```powershell
terraform import google_artifact_registry_repository.repo projects/sabs-1000/locations/asia-south1/repositories/mlapp-dev-repo
terraform import google_bigquery_dataset.dataset          projects/sabs-1000/datasets/training_dataset_dev
terraform import google_bigquery_table.table             projects/sabs-1000/datasets/training_dataset_dev/tables/features_table
terraform import google_storage_bucket.artifacts          mlapp-dev-artifacts-sabs-1000
terraform import google_storage_bucket.data              mlapp-dev-data-sabs-1000
terraform import google_service_account.cicd             projects/sabs-1000/serviceAccounts/mlapp-dev-cicd@sabs-1000.iam.gserviceaccount.com
terraform import google_service_account.runtime           projects/sabs-1000/serviceAccounts/mlapp-dev-runtime@sabs-1000.iam.gserviceaccount.com

terraform apply
```


cd terraform && terraform output -json > outputs.json