variable "cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

variable "artifact_bucket" {
  description = "S3 bucket for artifacts"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}