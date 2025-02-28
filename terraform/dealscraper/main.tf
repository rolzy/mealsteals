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

data "aws_iam_policy_document" "dealscraper_lambda_role_policy" {
  statement {
    effect = "Allow"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      aws_sqs_queue.dealscraper_queue.arn,
      aws_sqs_queue.dealscraper_deadletter_queue.arn,
      aws_cloudwatch_log_group.dealscraper_lambda_log_group.arn,
    ]
  }
}

resource "aws_iam_policy" "dealscraper_lambda_role_policy" {
  name        = "${var.resource_prefix}-lambda-role-policy"
  description = "Policy for the dealscraper lambda role"
  policy      = data.aws_iam_policy_document.dealscraper_lambda_role_policy.json
}

resource "aws_iam_role" "dealscraper_lambda_role" {
  name               = "${var.resource_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.dealscraper_lambda_role_trust_policy.json
}

resource "aws_iam_role_policy_attachment" "role_policy_attach" {
  role       = aws_iam_role.dealscraper_lambda_role.name
  policy_arn = aws_iam_policy.dealscraper_lambda_role_policy.arn
}

resource "aws_cloudwatch_log_group" "dealscraper_lambda_log_group" {
  name              = "/aws/lambda/${var.resource_prefix}-lambda-logs"
  retention_in_days = 14
}

resource "aws_lambda_function" "dealscraper_lambda" {
  function_name = var.resource_prefix
  description   = "MealSteals DealScraper Lambda function"
  role          = aws_iam_role.dealscraper_lambda_role.arn
  package_type  = "Image"
  image_uri     = var.dealscraper_image_uri
  memory_size   = 1024
  timeout       = 300

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

resource "aws_sqs_queue" "dealscraper_queue" {
  name                       = "${var.resource_prefix}-queue"
  message_retention_seconds  = 86400
  visibility_timeout_seconds = 300
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dealscraper_deadletter_queue.arn
    maxReceiveCount     = 4
  })
}

resource "aws_sqs_queue" "dealscraper_deadletter_queue" {
  name = "${var.resource_prefix}-deadletter-queue"
}

resource "aws_sqs_queue_redrive_allow_policy" "terraform_queue_redrive_allow_policy" {
  queue_url = aws_sqs_queue.dealscraper_deadletter_queue.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.dealscraper_queue.arn]
  })
}

resource "aws_lambda_event_source_mapping" "dealscraper_event_source_mapping" {
  event_source_arn = aws_sqs_queue.dealscraper_queue.arn
  enabled          = true
  function_name    = aws_lambda_function.dealscraper_lambda.arn
  batch_size       = 1
}
