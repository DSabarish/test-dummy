# Config generator (optional)

Reads **repo root `config.yaml`** and writes `ml_app_env.txt` (env format). No GCP resources, no state. Use when infra already exists and you only need the env export.

```bash
terraform init
terraform apply -auto-approve
```

Output: `terraform/config-generator/ml_app_env.txt`
