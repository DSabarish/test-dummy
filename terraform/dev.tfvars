# terraform\dev.tfvars

project_id  = "sabs-dev-100"
region      = "asia-south1"
environment = "dev"
prefix      = "mlapp"

labels = {
  owner       = "ml-team"
  environment = "dev"
}

dataset_id       = "training_dataset_dev"
table_id         = "features_table"
dataset_location = "asia-south1"

dataset_delete_on_destroy = true
bucket_force_destroy      = true

artifacts_retention_days = 7
data_retention_days      = 3

table_schema = [
  { name = "feature_1", type = "FLOAT", mode = "NULLABLE" },
  { name = "feature_2", type = "FLOAT", mode = "NULLABLE" },
  { name = "feature_3", type = "FLOAT", mode = "NULLABLE" },
  { name = "feature_4", type = "FLOAT", mode = "NULLABLE" },
  { name = "feature_5", type = "FLOAT", mode = "NULLABLE" }
]