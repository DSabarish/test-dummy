## DataNeurus Terraform + CI/CD Template

This document is an internal, reusable guide for how DataNeurus sets up **Terraform integrated with CI/CD** as a template for ML/AI/Data projects on GCP.

It is written for engineers who:

- **know a bit of Python / GCP**, but
- **are new to Terraform and CI/CD**, and
- **want a practical, opinionated starting point**.

You can skim the high‑level ideas first, and come back to the code and commands later.

---

## 1. Introduction

### 1.1 What is CI/CD?

- **CI (Continuous Integration)**:  
  Every change you push (usually via pull request) is:
  - automatically built,
  - automatically tested, and
  - validated before it is merged.

- **CD (Continuous Delivery / Deployment)**:  
  Once changes are merged, an automated pipeline:
  - builds an artifact (e.g. Docker image),
  - deploys it to the target environment (dev / QA / prod),
  - runs post‑deploy checks where needed.

In this guide, **CI/CD = GitHub Actions pipelines** that run on each push/merge to `dev`, `qa`, or `prod` branches.

### 1.2 Why CI/CD matters for ML/AI/Data and cloud infrastructure

For ML/AI/Data projects we care about:

- **Reproducibility**:  
  - Same training data + same code + same infra → same result.  
  - CI ensures the pipeline is always run in the same environment.

- **Safety and speed**:
  - Automated tests catch bugs before they reach production.
  - Deployments are repeatable and fast, not manual click‑ops.

- **Traceability**:
  - Every deployment is tied to a Git commit, a pull request, and a pipeline run.
  - Easy audits: “what changed, when, and by whom?”

### 1.3 Common problems when CI/CD is used alone (without Terraform)

If you only have CI/CD for code, and infrastructure is created manually in the cloud console:

- **Manual infra creation**:
  - Buckets, BigQuery datasets, service accounts, Cloud Run services are created by hand.
  - Different people may click different options.

- **Configuration drift**:
  - Dev, QA, and prod slowly diverge because changes are made manually.
  - One environment has extra permissions / different timeouts / different names.

- **Hidden dependencies**:
  - Pipelines assume buckets/datasets already exist.
  - No clear place to see *how* infra is created or updated.

- **Poor reproducibility**:
  - Re‑creating an environment from scratch is painful.
  - “Disaster recovery” becomes: “hope we remember all the clicks we did last year”.

CI/CD alone automates **code** changes, but not **infra** changes.

### 1.4 How Terraform complements CI/CD

Terraform adds:

- **Declarative infrastructure**:
  - You describe *what you want* (buckets, datasets, roles) in `.tf` files.
  - Terraform figures out *how to get there*.

- **Single source of truth**:
  - Infrastructure definitions live in Git.
  - Code review applies to infra just like application changes.

- **State and drift detection**:
  - Terraform tracks what is currently deployed (state).
  - `terraform plan` shows you exactly what will change before it changes.

- **Safe, repeatable environments**:
  - Dev, QA, and prod are defined from the same template.
  - New projects can copy the template and get a standard setup quickly.

CI/CD + Terraform together give you:

- CI/CD → **automation & gates**.  
- Terraform → **consistent, reviewable, reproducible infra**.

---

## 2. Why Terraform instead of Python + GCP SDK?

Many engineers are comfortable with Python and the GCP SDK. It is tempting to:

- write Python scripts that call the GCP APIs, and
- let CI/CD run those scripts to create infrastructure.

This *works*, but has drawbacks compared to Terraform.

### 2.1 Imperative vs declarative infrastructure

- **Imperative (Python + GCP SDK)**:
  - You write step‑by‑step code:  
    “create bucket A → give role X to SA Y → update lifecycle rule Z”.
  - To change something, you must write new logic for all the branching cases:
    - “if bucket already exists then…”
    - “if permission is already there then…”
  - The script describes **how** to do things.

- **Declarative (Terraform)**:
  - You declare the desired end state:  
    “there must be a bucket `mlapp-dev-artifacts` in region `asia-south1` with lifecycle X”.
  - Terraform computes the **diff** between current state and desired state.
  - It generates the exact API calls needed (create, update, delete).
  - The code describes **what** you want, not how to get there.

For teams and long‑lived projects, declarative is usually easier to reason about and maintain.

### 2.2 Reproducibility, state management, drift detection

- **Terraform state**:
  - Terraform keeps a state file (ideally in a remote backend like GCS).
  - State links your config to the actual resources in GCP.

