# New project template — GCP infra + config

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

### Option A: New repo from this template

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
   gcloud config set project YOUR_PROJECT_ID_DEV
   gcloud services enable artifactregistry.googleapis.com bigquery.googleapis.com iam.googleapis.com run.googleapis.com storage.googleapis.com --project YOUR_PROJECT_ID_DEV
   ```
   Repeat for qa/prod if you use separate projects.

4. **Run Terraform** (from repo root):
   ```bash
   cd terraform
   terraform init -reconfigure
   terraform plan -var="active_env=dev"
   terraform apply -var="active_env=dev"
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

### Option B: New branch in the same repo

1. Create a new branch.
2. Copy the contents of **new-project-template/** to the repo root (so `config.yaml` and `terraform/` are at root; merge or replace as needed).
3. Follow steps 2–6 above: edit `config.yaml` with the new project IDs, run Terraform, export outputs, set secrets.

---

## Important

- **config.yaml** must stay at the **same level as `terraform/` and `ML-code/`** (repo root). Terraform reads `../config.yaml`; ML-code reads `config.yaml` from repo root.
- Do **not** copy any `terraform.tfstate` or `.terraform/` from another project. This template is code-only; each new project gets its own state after `terraform init` and `apply`.
- After the first `apply`, always run `terraform output -json > terraform-output.json` and commit it so CI/CD and ML code can use bucket names, project ID, etc.

---

## Folder name

You can rename **new-project-template** to something like **project-template** or **starter** if you prefer. The only requirement is that when you copy it into a repo, **config.yaml** and **terraform/** end up at the root of that repo.
