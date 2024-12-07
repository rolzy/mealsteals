# Retrieve the latest version of the secrets from AWS Secrets Manager
data "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id = var.anthropic_api_key_secret_id
}

# Decode the secrets JSON strings into local variables
locals {
  anthropic_api_key    = data.aws_secretsmanager_secret_version.anthropic_api_key.secret_string
}
