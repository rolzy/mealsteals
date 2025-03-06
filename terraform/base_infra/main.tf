resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name = "anthropic_api_key"
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key_value" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.anthropic_api_key
}

resource "aws_secretsmanager_secret" "google_api_key" {
  name = "google_api_key"
}

resource "aws_secretsmanager_secret_version" "google_api_key_value" {
  secret_id     = aws_secretsmanager_secret.google_api_key.id
  secret_string = var.google_api_key
}

resource "aws_ecr_repository" "mealsteals_dealscraper_repo" {
  name         = "mealsteals-dealscraper"
  force_delete = true
}

resource "aws_ecr_repository" "mealsteals_dealfinder_repo" {
  name         = "mealsteals-dealfinder"
  force_delete = true
}
