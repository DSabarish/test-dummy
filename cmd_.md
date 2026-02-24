############################################
# ✅ GOLDEN PATH — FULL EXECUTION SCRIPT
############################################

# -------------------------------
# 🔹 PROJECT VARIABLE
# -------------------------------
$PROJECT_ID = "sabs-dev-100"
echo $PROJECT_ID

# -------------------------------
# ✅ STEP 1 — Environment & Tools
# -------------------------------
terraform -version
gcloud version

# Clear any manually set credentials path
$env:GOOGLE_APPLICATION_CREDENTIALS=""

# -------------------------------
# ✅ STEP 2 — Authentication & Project Setup
# -------------------------------

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

# -------------------------------
# ✅ STEP 3 — Enable Required APIs
# -------------------------------_
gcloud services enable artifactregistry.googleapis.com --project $PROJECT_ID
gcloud services enable bigquery.googleapis.com --project $PROJECT_ID 
gcloud services enable iam.googleapis.com --project $PROJECT_ID


gcloud services enable `
  run.googleapis.com `
  artifactregistry.googleapis.com `
  bigquery.googleapis.com `
  iam.serviceaccounts.actAs `
  --quiet

gcloud services enable `
  run.googleapis.com `
  artifactregistry.googleapis.com `
  bigquery.googleapis.com `
  --quiet

gcloud projects add-iam-policy-binding sabs-1000 `
  --member="user:sabsdrive05@gmail.com" `
  --role="roles/iam.serviceAccountUser"

gcloud iam service-accounts add-iam-policy-binding `
  mlapp-dev-runtime@sabs-1000.iam.gserviceaccount.com `
  --member="serviceAccount:mlapp-dev-cicd@sabs-1000.iam.gserviceaccount.com" `
  --role="roles/iam.serviceAccountUser"

# -------------------------------
# ✅ STEP 4 — Prepare Terraform
# -------------------------------

cd terraform

# Ensure dev.tfvars contains:
# project_id = "$PROJECT_ID"

# Wipe old state (prevents cross-project issues)
rm terraform.tfstate -ErrorAction SilentlyContinue
rm terraform.tfstate.backup -ErrorAction SilentlyContinue

# Fresh initialization
terraform init -reconfigure

# -------------------------------
# ✅ STEP 5 — Plan
# -------------------------------
terraform plan -var-file="dev.tfvars"

# Verify:
# - All resources show project = "$PROJECT_ID"
# - Plan summary looks correct

# -------------------------------
# ✅ STEP 6 — Apply
# -------------------------------
terraform apply -var-file="dev.tfvars"
# Type 'yes' when prompted

############################################
# ✅ DONE — INFRA DEPLOYED TO $PROJECT_ID
############################################


artifact_repo_url = "asia-south1-docker.pkg.dev/sabs-1000/mlapp-dev-repo"
artifacts_bucket = "mlapp-dev-artifacts-sabs-1000"
cicd_service_account = "mlapp-dev-cicd@sabs-1000.iam.gserviceaccount.com"
data_bucket = "mlapp-dev-data-sabs-1000"
dataset_id = "training_dataset_dev"
runtime_service_account = "mlapp-dev-runtime@sabs-1000.iam.gserviceaccount.com"
PS C:\Users\Selvam Sabarish\Desktop\sabs\my_work_on_cnp_projects\DN_Terraform\InfraBuild3\terraform> 




