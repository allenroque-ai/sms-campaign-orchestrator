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
  env = "staging"
}

module "iam" {
  source          = "../../modules/iam"
  cluster_name    = "sms-campaign-${local.env}"
  artifact_bucket = var.artifact_bucket
  tags = {
    Project = "sms-campaign"
    Env     = local.env
    Owner   = "ops"
  }
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
  tags = {
    Project = "sms-campaign"
    Env     = local.env
    Owner   = "ops"
  }
}

module "ssm_parameter" {
  source                = "../../modules/ssm_parameter"
  initial_task_def_arn  = module.ecs_service.task_def_arn
  tags = {
    Project = "sms-campaign"
    Env     = local.env
    Owner   = "ops"
  }
}

module "codedeploy" {
  source                  = "../../modules/codedeploy"
  app_name                = "sms-campaign-${local.env}"
  deployment_group_name   = "sms-campaign-${local.env}-dg"
  service_role_arn        = module.iam.codedeploy_role_arn
  ecs_cluster_name        = "sms-campaign-${local.env}"
  ecs_service_name        = "sms-campaign-${local.env}"
  alb_listener_arn        = module.ecs_service.alb_listener_arn
  target_group_blue_name  = module.ecs_service.target_group_blue_name
  target_group_green_name = module.ecs_service.target_group_green_name
  tags = {
    Project = "sms-campaign"
    Env     = local.env
    Owner   = "ops"
  }
}

module "lambda_promote" {
  source   = "../../modules/lambda_promote"
  zip_path = var.lambda_zip_path
  tags = {
    Project = "sms-campaign"
    Env     = local.env
    Owner   = "ops"
  }
}