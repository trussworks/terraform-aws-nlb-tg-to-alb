data "aws_partition" "current" {}

locals {
  function_name_base = var.name
  job_identifier     = var.lambda_job_identifier
  full_function_name = "${local.function_name_base}-${local.job_identifier}"

  # These filenames are hardcoded in constant.py in the Lambda function.
  active_ip_key_filename  = "active_ip.json"
  pending_ip_key_filename = "pending_ip.json"

  # These keys are the default values in constant.py in the Lambda function.
  active_ip_key_full  = "${var.alb_dns_name}/${local.active_ip_key_filename}"
  pending_ip_key_full = "${var.alb_dns_name}/${local.pending_ip_key_filename}"
}

resource "aws_cloudwatch_event_rule" "main" {
  name                = "${local.full_function_name}-trigger"
  description         = "Trigger the ${local.full_function_name} Lambda function every minute."
  schedule_expression = "rate(1 minute)"
  is_enabled          = true
  tags                = var.tags
}

resource "aws_cloudwatch_event_target" "main" {
  target_id = local.full_function_name
  rule      = aws_cloudwatch_event_rule.main.name
  arn       = module.updater.lambda_arn
}

module "updater" {
  source                 = "trussworks/lambda/aws"
  version                = "2.4.0"
  name                   = local.function_name_base
  handler                = "populate_NLB_TG_with_ALB.lambda_handler"
  job_identifier         = local.job_identifier
  runtime                = "python3.8"
  timeout                = 500
  role_policy_arns_count = 1
  role_policy_arns       = [aws_iam_policy.main.arn]

  s3_bucket = var.lambda_s3_bucket
  s3_key    = var.lambda_s3_key

  cloudwatch_logs_retention_days = var.log_retention_days

  source_types = ["events"]
  source_arns  = [aws_cloudwatch_event_rule.main.arn]

  env_vars = {
    ALB_DNS_NAME                      = var.alb_dns_name
    ALB_LISTENER                      = var.alb_listener_port
    S3_BUCKET                         = var.status_s3_bucket
    NLB_TG_ARN                        = var.nlb_target_group_arn
    MAX_LOOKUP_PER_INVOCATION         = var.max_lookup_per_invocation
    INVOCATIONS_BEFORE_DEREGISTRATION = var.invocations_before_deregistration
    CW_METRIC_FLAG_IP_COUNT           = var.enable_cloudwatch_metrics
  }

  tags = var.tags
}

data "aws_iam_policy_document" "main" {
  # Allow uploading and downloading of IP lists, which act as state for the Lambda function.
  statement {
    effect = "Allow"
    resources = [
      "arn:${data.aws_partition.current.partition}:s3:::${var.status_s3_bucket}/${local.active_ip_key_full}",
      "arn:${data.aws_partition.current.partition}:s3:::${var.status_s3_bucket}/${local.pending_ip_key_full}",
    ]
    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]
  }

  # Allow the Lambda function to get information about target health.
  statement {
    effect = "Allow"
    # From the AWS console: "This action does not support resource-level
    # permissions. This requires a wildcard (*) for the resource."
    resources = ["*"]
    actions = [
      "elasticloadbalancing:DescribeTargetHealth",
    ]
  }

  # Allow configuring the NLB target groups to point to the ALB IPs.
  statement {
    effect    = "Allow"
    resources = [var.nlb_target_group_arn]
    actions = [
      "elasticloadbalancing:RegisterTargets",
      "elasticloadbalancing:DeregisterTargets",
    ]
  }

  # Allow saving metric data, which is useful for tracking the number of IPs
  # associated targeted by the NLB.
  statement {
    effect    = "Allow"
    resources = ["*"]
    actions   = ["cloudwatch:putMetricData"]
  }
}

resource "aws_iam_policy" "main" {
  name        = "${local.full_function_name}-updater"
  description = "Allow the ${local.full_function_name} Lambda function to update NLB target groups and save state to S3."
  policy      = data.aws_iam_policy_document.main.json
  tags        = var.tags
}
