terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region = "ap-southeast-2"
}

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

