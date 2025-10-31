resource "aws_ssm_parameter" "task_def_arn" {
  name     = "/sms-campaign/task-def-arn"
  type     = "String"
  value    = var.initial_task_def_arn
  overwrite = true

  tags = var.tags

  lifecycle {
    ignore_changes = [value]  # Will be updated by Lambda
  }
}

# Additional parameters can be added here as needed