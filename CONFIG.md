# Configuration: single source of truth

## One file

**`config.yaml`** at the repo root is the only configuration file. Terraform and ML code both read from it. Do not add other config YAMLs or duplicate values.

## Flow

```
config.yaml (repo root)
       │
       ├── Terraform (terraform/config.tf)
       │   Reads via yamldecode(file("${path.module}/../config.yaml")).
       │   All resources use local.config.* from this.
       │
       └── ML code (ML-code/config_loader.py)
           load_config() reads root config.yaml, derives feature_columns from table_schema,
           and adds computed keys (data_bucket, artifacts_bucket, SAs, artifact_repo_url).
```

## Optional export

- **terraform apply** writes `terraform/ml_app_env.txt` (env-style) for CI/secrets.
- **terraform/config-generator**: same env export without touching GCP; run from that dir with `terraform apply -auto-approve`.

## Editing

Change only **config.yaml**. Then run `terraform plan` / `terraform apply` as needed; ML code picks up the file on next run. No tfvars; no per-environment files.
