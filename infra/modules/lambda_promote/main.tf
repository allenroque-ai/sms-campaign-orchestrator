resource "aws_iam_role" "lambda" {
  name               = "sms-campaign-promote-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json

  tags = var.tags
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "inline" {
  name   = "sms-campaign-promote-inline"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "ssm:PutParameter"
        Resource = "arn:aws:ssm:*:*:parameter/sms-campaign/task-def-arn"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "inline_attach" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.inline.arn
}

resource "aws_lambda_function" "this" {
  function_name = "sms-campaign-promote"
  role          = aws_iam_role.lambda.arn
  filename      = var.zip_path
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 60

  tags = var.tags
}