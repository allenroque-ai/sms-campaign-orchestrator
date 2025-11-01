variable "region" {
  description = "AWS region"
  type        = string
}

variable "ecr_repo_url" {
  description = "ECR repository URL"
  type        = string
}

variable "ecr_repo_arn" {
  description = "ECR repository ARN"
  type        = string
}

variable "state_machine_arn" {
  description = "Step Functions state machine ARN"
  type        = string
}

variable "artifact_bucket_arn" {
  description = "S3 artifact bucket ARN"
  type        = string
}