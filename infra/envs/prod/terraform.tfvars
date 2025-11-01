region                   = "us-east-1"
artifact_bucket          = "sms-campaign-artifacts-prd"
codestar_connection_arn  = "arn:aws:codestar-connections:us-east-1:754102187132:connection/2417914c-bcef-4078-916f-c6d7ba7906d8"
github_repo              = "allenroque-ai/sms-campaign-orchestrator"
github_branch            = "main"
account_id               = "754102187132"

# ECS specific
cluster_name             = "sms-campaign-prod"
service_name             = "sms-campaign-prod"

# SSM specific
ssm_parameter_name       = "/sms-campaign/task-def-arn"

# VPC/Network (using staging VPC for now - update to prod VPC)
vpc_id                   = "vpc-c88adcae"
private_subnet_ids       = ["subnet-54990c58", "subnet-7ba5c647"]
security_group_ids       = ["sg-ef17c090"]

# Container
container_image          = "754102187132.dkr.ecr.us-east-1.amazonaws.com/sms-campaign:latest"

# Lambda
lambda_zip_path          = "../../dist/lambda_promote.zip"