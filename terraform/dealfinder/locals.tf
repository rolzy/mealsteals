# Retrieve the latest version of the secrets from AWS Secrets Manager
data "aws_secretsmanager_secret_version" "google_api_key" {
  secret_id = var.google_api_key_secret_id
}

# Decode the secrets JSON strings into local variables
locals {
  google_api_key = data.aws_secretsmanager_secret_version.google_api_key.secret_string
}
