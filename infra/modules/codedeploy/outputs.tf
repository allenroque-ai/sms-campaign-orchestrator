output "app_name" {
  description = "Name of the CodeDeploy application"
  value       = aws_codedeploy_app.this.name
}

output "deployment_group_name" {
  description = "Name of the CodeDeploy deployment group"
  value       = aws_codedeploy_deployment_group.this.deployment_group_name
}