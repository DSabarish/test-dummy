# Terraform Implementation Guide <img src="./logo.png" alt="DataNeurus logo" align="right" width="150" />

## Terraform + CI/CD: Infrastructure as Code for ML/AI/Data Projects

> **Document Type:** Internal Engineering Reference  
> **Audience:** Engineers new to Infrastructure as Code (beginner → intermediate)  
> **Status:** 🟡 Active Template — Under Review  
> **Last Updated:** 26-02-2026

---

## Table of Contents

1. [Introduction](01-introduction.md)
2. [Why Terraform Instead of Python + GCP SDK](02-why-terraform-python-gcp-sdk.md)
3. [Responsibility Split: Terraform vs CI/CD](03-responsibility-split-terraform-cicd.md)
4. [Terraform Project Structure](04-terraform-project-structure.md)
5. [Terraform Code Walkthrough](05-terraform-code-walkthrough.md)
6. [Terraform Workflow](06-terraform-workflow.md)
7. [CI/CD Integration](07-cicd-integration.md)
8. [Maintenance & Scaling](08-maintenance-scaling.md)
9. [Quick Reference Cheatsheet](09-quick-reference-cheatsheet.md)
10. [End-to-End Flowchart (Terraform + CI/CD)](10-terraform-cicd-flowchart.md)

---

**Part 7 · CI/CD Integration** · [← Index](README.md)

---

## 7. CI/CD Integration

### 7.1 How GitHub Actions Integrates with Terraform

The DataNeurus CI/CD pipeline is designed around a critical principle:

> **Terraform changes are reviewed before they are applied, just like application code.**

This is achieved through the **Pull Request → Plan, Merge → Apply** pattern.

---

### 7.2 The Full CI/CD Workflow

```
┌──────────────────────────────────────────────────────────────────────┐
│                   GITHUB ACTIONS WORKFLOW                            │
│                                                                      │
│  Trigger: push to dev / qa / prod                                    │
│                                                                      │
│  ┌─────────┐    ┌──────────────┐    ┌────────────────┐               │
│  │  test   │───►│   pipeline   │───►│    deploy      │               │
│  │         │    │              │    │                │               │
│  │ pytest  │    │ Load outputs │    │ Load outputs   │               │
│  │         │    │ Auth to GCP  │    │ Auth to GCP    │               │
│  └─────────┘    │ Run ML code  │    │ Build Docker   │               │
│                 └──────────────┘    │ Push to AR     │               │
│                                     │ gcloud run     │               │
│                                     │ deploy         │               │
│                                     └────────────────┘               │
│                                              │                       │
│                                              ▼                       │
│                                     ┌────────────────┐               │
│                                     │   push-code    │               │
│                                     │ (dev → qa →    │               │
│                                     │  prod chain)   │               │
│                                     └────────────────┘               │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 7.3 How CI/CD Reads Terraform Outputs

Each job starts by loading infrastructure values from `terraform/terraform-output.json`:

```yaml
# .github/workflows/cicd.yml (simplified)

jobs:
  pipeline:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set environment from branch
        run: echo "ACTIVE_ENV=${{ github.ref_name }}" >> $GITHUB_ENV

      - name: Load Terraform outputs
        run: |
          python3 - <<'EOF'
          import json, os

          # Read terraform-output.json (committed to repo, no secrets)
          with open("terraform/terraform-output.json", "r", encoding="utf-8-sig") as f:
              outputs = json.load(f)

          # Write to GITHUB_ENV so subsequent steps can use them
          with open(os.environ["GITHUB_ENV"], "a") as env_file:
              env_file.write(f"GCP_PROJECT={outputs['project_id']['value']}\n")
              env_file.write(f"DATA_BUCKET={outputs['data_bucket']['value']}\n")
              env_file.write(f"ARTIFACTS_BUCKET={outputs['artifacts_bucket']['value']}\n")
              env_file.write(f"DATASET_ID={outputs['dataset_id']['value']}\n")
              env_file.write(f"TABLE_ID={outputs['table_id']['value']}\n")
          EOF

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}  # The ONLY secret

      - name: Run ML Pipeline
        run: python ML-code/run_pipeline.py
        env:
          ACTIVE_ENV: ${{ env.ACTIVE_ENV }}
          GCP_PROJECT: ${{ env.GCP_PROJECT }}
          DATA_BUCKET: ${{ env.DATA_BUCKET }}
