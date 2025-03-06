data "aws_iam_policy_document" "dealfinder_lambda_role_trust_policy" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "dealfinder_lambda_role_policy" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "${aws_cloudwatch_log_group.dealfinder_lambda_log_group.arn}:*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = [
      var.google_api_key_secret_arn,
    ]
  }
}

resource "aws_iam_policy" "dealfinder_lambda_role_policy" {
  name        = "${var.resource_prefix}-lambda-role-policy"
  description = "Policy for the dealfinder lambda role"
  policy      = data.aws_iam_policy_document.dealfinder_lambda_role_policy.json
}

resource "aws_iam_role" "dealfinder_lambda_role" {
  name               = "${var.resource_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.dealfinder_lambda_role_trust_policy.json
}

resource "aws_iam_role_policy_attachment" "role_policy_attach" {
  role       = aws_iam_role.dealfinder_lambda_role.name
  policy_arn = aws_iam_policy.dealfinder_lambda_role_policy.arn
}

resource "aws_cloudwatch_log_group" "dealfinder_lambda_log_group" {
  name              = "/aws/lambda/${var.resource_prefix}"
  retention_in_days = 14
}

resource "aws_lambda_function" "dealfinder_lambda" {
  function_name = var.resource_prefix
  description   = "MealSteals DealFinder Lambda function"
  role          = aws_iam_role.dealfinder_lambda_role.arn
  package_type  = "Image"
  image_uri     = var.dealfinder_image_uri
  memory_size   = 256
  timeout       = 30

  environment {
    variables = {
      GOOGLE_API_KEY_SECRET_ARN = var.google_api_key_secret_arn
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.role_policy_attach,
    aws_cloudwatch_log_group.dealfinder_lambda_log_group,
  ]
}