- **Reproducibility**:
  - If you run `terraform apply` against the same configuration and state, you will converge to the same infra.
  - No hidden steps, everything is in `.tf` files.

- **Drift detection**:
  - If someone changes a resource manually in the GCP console, `terraform plan` shows the drift.
  - You can decide to:
    - bring the cloud into alignment with code, or
    - update the code to reflect a manual change.

With pure Python scripts, you typically:

- don’t have a centralized state file,
- don’t get automatic drift detection,
- and must implement your own “is this resource already in the desired shape?” logic.

### 2.3 Maintainability and team collaboration

- **Reviewability**:
  - Terraform code is short and declarative; diffs are easy to review.
  - It is obvious what is changing between commits.

- **Standardization**:
  - Corporate patterns (labels, naming conventions, IAM roles) can be shared via modules/templates.
  - New projects copy the template instead of reinventing scripts.

- **Onboarding**:
  - A new engineer can quickly understand infra by reading `main.tf` and `config.yaml`.
  - With Python scripts, logic may be spread across many helper modules and functions.

### 2.4 When Python / GCP SDK is still useful

Terraform is not a replacement for **all** GCP scripting. Good uses of Python + GCP SDK:

- **Data / ML workloads**:
  - reading/writing data from GCS / BigQuery,
  - training models, running batch predictions.

- **One‑off migrations**:
  - complex data migration between schemas,
  - temporary scripts to fix historical issues.

- **Application logic**:
  - anything that happens *inside* your service / pipeline.

Terraform is the better choice for:

- **defining long‑lived infrastructure** (buckets, datasets, IAM, networks, Cloud Run services),
- **repeating the same setup** in dev/QA/prod,
- **keeping infra under version control**, with code review and CI/CD checks.

---

## 3. Responsibility Split: Terraform vs CI/CD

We recommend a **clear boundary**:

- **Terraform**: “What infra exists and how it is configured.”  
- **CI/CD**: “When and how we test, build, and deploy code.”

### 3.1 What belongs to Terraform?

- **Resource creation & configuration**:
  - GCS buckets for data and artifacts.
  - BigQuery datasets and tables.
  - Artifact Registry repositories.
  - Cloud Run service (name, region, runtime service account).

- **Access control (IAM)**:
  - CI/CD service accounts and their roles.
  - Runtime service accounts and their roles.

- **Environment‑specific settings**:
  - retention policies,
  - scale‑to‑zero vs always‑on,
  - region, labels, basic quotas.

### 3.2 What belongs to CI/CD?

- **Automation & orchestration**:
  - running tests (`pytest`),
  - running the ML pipeline (training / evaluation),
  - building Docker images,
  - deploying to Cloud Run using the infra created by Terraform.

- **Gates & safety**:
  - enforcing `terraform plan` on pull requests,
  - enforcing tests before merge,
  - controlling who can trigger `terraform apply` (e.g. only on merge to protected branches).

- **Promotion workflow**:
  - dev → QA → prod promotion logic (branch merges, auto‑merges, etc.).

### 3.3 Comparison table

| Area                         | Terraform (Infra as Code)                             | CI/CD (GitHub Actions)                                             |
|------------------------------|--------------------------------------------------------|---------------------------------------------------------------------|
| Create buckets/datasets      | Yes                                                   | No (should assume they already exist)                              |
| Configure IAM roles          | Yes                                                   | No (uses the roles Terraform granted)                              |
| Choose region / project      | Yes                                                   | Reads from Terraform outputs / config                              |
| Build Docker images          | No                                                    | Yes (builds and pushes to Artifact Registry)                       |
| Deploy Cloud Run             | Partially (service name, SA, region via outputs)     | Yes (runs `gcloud run deploy` using Terraform outputs + config)    |
| Run tests / ML pipeline      | No                                                    | Yes                                                                 |
| Enforce branch policies      | No                                                    | Yes                                                                 |
| Detect infra drift           | Yes (`terraform plan`)                                | Indirectly (by running Terraform in pipelines)                     |
| Promotion between envs       | No (by design, infra only)                           | Yes (merging branches, running deploy workflows)                   |

---

## 4. Terraform Project Structure (DataNeurus Template)

### 4.1 Typical Terraform layout in many projects

In many public examples, a Terraform project has:

