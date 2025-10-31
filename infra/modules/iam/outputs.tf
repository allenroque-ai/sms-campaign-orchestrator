output "task_execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = aws_iam_role.task_exec.arn
}

output "task_role_arn" {
  description = "ECS task role ARN"
  value       = aws_iam_role.task.arn
}

output "codedeploy_role_arn" {
  description = "CodeDeploy service role ARN"
  value       = aws_iam_role.codedeploy.arn
}