locals {
  deployment_s3_key = "deployment.zip"
}

module "nlb_tg_to_alb" {
  source = "../../"

  alb_dns_name          = module.alb.alb_dns_name
  lambda_job_identifier = "simple"
  lambda_s3_bucket      = aws_s3_bucket.lambda_bucket.id
  lambda_s3_key         = local.deployment_s3_key
  name                  = var.test_name
  nlb_target_group_arn  = module.nlb.nlb_target_group_arn
  status_s3_bucket      = aws_s3_bucket.lambda_bucket.id

  depends_on = [
    aws_s3_bucket_object.lambda_deployment,
  ]
}

# Everything below this comment serves as supporting infrastructure that is
# used by the nlb_tg_to_alb module.

data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

locals {
  # Shared locals.
  environment                 = "test"
  trussworks_circleci_account = "313564602749"

  # ALB locals.
  container_port     = "8080"
  container_protocol = "HTTP"
  health_check_path  = "/"
  zone_name          = "infra-test.truss.coffee"

  # S3 locals.
  cors_rules         = []
  enable_analytics   = false
  enable_versioning  = false
  lambda_bucket_name = var.test_name
}

module "alb" {
  source  = "trussworks/alb-web-containers/aws"
  version = "~> 6"

  name        = var.test_name
  environment = local.environment

  alb_vpc_id                  = module.vpc.vpc_id
  alb_subnet_ids              = module.vpc.private_subnets
  alb_default_certificate_arn = module.acm_cert.acm_arn

  container_port     = local.container_port
  container_protocol = local.container_protocol
  health_check_path  = local.health_check_path

  logs_s3_bucket         = module.logs.aws_logs_bucket
  logs_s3_prefix         = "alb"
  logs_s3_prefix_enabled = true

  depends_on = [
    module.acm_cert,
    module.vpc,
  ]
}

module "acm_cert" {
  source  = "trussworks/acm-cert/aws"
  version = "~> 3"

  domain_name = "${var.test_name}.${local.zone_name}"
  environment = local.environment
  zone_name   = local.zone_name
}

module "nlb" {
  source  = "trussworks/nlb-containers/aws"
  version = "~> 4"

  name           = var.test_name
  environment    = local.environment
  logs_s3_bucket = module.logs.aws_logs_bucket
  nlb_ipv4_addrs = [
    cidrhost(module.vpc.private_subnets_cidr_blocks[0], 10),
    cidrhost(module.vpc.private_subnets_cidr_blocks[1], 10),
    cidrhost(module.vpc.private_subnets_cidr_blocks[2], 10),
  ]
  nlb_subnet_ids = module.vpc.private_subnets
  nlb_vpc_id     = module.vpc.vpc_id

  depends_on = [
    module.vpc,
  ]
}

resource "aws_s3_bucket_object" "lambda_deployment" {
  bucket                 = aws_s3_bucket.lambda_bucket.id
  key                    = local.deployment_s3_key
  source                 = "../../function/deployment.zip"
  server_side_encryption = "AES256"

  depends_on = [
    aws_s3_bucket.lambda_bucket,
  ]
}

data "aws_iam_policy_document" "bucket_policy" {
  statement {
    sid    = "allow-circleci-upload"
    effect = "Allow"
    principals {
      type = "AWS"
      identifiers = [
        data.aws_caller_identity.current.arn,
        "arn:${data.aws_partition.current.partition}:iam::${local.trussworks_circleci_account}:role/circleci",
      ]
    }
    actions = ["s3:*"]
    resources = [
      "arn:aws:s3:::${local.lambda_bucket_name}",
      "arn:aws:s3:::${local.lambda_bucket_name}/*",
    ]
  }
}

resource "aws_s3_bucket" "lambda_bucket" {
  bucket = local.lambda_bucket_name
  acl    = "private"
  policy = data.aws_iam_policy_document.bucket_policy.json
}

module "logs" {
  source            = "trussworks/logs/aws"
  version           = "~> 10"
  s3_bucket_name    = var.logs_bucket_name
  force_destroy     = true
  allow_alb         = true
  alb_logs_prefixes = ["alb"]
  allow_nlb         = true
  nlb_logs_prefixes = ["nlb/${var.test_name}-${local.environment}"]
}

module "vpc" {
  source             = "terraform-aws-modules/vpc/aws"
  version            = "~> 2"
  cidr               = "10.0.0.0/16"
  azs                = var.vpc_azs
  enable_nat_gateway = true
  private_subnets    = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  public_subnets     = ["10.0.104.0/24", "10.0.105.0/24", "10.0.106.0/24"]
}