- **`main.tf`**: main resources and provider configuration.
- **`variables.tf`**: input variables.
- **`outputs.tf`**: values exported for other tools (e.g. CI/CD).
- **`terraform.tfvars`**: actual values for variables (often one file per environment).
- **`backend.tf`**: where Terraform state is stored (e.g. GCS bucket).

For multiple environments, people often duplicate configs:

- `dev.tfvars`, `qa.tfvars`, `prod.tfvars`, etc.
- Sometimes even separate folders per environment with repeated `.tf` files.

This works but leads to **duplication** and **drift** between environments.

### 4.2 DataNeurus improved layout: single config for DEV / QA / PROD

Our template uses:

- **`terraform/` directory** containing Terraform code, for example:
  - `main.tf` – core resources shared across environments.
  - `config.tf` – wiring between Terraform variables and our shared YAML config.
  - `outputs.tf` – what CI/CD needs (buckets, dataset, project, region, etc.).
  - `backend.tf` – state backend (e.g. GCS).

- **`config.yaml` at repo root**:
  - Single YAML file with **all environments** under one `environments:` key.
  - For example:
    - `environments.dev` – dev project, region, retention days, Cloud Run sizing.
    - `environments.qa` – QA settings.
    - `environments.prod` – production settings.

- **No separate `dev.tfvars` / `qa.tfvars` / `prod.tfvars`**.  
  Instead, we have:

  - a single `active_env` (e.g. `"dev"`, `"qa"`, `"prod"`),
  - CI/CD sets an environment variable (e.g. `ACTIVE_ENV`) based on the Git branch,
  - Terraform and the ML pipeline both read from `config.yaml` using that environment.

### 4.3 Why this reduces duplication and improves maintainability

- **One place for environment differences**:
  - Cloud Run scaling options, retention days, project IDs, region per env are all in `config.yaml`.

- **No copy–paste `.tfvars`**:
  - You never need to keep multiple `.tfvars` files in sync.
  - If we add a new field (e.g. `timeout_seconds`), we add it once per env in `config.yaml`.

- **Shared logic, different data**:
  - Terraform logic (how to create buckets, datasets, etc.) stays identical.
  - Only values (IDs, sizes, feature flags) differ per environment.

### 4.4 How environment selection works (conceptual)

The template follows this pattern:

- **Branches map to environments**:
  - `dev` branch → `ACTIVE_ENV=dev`.
  - `qa` branch → `ACTIVE_ENV=qa`.
  - `prod` branch → `ACTIVE_ENV=prod`.

- **CI/CD sets `ACTIVE_ENV`**:
  - GitHub Actions step writes `ACTIVE_ENV=${{ github.ref_name }}` into the environment.

- **Terraform & ML code read from the same `config.yaml`**:
  - Terraform uses `ACTIVE_ENV` (or an input variable) to pick the right block inside `config.yaml`.
  - The ML pipeline also loads `config.yaml` and uses the same `active_env` to get dataset, table, and other ML settings.

Result: **one configuration file**, one Git branch per environment, synchronized infra and ML configuration.

---

## 5. Terraform Code Walkthrough (Small Example)

This section walks through a simplified but realistic Terraform example:

- configure the GCP provider,
- create:
  - one GCS bucket for data,
  - one BigQuery dataset,
  - one Artifact Registry repository,
- output values for CI/CD.

### 5.1 Provider configuration

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "dn-terraform-state"
    prefix = "mlapp/infra"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
```

- **`terraform` block**:
  - pins Terraform and provider versions.
  - configures the remote state backend (GCS in this example).

- **`provider "google"`**:
  - tells Terraform to talk to GCP using a project and region passed via variables.

### 5.2 Variables (simplified)

```hcl
variable "project_id" {
  type        = string
  description = "GCP project where infra is created"
}

variable "region" {
  type        = string
  description = "Default region for regional resources"
  default     = "asia-south1"
}

