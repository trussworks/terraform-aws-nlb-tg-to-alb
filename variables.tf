variable "alb_dns_name" {
  type        = string
  description = "The FQDN of the ALB."
}

variable "alb_listener_port" {
  type        = number
  description = "The port on which the ALB listens."
  default     = 443
}

variable "enable_cloudwatch_metrics" {
  type        = bool
  description = "Enable CloudWatch metrics for IP address count."
  default     = true
}

variable "invocations_before_deregistration" {
  type        = number
  description = "The number of required invocations before an IP address is deregistered."
  default     = 3
}

variable "lambda_job_identifier" {
  type        = string
  description = "A way to uniquely identify this Lambda function."
}

variable "lambda_s3_bucket" {
  type        = string
  description = "Name of s3 bucket used to store the Lambda build."
}

variable "lambda_s3_key" {
  type        = string
  description = "Name of s3 bucket used to store the Lambda build."
}

variable "log_retention_days" {
  description = "Number of days to retain logs."
  type        = number
  default     = 30
}

variable "max_lookup_per_invocation" {
  type        = number
  description = "The maximum number times of a DNS lookup occurs per Lambda invocation."
  default     = 50
}

variable "name" {
  type        = string
  description = "Lambda function name."
}

variable "nlb_target_group_arn" {
  type        = string
  description = "The ARN of the NLB's target group."
}

variable "status_s3_bucket" {
  type        = string
  description = "The name of the S3 bucket that will store the pending and active IP information produced by the Lambda function."
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to each AWS resource."
  default     = {}
}