```

---

### 7.4 The Deploy Job: Cloud Run via CI/CD

```yaml
  deploy:
    needs: pipeline
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Load Terraform outputs
        run: |
          # (same pattern as pipeline job)
          # Exports: GCP_PROJECT, REGION, ARTIFACT_REPO_URL, RUNTIME_SERVICE_ACCOUNT

      - name: Auth to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Setup gcloud
        uses: google-github-actions/setup-gcloud@v2

      - name: Authenticate Docker to Artifact Registry
        run: gcloud auth configure-docker ${{ env.REGION }}-docker.pkg.dev

      - name: Build and Push Docker Image
        run: |
          IMG="${{ env.ARTIFACT_REPO_URL }}/app:${{ github.sha }}"
          docker build -t "$IMG" .
          docker push "$IMG"
          echo "IMAGE=$IMG" >> $GITHUB_ENV

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy app \
            --image "${{ env.IMAGE }}" \
            --region "${{ env.REGION }}" \
            --platform managed \
            --allow-unauthenticated \
            --service-account "${{ env.RUNTIME_SERVICE_ACCOUNT }}" \
            --set-env-vars "GCP_PROJECT=${{ env.GCP_PROJECT }},ACTIVE_ENV=${{ env.ACTIVE_ENV }}"
```

> 💡 **Notice:** Cloud Run is deployed **only via `gcloud run deploy`**. Terraform never touches Cloud Run. This is an intentional architectural boundary. Cloud Run is an "application concern" — it changes with every code push. Terraform manages "infrastructure" — things that persist and are shared.

---

### 7.5 Pull Request → Plan (Recommended Addition)

For teams wanting even more safety, add a Terraform plan step on Pull Requests:

```yaml
# Triggered on pull requests targeting dev/qa/prod
on:
  pull_request:
    branches: [dev, qa, prod]

jobs:
  terraform-plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Auth to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Terraform Init
        run: terraform -chdir=terraform init -reconfigure

      - name: Terraform Plan
        run: |
          BRANCH="${{ github.base_ref }}"
          terraform -chdir=terraform plan -var="active_env=$BRANCH"
          # Plan output is shown in the PR for review
```

This means:
- **PR opened** → `terraform plan` runs, shows what infra would change → reviewers can see it
- **PR merged** → `terraform apply` runs (or is run manually by an engineer with the output file)

**Why this prevents accidental infra changes:**
- Infrastructure changes are peer-reviewed, just like code
- No one can accidentally delete a BigQuery dataset by merging a PR without others seeing it in the plan output
- The plan output is a comment on the PR (with additional tooling like Atlantis or Terraform Cloud)

---

### 7.6 Branch = Environment Mapping

The pipeline relies on a convention where **branch name = environment name**:

```
Branch: dev   →  ACTIVE_ENV=dev   →  Uses environments.dev in config.yaml
Branch: qa    →  ACTIVE_ENV=qa    →  Uses environments.qa in config.yaml
Branch: prod  →  ACTIVE_ENV=prod  →  Uses environments.prod in config.yaml
```

**Promotion chain** (configured in `config.yaml`):

```
dev ──► qa ──► prod
        ↑         ↑
    push_to_next  push_to_next
   _branch=true  _branch=false
```

After a successful deploy to `dev`, CI/CD automatically merges code to `qa`. After `qa` succeeds, code is promoted to `prod`. This is the **GitOps promotion pattern**.

> ⚠️ **Guard:** The workflow trigger is restricted to exactly `[dev, qa, prod]`. Feature branches do not trigger the pipeline.

---

[← Previous: Terraform Workflow](06-terraform-workflow.md) · [Index](README.md) · [Next: Maintenance & Scaling →](08-maintenance-scaling.md)