variable "environment" {
  type        = string
  description = "Environment name: dev, qa, prod"
}
```

These are typically wired to values read from `config.yaml`.

### 5.3 Creating a GCS bucket (data)

```hcl
resource "google_storage_bucket" "data" {
  name          = "mlapp-${var.environment}-data"
  location      = var.region
  force_destroy = var.environment == "dev" ? true : false

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 7
    }
  }

  labels = {
    owner       = "ml-team"
    environment = var.environment
  }
}
```

Key ideas:

- Bucket name includes the environment.
- Dev can be more aggressive (`force_destroy = true`, shorter retention).
- Labels help with billing and operations.

### 5.4 BigQuery dataset

```hcl
resource "google_bigquery_dataset" "training" {
  dataset_id  = "training_dataset_${var.environment}"
  location    = var.region
  description = "Training data for ${var.environment} environment"

  labels = {
    environment = var.environment
  }
}
```

Again, the environment is part of the dataset name.

### 5.5 Artifact Registry repository

```hcl
resource "google_artifact_registry_repository" "mlapp" {
  location      = var.region
  repository_id = "mlapp-${var.environment}"
  description   = "Docker images for mlapp (${var.environment})"
  format        = "DOCKER"
}
```

This repository is where CI/CD will push Docker images.

### 5.6 Outputs for CI/CD

```hcl
output "project_id" {
  value = var.project_id
}

output "region" {
  value = var.region
}

output "data_bucket" {
  value = google_storage_bucket.data.name
}

output "dataset_id" {
  value = google_bigquery_dataset.training.dataset_id
}

output "artifact_repo_url" {
  value = "${google_artifact_registry_repository.mlapp.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.mlapp.repository_id}"
}
```

CI/CD workflows:

- read these outputs from `terraform-output.json`,
- export them as environment variables,
- use them to run the ML pipeline and to deploy Cloud Run.

---

## 6. Terraform Workflow

Terraform is usually run in this sequence:

1. `terraform init`
2. `terraform plan`
3. `terraform apply`
4. `terraform destroy` (for teardown only, usually dev)

### 6.1 `terraform init`

**Command:**

```bash
cd terraform
terraform init
```

- **What it does:**
  - downloads required providers (e.g. `hashicorp/google`),
  - initializes the backend (e.g. GCS state bucket),
  - prepares the working directory for future commands.

You typically run this once per machine or whenever provider/backend config changes.

### 6.2 `terraform plan`

**Command:**

```bash
terraform plan -var="environment=dev"
```

or if you are using a wrapper that reads from `config.yaml`, that wrapper sets the environment automatically.

- **What it does:**
  - loads the current state (from GCS),
  - compares the desired configuration (`.tf` files) with reality,
  - shows a **diff**:
    - resources to be created (`+`),
    - resources to be changed (`~`),
    - resources to be destroyed (`-`).

You should always review the plan. In CI, the plan output is attached to pull requests.

### 6.3 `terraform apply`

**Command:**

```bash
terraform apply -var="environment=dev"
```

- **What it does:**
  - recomputes the plan (unless you pass a saved plan file),
  - asks for confirmation (unless `-auto-approve` is used),
  - calls the GCP APIs to create/update/delete resources,
  - updates the state file.

In our CI/CD pattern, `terraform apply` is only run:

- after code review,
- from a protected branch (e.g. merge to `dev`, `qa`, `prod`).

### 6.4 `terraform destroy`

**Command:**

```bash
terraform destroy -var="environment=dev"
```

- **What it does:**
  - shows a plan of which resources will be destroyed,
  - deletes them when you confirm.

This is usually only allowed for **dev** environments, not QA/prod.

### 6.5 Terraform workflow (ASCII flowchart)

```text
[Edit config.yaml / *.tf]
            |
            v
   [terraform init]  (first time or after provider/backend change)
            |
            v
       [terraform plan]
            |
            v
   [Review plan output]
        /        \
       /no        \yes
      v            v
 [Fix config]   [terraform apply]
                     |
                     v
        [Infra updated + state stored]
