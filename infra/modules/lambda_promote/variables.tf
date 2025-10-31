variable "zip_path" {
  description = "Path to the Lambda ZIP file"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}