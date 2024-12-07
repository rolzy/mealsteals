variable "dealscraper_image_uri" {
  description = "Image URI for the DealScraper docker image"
  type = string
}

variable "anthropic_api_key_secret_id" {
  description = "Secret ID for the Anthropic API key"
  type = string
}

variable "dealscraper_lambda_function_name" {
  description = "Lambda function name for the dealscraper function"
  type = string
  default = "dealscraper"
}
