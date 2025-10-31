variable "app_name" {
  description = "Name of the CodeDeploy application"
  type        = string
}

variable "deployment_group_name" {
  description = "Name of the CodeDeploy deployment group"
  type        = string
}

variable "service_role_arn" {
  description = "ARN of the CodeDeploy service role"
  type        = string
}

variable "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

variable "ecs_service_name" {
  description = "Name of the ECS service"
  type        = string
}

variable "alb_listener_arn" {
  description = "ARN of the ALB listener"
  type        = string
}

variable "target_group_blue_name" {
  description = "Name of the blue target group"
  type        = string
}

variable "target_group_green_name" {
  description = "Name of the green target group"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}