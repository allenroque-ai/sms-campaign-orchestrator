region                   = "us-east-1"
artifact_bucket          = "sms-campaign-artifacts-stg"
codestar_connection_arn  = "arn:aws:codestar-connections:us-east-1:754102187132:connection/YOUR-CONNECTION-ID"
github_repo              = "your-org/your-repo"
github_branch            = "main"
account_id               = "754102187132"

# ECS specific
cluster_name             = "sms-campaign-staging"
service_name             = "sms-campaign-staging"

# SSM specific
ssm_parameter_name       = "/sms-campaign/task-def-arn"

# VPC/Network (you'll need to provide these)
vpc_id                   = "vpc-c88adcae"
private_subnet_ids       = ["subnet-54990c58", "subnet-7ba5c647"]
security_group_ids       = ["sg-ef17c090"]

# Container
container_image          = "754102187132.dkr.ecr.us-east-1.amazonaws.com/sms-campaign:latest"