```

---

## 7. CI/CD Integration (GitHub Actions + Terraform)

The DataNeurus pattern is:

- use **GitHub Actions** as the CI/CD engine,
- run **Terraform** inside those workflows,
- clearly separate **plan** vs **apply** stages.

### 7.1 Typical triggers

- **On pull request to `dev` / `qa` / `prod`**:
  - run tests,
  - run `terraform plan`,
  - attach plan output to the PR for review.

- **On merge to `dev` / `qa` / `prod`**:
  - run tests again (optional but recommended),
  - run `terraform apply`,
  - build and push Docker image,
  - deploy Cloud Run using:
    - Terraform outputs (`project_id`, `region`, buckets, etc.),
    - Cloud Run sizing from `config.yaml` (`min_instances`, `max_instances`, `cpu`, etc.).

### 7.2 Why this prevents accidental infra changes

- **No direct `gcloud` in local terminals**:
  - Engineers do not manually create production resources.
  - All infra changes must go through Git + PR + CI.

- **Reviewable diffs and plans**:
  - Reviewers can see both the code diffs and the Terraform plan before merge.

- **Branch protection**:
  - Only approved PRs can be merged into `prod`.
  - Only merges to `prod` trigger `terraform apply` in that environment.

### 7.3 CI/CD workflow (ASCII flowchart)

```text
Developer pushes branch ---> [Pull Request to dev/qa/prod]
                                   |
                                   v
                       [GitHub Actions: CI job]
                           - run tests
                           - terraform plan
                                   |
                                   v
                     [PR shows tests + plan result]
                        /                    \
                       / reject               \ approve
                      v                        v
            [Fix code/config]          [Merge to dev/qa/prod]
                                               |
                                               v
                                  [GitHub Actions: CD job]
                                      - terraform apply
                                      - build & push image
                                      - deploy Cloud Run
                                               |
                                               v
                                     [Environment updated]
```

---

## 8. Maintenance & Scaling

This Terraform + CI/CD setup is designed to:

- simplify onboarding new projects,
- make new environments cheap to create,
- allow safe, incremental infra evolution over time.

### 8.1 Onboarding a new project

At a high level:

- **Step 1 – Copy the template**:
  - start from this repository structure (Terraform + `config.yaml` + CI/CD workflow).

- **Step 2 – Update `config.yaml`**:
  - set project IDs, environment names, regions,
  - adjust Cloud Run sizing, retention days, and IAM roles per env.

- **Step 3 – Run Terraform for dev**:
  - initialize Terraform,
  - run `plan` and `apply` for the `dev` environment.

- **Step 4 – Wire up CI/CD**:
  - ensure GitHub Actions is enabled for the repo,
  - configure secrets (e.g. GCP service account JSON).

Once this is done, the same pattern applies to QA and prod.

### 8.2 Creating new environments

To add a new environment (example: `staging`):

- **Add a new block** under `environments.staging` in `config.yaml`.
- **Configure Terraform / CI/CD** to treat branch `staging` as:
  - `ACTIVE_ENV=staging`.
- Run Terraform once for the new env (plan + apply).

Because all logic is shared, the cost of a new environment is mostly:

- one new block in `config.yaml`,
- one branch mapping in the CI/CD workflow.

### 8.3 Updating infrastructure safely

When we need a change (e.g. increase Cloud Run `max_instances` for prod):

- **Change** the value in `config.yaml` under `environments.prod.cloud_run.max_instances`.
- **Open a PR**:
  - CI runs tests and `terraform plan` (for prod).
  - Reviewers check that the plan is acceptable.
- **Merge the PR**:
  - prod CI/CD workflow runs `terraform apply` and then redeploys Cloud Run with updated scaling flags.

No console clicking. Every change is:

- visible in Git history,
- reviewed,
- reproducible on another project or environment.

### 8.4 How Terraform and CI/CD interact (ASCII overview)

```text
          +-------------------+
          |  config.yaml      |
          | (dev/qa/prod)     |
          +---------+---------+
                    |
      +-------------+-------------+
      |                           |
      v                           v
+------------+             +---------------+
| Terraform  |             | ML / App code |
| (main.tf)  |             | (Python, etc.)|
+-----+------+             +-------+-------+
      |                              |
      | terraform outputs            | uses config + outputs
      v                              v
  +---------------------+     +----------------------+
  | GitHub Actions      |     | GitHub Actions       |
  | (Infra pipeline)    |     | (ML/App pipeline)    |
  +---------+-----------+     +----------+-----------+
            |                            |
            v                            v
  [Create/update infra]         [Train, build, deploy]
        in GCP                         to GCP
```

Mentally, you can think of it like this:

- **Terraform** defines and maintains the “platform”: buckets, datasets, service accounts, Cloud Run service.
- **ML/App code + CI/CD** run *on top of* that platform, using the resources and configuration Terraform provides.

---

## 9. Summary

- **Terraform** gives DataNeurus a declarative, reviewable, and reproducible way to define cloud infrastructure.
- **CI/CD (GitHub Actions)** automates testing, planning, applying, building, and deploying.
- Our **single `config.yaml` + multi‑env design** keeps configuration in one place and avoids `.tfvars` duplication.
- Together, this pattern is a reusable company template that makes it easier for new teams to spin up consistent, safe ML/AI/Data environments on GCP.

