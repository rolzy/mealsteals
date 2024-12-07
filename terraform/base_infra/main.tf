resource "aws_dynamodb_table" "restaurants_table" {
  name                        = "MealSteals-Restaurant-Table"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "website"
  range_key                   = "name"
  deletion_protection_enabled = true

  attribute {
    name = "website"
    type = "S"
  }

  attribute {
    name = "name"
    type = "S"
  }
}

resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name = "anthropic_api_key"
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key_value" {
  secret_id = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.anthropic_api_key
}

resource "aws_ecr_repository" "deal_scraper" {
  name = "deal_scraper"
  force_delete = true
}
