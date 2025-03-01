variable "dealfinder_image_uri" {
  description = "Image URI for the dealfinder docker image"
  type        = string
}

variable "google_api_key_secret_arn" {
  description = "Secret ARN for the Google API key"
  type        = string
}

variable "resource_prefix" {
  description = "Lambda function name for the dealfinder function"
  type        = string
  default     = "mealsteals-dealfinder"
}
