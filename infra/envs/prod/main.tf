terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

locals {
  env = "prod"
}

module "iam" {
  source          = "../../modules/iam"
  cluster_name    = "sms-campaign-${local.env}"
  artifact_bucket = var.artifact_bucket
}

module "ecs_service" {
  source              = "../../modules/ecs_service"
  cluster_name        = "sms-campaign-${local.env}"
  vpc_id              = var.vpc_id
  private_subnet_ids  = var.private_subnet_ids
  security_group_ids  = var.security_group_ids
  task_exec_role_arn  = module.iam.task_execution_role_arn
  task_role_arn       = module.iam.task_role_arn
  container_image     = var.container_image
}

module "ssm_parameter" {
  source                = "../../modules/ssm_parameter"
  initial_task_def_arn  = module.ecs_service.task_def_arn
}

module "lambda_promote" {
  source           = "../../modules/lambda_promote"
  zip_path         = var.lambda_zip_path
  ecs_cluster_name = "sms-campaign-${local.env}"
  ecs_service_name = "sms-campaign-${local.env}"
}

# CodePipeline for production
module "codepipeline" {
  source                  = "../../modules/codepipeline"
  artifact_bucket         = var.artifact_bucket
  artifact_bucket_arn     = "arn:aws:s3:::${var.artifact_bucket}"
  codestar_connection_arn = var.codestar_connection_arn
  github_repo             = var.github_repo
  ecs_cluster_name        = "sms-campaign-${local.env}"
  ecs_service_name        = "sms-campaign-${local.env}"
  alb_listener_arn        = module.ecs_service.alb_listener_arn
  target_group_names      = [module.ecs_service.target_group_blue_name, module.ecs_service.target_group_green_name]
  build_project_name      = module.codebuild.build_project_name
  integration_test_project_name = module.codebuild.integration_test_project_name
  promote_function_name   = module.lambda_promote.function_name
  promote_function_arn    = module.lambda_promote.function_arn
  task_execution_role_arn = module.iam.task_execution_role_arn
  task_role_arn           = module.iam.task_role_arn
}

module "codebuild" {
  source               = "../../modules/codebuild"
  region               = var.region
  ecr_repo_url         = "${var.account_id}.dkr.ecr.${var.region}.amazonaws.com/sms-campaign"
  ecr_repo_arn         = "arn:aws:ecr:${var.region}:${var.account_id}:repository/sms-campaign"
  state_machine_arn    = "arn:aws:states:${var.region}:${var.account_id}:stateMachine:sms-campaign-orchestrator"
  artifact_bucket_arn  = "arn:aws:s3:::${var.artifact_bucket}"
}