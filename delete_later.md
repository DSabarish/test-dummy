### 1. What this repo is doing (current state)

#### 1.1 Terraform (`terraform/main.tf` + `terraform/config.tf`)

Terraform manages **only core GCP infra**:

- **Artifact Registry**
  - `google_artifact_registry_repository.repo`
  - Name: `<prefix>-<environment>-repo` (e.g. `mlapp-dev-repo`)
  - Region: from `config.yaml`
  - Format: DOCKER
  - Labeled via `labels` from config.

- **BigQuery**
  - `google_bigquery_dataset.dataset`
    - `dataset_id`, `dataset_location`, `delete_contents_on_destroy` from config.
  - `google_bigquery_table.table`
    - `dataset_id`, `table_id`, `schema = jsonencode(local.config.table_schema)`
    - `deletion_protection = false`.
  - Dataset/table labels from config.

- **GCS buckets**
  - `google_storage_bucket.artifacts`
    - Name: `<prefix>-<env>-artifacts-<project_id>`
    - `bucket_storage_class`, `bucket_force_destroy`
    - `lifecycle_rule` age = `artifacts_retention_days`.
  - `google_storage_bucket.data`
    - Name: `<prefix>-<env>-data-<project_id>`
    - `lifecycle_rule` age = `data_retention_days`.
  - Both with uniform bucket‑level access and `labels`.

- **Service accounts and IAM**
  - `google_service_account.cicd` and `google_service_account.runtime`.
  - `google_project_iam_member.cicd_roles` for **CI/CD SA**, roles from per‑env block in `config.yaml`:
    - dev / qa: admin‑ish (storage.admin, artifactregistry.admin, bq dataEditor, jobUser, iam.serviceAccountUser, run.admin).
    - prod: **tightened** (storage.objectAdmin, artifactregistry.writer, etc.).
  - `google_project_iam_member.runtime_roles` for **runtime SA** (read‑only BQ + GCS).

- **Outputs** (used only by CI/CD)
  - `project_id`, `region`
  - `artifact_repo_url`
  - `artifacts_bucket`, `data_bucket`
  - `dataset_id`, `table_id`
  - `cicd_service_account`, `runtime_service_account`

All of the above are driven from a **single master `config.yaml`** using:

- `active_env: "dev" | "qa" | "prod"`
- `environments.dev|qa|prod` blocks (project/env, Terraform settings, BQ schema, ML paths, CI/CD promotion flags).

`terraform/config.tf`:

- `var active_env` (overridable via `-var="active_env=..."`).
- `_raw = yamldecode(file("../config.yaml"))`
- `_env = coalesce(var.active_env, _raw.active_env)`
- `_cfg = _raw.environments[_env]`
- `local.config` is built from `_cfg` (no duplication).

#### 1.2 Cloud Run and CI/CD (`.github/workflows/cicd.yml`)

- **Trigger:** on push to `dev`, `qa`, `prod` + `workflow_dispatch`.
- **Shared env:** `PYTHON_VERSION=3.11`.

**Jobs:**

- `test`:
  - Checkout, set up Python, install requirements, run `pytest`.

- `pipeline`:
  - Checkout.
  - Set `ACTIVE_ENV=${{ github.ref_name }}` (dev/qa/prod).
  - **Load infra values from `terraform/terraform-output.json`**:
    - Using Python to robustly parse JSON (handles BOM/encoding/CRLF).
    - Export:
      - `GCP_PROJECT`, `DATA_BUCKET`, `ARTIFACTS_BUCKET`, `DATASET_ID`, `TABLE_ID`.
  - Auth to GCP via `google-github-actions/auth@v2` with:
    - `credentials_json: ${{ secrets.GCP_SA_KEY }}` (**the only secret**).
  - Setup Python, install `ML-code/requirements.txt`.
  - Run `python ML-code/run_pipeline.py` with env:
    - `ACTIVE_ENV` (env name from branch).
    - `GCP_PROJECT`, `DATA_BUCKET`, `ARTIFACTS_BUCKET`, `DATASET_ID`, `TABLE_ID`.

- `deploy`:
  - Checkout.
  - Set `ACTIVE_ENV=${{ github.ref_name }}`.
  - Load infra values from **the same `terraform/terraform-output.json`**:
    - `GCP_PROJECT`, `ARTIFACTS_BUCKET`, `REGION`, `ARTIFACT_REPO_URL`, `RUNTIME_SERVICE_ACCOUNT`.
  - Auth to GCP with `GCP_SA_KEY`.
  - Setup gcloud; Docker auth to `<REGION>-docker.pkg.dev`.
  - **Build & push image**:
    - `REPO="${{ env.ARTIFACT_REPO_URL }}"`.
    - `IMG="$REPO/app:${{ github.sha }}"`.
    - `docker build -t "$IMG" . && docker push "$IMG"`.
    - `IMAGE` exported to `$GITHUB_ENV`.

  - **Deploy Cloud Run via CLI**:

    ```bash
    gcloud run deploy app \
      --image "${{ env.IMAGE }}" \
      --region "${{ env.REGION }}" \
      --platform managed \
      --allow-unauthenticated \
      --service-account "${{ env.RUNTIME_SERVICE_ACCOUNT }}" \
      --set-env-vars "GCP_PROJECT=${{ env.GCP_PROJECT }},ARTIFACTS_BUCKET=${{ env.ARTIFACTS_BUCKET }},ACTIVE_ENV=${{ env.ACTIVE_ENV }}"
    ```

    - This is the **only place Cloud Run is created/updated.**
    - Cloud Run config (SA, region, env vars) is **owned by CI**, not Terraform.

