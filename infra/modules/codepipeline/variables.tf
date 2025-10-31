variable "artifact_bucket" {
  description = "S3 bucket for CodePipeline artifacts"
  type        = string
}

variable "artifact_bucket_arn" {
  description = "S3 bucket ARN for CodePipeline artifacts"
  type        = string
}

variable "codestar_connection_arn" {
  description = "CodeStar connection ARN for GitHub"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository (owner/repo)"
  type        = string
}

variable "ecs_cluster_name" {
  description = "ECS cluster name"
  type        = string
}

variable "ecs_service_name" {
  description = "ECS service name"
  type        = string
}

variable "alb_listener_arn" {
  description = "ALB listener ARN"
  type        = string
}

variable "target_group_names" {
  description = "Target group names for blue/green"
  type        = list(string)
}

variable "build_project_name" {
  description = "CodeBuild build project name"
  type        = string
}

variable "integration_test_project_name" {
  description = "CodeBuild integration test project name"
  type        = string
}

variable "promote_function_name" {
  description = "Lambda promote function name"
  type        = string
}

variable "promote_function_arn" {
  description = "Lambda promote function ARN"
  type        = string
}