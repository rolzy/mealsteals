data "aws_iam_policy_document" "dealscraper_lambda_role_trust_policy" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "dealscraper_lambda_role" {
  name               = "iam_for_lambda"
  assume_role_policy = data.aws_iam_policy_document.dealscraper_lambda_role_trust_policy.json
}

resource "aws_iam_role_policy_attachment" "cloudwatch_logs_policy_attach" {
  role       = aws_iam_role.dealscraper_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "dealscraper_lambda_log_group" {
  name              = "/aws/lambda/${var.dealscraper_lambda_function_name}"
  retention_in_days = 14
}

resource "aws_lambda_function" "dealscraper_lambda" {
  function_name = var.dealscraper_lambda_function_name
  role          = aws_iam_role.dealscraper_lambda_role.arn
  package_type = "Image"
  image_uri = var.dealscraper_image_uri
  memory_size=1024
  timeout = 300

  environment {
    variables = {
      ANTHROPIC_API_KEY = local.anthropic_api_key
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.cloudwatch_logs_policy_attach,
    aws_cloudwatch_log_group.dealscraper_lambda_log_group,
  ]
}