- `push-code` (branch promotion):
  - Runs after `deploy`.
  - Checkout with write token.
  - Set `ACTIVE_ENV=${{ github.ref_name }}`.
  - Install `pyyaml`, load `config.yaml`, select `environments[ACTIVE_ENV]`.
  - Read **per‑env** `push_to_next_branch` and `next_branch_name`:
    - dev: true, "qa"
    - qa: true, "prod"
    - prod: false, "" (end of chain).
  - Edge cases:
    - If env missing → skip (write `PUSH_TO_NEXT_BRANCH=false`).
    - If `push_to_next_branch=false` or `next_branch_name` empty → skip.
  - If `PUSH_TO_NEXT_BRANCH == 'true'` and `NEXT_BRANCH_NAME != ''`:
    - Fetch, check if branch exists:
      - If exists: checkout `<next>`, merge `<current>`, push.
      - Else: create `<next>` from `<current>`, push `-u`.

#### 1.3 Python / Docker


- **`ML-code/config_loader.py`**:
  - Reads `config.yaml`, selects env block via `ACTIVE_ENV` or `active_env`.
  - Derives:
    - `feature_columns` from `table_schema` minus `target_column`.
    - Buckets, repo URL, service account emails.
  - All ML modules (`generate_data.py`, `clean.py`, `train.py`, `inference.py`, etc.) import `load_config()`; they never read env-specific infra from secrets.

- **Dockerfile**:
  - Copies `ML-code/` and `frontend/`, and `config.yaml` into the image.
  - Runs `uvicorn inference:app --host 0.0.0.0 --port ${PORT:-8080}`.
  - At runtime, inference uses `load_config()` + `ACTIVE_ENV` from Cloud Run env vars.

---

### 2. Confirming your desired architecture

Per your constraints:

1. **Terraform does NOT manage Cloud Run**  
   ✅ Confirmed. There is no Cloud Run resource in `terraform/main.tf` or elsewhere.

2. **CI/CD deploys Cloud Run using `gcloud run deploy`**  
   ✅ Confirmed. All Cloud Run creation/updates are done in the `deploy` job via `gcloud run deploy app ...`.

3. **CI reads all infra values from `terraform/terraform-output.json`**  
   ✅ Confirmed.
   - Both `pipeline` and `deploy` use the Python snippet to parse `terraform/terraform-output.json` and export:
     - `project_id`, `region`, `table_id`, `artifacts_bucket`, `data_bucket`, `dataset_id`, `cicd_service_account`, `runtime_service_account`.
   - There is no dependency on `terraform.tfstate` in CI.

4. **No infra values duplicated in GitHub secrets**  
   ✅ Confirmed.
   - Only secret in use is `GCP_SA_KEY` for the CI/CD service account.
   - `GCP_PROJECT`, buckets, dataset, table, region, SAs are **all derived from Terraform outputs**, not from `secrets.*`.

5. **Cloud Run as “application concern” owned by CI**  
   ✅ Confirmed in practice and code:
   - Terraform doesn’t see Cloud Run.
   - All Cloud Run configuration (image, env vars, region, runtime SA) flows from:
     - Terraform outputs → CI env vars → `gcloud run deploy`.

6. **Documented in README**  
   ✅ Largely done:
   - README has:
     - “Central configuration: one file, all environments”.
     - Config flow (config → Terraform vs config → ML vs config → CI).
     - CI/CD section describing reading `terraform-output.json`, using `ACTIVE_ENV`, and deploy to Cloud Run.
   - If you want, we can further tighten wording to explicitly say: “Cloud Run is configured and deployed **only** via CI/CD (`gcloud run deploy`), not Terraform.”

---

### 3. Cleanliness, duplication, and clarity

You already made **big strides** toward a very clean architecture:

- **Single `config.yaml`** for dev/qa/prod with clear, opinionated comments.
- **Terraform** reads only from `environments[active_env]`.
- **ML** reads only from the same.
- **CI** reads infra dynamically from `terraform/terraform-output.json`.
- No secrets for infra identifiers.

Remaining points (critique, not blockers):

