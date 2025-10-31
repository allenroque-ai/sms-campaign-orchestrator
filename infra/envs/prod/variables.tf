variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "artifact_bucket" {
  description = "S3 bucket for artifacts"
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

variable "github_branch" {
  description = "GitHub branch"
  type        = string
  default     = "main"
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
}

variable "cluster_name" {
  description = "ECS cluster name"
  type        = string
}

variable "service_name" {
  description = "ECS service name"
  type        = string
}

variable "ssm_parameter_name" {
  description = "SSM parameter name for task definition ARN"
  type        = string
  default     = "/sms-campaign/task-def-arn"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs"
  type        = list(string)
}

variable "container_image" {
  description = "Container image URI"
  type        = string
}

variable "lambda_zip_path" {
  description = "Path to Lambda ZIP file"
  type        = string
}