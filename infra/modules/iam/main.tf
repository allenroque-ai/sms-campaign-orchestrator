resource "aws_iam_role" "task_exec" {
  name               = "${var.cluster_name}-task-exec"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json

  tags = var.tags
}

data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "task_exec_logs" {
  role       = aws_iam_role.task_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name               = "${var.cluster_name}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json

  tags = var.tags
}

resource "aws_iam_policy" "task_inline" {
  name   = "${var.cluster_name}-task-inline"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:*:*:secret:sms-campaign/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:AbortMultipartUpload",
          "s3:CreateMultipartUpload",
          "s3:UploadPart",
          "s3:CompleteMultipartUpload"
        ]
        Resource = "arn:aws:s3:::${var.artifact_bucket}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "task_attach" {
  role       = aws_iam_role.task.name
  policy_arn = aws_iam_policy.task_inline.arn
}

# CodeDeploy role for blue/green deployments
resource "aws_iam_role" "codedeploy" {
  name               = "${var.cluster_name}-codedeploy"
  assume_role_policy = data.aws_iam_policy_document.codedeploy_assume_role.json

  tags = var.tags
}

data "aws_iam_policy_document" "codedeploy_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["codedeploy.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "codedeploy" {
  role       = aws_iam_role.codedeploy.name
  policy_arn = "arn:aws:iam::aws:policy/AWSCodeDeployRoleForECS"
}