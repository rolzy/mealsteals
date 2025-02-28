variable "dealscraper_image_uri" {
  description = "Image URI for the DealScraper docker image"
  type        = string
}

variable "anthropic_api_key_secret_id" {
  description = "Secret ID for the Anthropic API key"
  type        = string
}

variable "resource_prefix" {
  description = "Resource prefix for the dealscraper module"
  type        = string
  default     = "mealsteals-dealscraper"
}