- **Cloud Run configuration is “procedural” in CI**  
  - All tuning (CPU, memory, concurrency, min/max instances, timeout, ingress) lives in the `gcloud run deploy` flags.
  - You started to document platform options in `config.yaml` but haven’t wired them into the `gcloud` call yet.
  - That’s acceptable in this architecture, but you should treat the deploy step as part of “app config” and document any future Cloud Run tuning flags in README/config.

- **Hidden coupling: branch name = environment**  
  - `ACTIVE_ENV=${{ github.ref_name }}` assumes branches are *exactly* `dev`, `qa`, `prod`.
  - That’s fine, but it is implicit coupling. README does mention this; I’d keep that explicit.

- **Promotion semantics are encoded in config.yaml**  
  - dev → qa, qa → prod, prod stops. That’s good and explicit.
  - It also means that if someone changes `next_branch_name` without understanding the pipeline, you can route code in unexpected ways. You already guard against empty names; that’s good defense.

- **Service accounts**  
  - CI/CD SA has broad roles in dev/qa, tightened in prod—good. Long‑term, consider Workload Identity Federation instead of key‑based `GCP_SA_KEY`, but that’s a separate security improvement and still consistent with your architecture (CI → Cloud Run via `gcloud run deploy`).

I don’t see any **dead code** or duplicate config inside this repo now:
- No extra `config.py`, no stray `config.yaml` copies for ML only.
- The old `ml_app_env.txt` flow has been relegated to `terraform/config-generator` only.

---

### 4. Architectural risks and hidden coupling

- **Risk: CI and console changes drift Cloud Run away from expectations**  
  - Since Terraform doesn’t track Cloud Run, this is by design: Cloud Run is “app space”.
  - Mitigation is **process/documentation**, not IaC:
    - Keep Cloud Run flags centralized in CI.
    - Document them in README and maybe a dedicated “Cloud Run config” section.
    - Avoid ad‑hoc console edits in prod.

- **Risk: Wrong branch / env mapping**  
  - If someone introduces a `feature/...` branch that also triggers this workflow, `ACTIVE_ENV` will be `feature/...` and `config_loader`/CI will fail.
  - Right now, triggers are restricted to `[dev, qa, prod]`, which is good. I’d keep that narrow.

- **Security: JSON key in secrets**  
  - Using `GCP_SA_KEY` is standard but comes with the usual risks (key leakage, long‑lived credentials).
  - Long‑term, consider moving to **Workload Identity Federation** for GitHub Actions; architecture remains the same (CI still owns Cloud Run).

- **Coupling: Bucket and dataset names encoded in config.yaml**  
  - This is intentional and good: you want config to be the master.
  - Just be aware that Cloud Run’s env vars (GCP_PROJECT, ARTIFACTS_BUCKET) must be derived from Terraform outputs to avoid duplication—which you’re already doing.

---

### 5. Suggested improvements **within your architecture**

All of these respect your explicit constraints (Cloud Run stays CI‑only):

1. **Make Cloud Run flags more “config‑like”**  
   - You already added a commented “Platform/infrastructure” block to `config.yaml` (min_instances, max_instances, cpu, memory, timeout, concurrency, etc.).
   - Next step (when you feel ready): wire those into `gcloud run deploy`:
     - Read them in CI (similar to how you read `terraform-output.json`), or pass them as static flags if you don’t need per‑env variance yet.
   - This keeps Cloud Run in CI, but makes the knob values more visible and centralized.

2. **Explicit Cloud Run doc in README**  
   - Add a mini‑section under “What this repo does” or “CI/CD”:
     - **Infra (Terraform):** Artifact Registry, BQ, GCS, IAM, outputs only.
     - **App (CI/CD):** Cloud Run service `app` is created/updated exclusively via `gcloud run deploy` in the `deploy` job. Terraform never touches it.
   - That matches your actual implementation and prevents future confusion.

3. **Add a sanity check for ACTIVE_ENV == known env**  
   - You already restrict triggers to `dev, qa, prod`.
   - Optionally add a guard in CI:
     - If `ACTIVE_ENV` not in `["dev","qa","prod"]`, fail early with a clear message.
   - This avoids weird behavior if someone later widens the branch filter.

4. **Optional: log Cloud Run deploy flags in CI output**  
   - Right now the `gcloud run deploy` line is clear; you might add comments above it explaining what each flag means (esp. when you start tuning scaling).
   - This is documentation, not code architecture, but it helps future maintainers.

---

### Bottom line

- **Your current setup already matches the target hybrid architecture:**
  - Terraform: infra only.
  - CI: app (Cloud Run) + ML pipeline.
  - `config.yaml`: single master config for dev/qa/prod.
  - `terraform/terraform-output.json`: single bridge from infra to CI.
  - Only real secret: `GCP_SA_KEY`.

- **I do NOT recommend moving Cloud Run into Terraform** given your stated direction.
- The main work left is **documentation polish and Cloud Run flag visibility**, not structural changes.

If you’d like, next step can be a tightened README snippet (just text here, no code changes) that you can paste in to make the “Terraform vs CI vs Cloud Run” boundary absolutely explicit for any future reader.