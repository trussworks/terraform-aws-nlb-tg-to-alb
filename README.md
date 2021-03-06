Creates a Lambda function that will update NLB target groups to point to an
ALB's IP addresses. This is modeled after [the architecture described by
AWS](https://aws.amazon.com/blogs/networking-and-content-delivery/using-aws-lambda-to-enable-static-ip-addresses-for-application-load-balancers/).
This is useful for situations where an ALB is in use, but IP addresses must be
allowlisted. ALBs do not use static IP addresses, so this module provides a
solution to that problem.

This module creates the following resources:

* Lambda function that updates the supplied NLB's target groups to point to the
  ALB's current IPs
* CloudWatch event rule that triggers the Lambda function every minute
* CloudWatch log group
* IAM policy to allow the Lambda to update the NLB's target groups, save state
  to an S3 bucket, and log to CloudWatch

## Terraform Versions

This module supports Terraform 1.x.

## Usage

### Example

```hcl
module "example" {
  source = "trussworks/nlb-tg-to-alb/aws"

  alb_dns_name          = "name-env-1234567890.us-gov-west-1.elb.amazonaws.com"
  lambda_job_identifier = "nlb-tg-updater"
  lambda_s3_bucket      = "s3-bucket-that-stores-deployment-zip-file"
  lambda_s3_key         = "deployment.zip"
  name                  = "example"
  nlb_target_group_arn  = "arn:aws-us-gov:elasticloadbalancing:us-gov-west-1:012345678901:loadbalancer/net/nlb-name-env/abcdef0123456789"
  status_s3_bucket      = "s3-bucket-that-stores-lambda-state"
}
```

This requires that you set up a few things:

* An S3 bucket to store the Lambda ZIP file
* An S3 bucket to store the Lambda state (active and pending IP lists); this
  can be the same bucket as where the Lambda ZIP file is stored or it can be a
  separate S3 bucket
* An NLB that will redirect traffic to the ALB
* An ALB that will receive traffic from the NLB

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 0.13 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 3.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | ~> 3.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_updater"></a> [updater](#module\_updater) | trussworks/lambda/aws | 2.4.0 |

## Resources

| Name | Type |
|------|------|
| [aws_cloudwatch_event_rule.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_rule) | resource |
| [aws_cloudwatch_event_target.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_target) | resource |
| [aws_iam_policy.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy) | resource |
| [aws_iam_policy_document.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_partition.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/partition) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_alb_dns_name"></a> [alb\_dns\_name](#input\_alb\_dns\_name) | The FQDN of the ALB. | `string` | n/a | yes |
| <a name="input_alb_listener_port"></a> [alb\_listener\_port](#input\_alb\_listener\_port) | The port on which the ALB listens. | `number` | `443` | no |
| <a name="input_enable_cloudwatch_metrics"></a> [enable\_cloudwatch\_metrics](#input\_enable\_cloudwatch\_metrics) | Enable CloudWatch metrics for IP address count. | `bool` | `true` | no |
| <a name="input_invocations_before_deregistration"></a> [invocations\_before\_deregistration](#input\_invocations\_before\_deregistration) | The number of required invocations before an IP address is deregistered. | `number` | `3` | no |
| <a name="input_lambda_job_identifier"></a> [lambda\_job\_identifier](#input\_lambda\_job\_identifier) | A way to uniquely identify this Lambda function. | `string` | n/a | yes |
| <a name="input_lambda_s3_bucket"></a> [lambda\_s3\_bucket](#input\_lambda\_s3\_bucket) | Name of s3 bucket used to store the Lambda build. | `string` | n/a | yes |
| <a name="input_lambda_s3_key"></a> [lambda\_s3\_key](#input\_lambda\_s3\_key) | Name of s3 bucket used to store the Lambda build. | `string` | n/a | yes |
| <a name="input_log_retention_days"></a> [log\_retention\_days](#input\_log\_retention\_days) | Number of days to retain logs. | `number` | `30` | no |
| <a name="input_max_lookup_per_invocation"></a> [max\_lookup\_per\_invocation](#input\_max\_lookup\_per\_invocation) | The maximum number times of a DNS lookup occurs per Lambda invocation. | `number` | `50` | no |
| <a name="input_name"></a> [name](#input\_name) | Lambda function name. | `string` | n/a | yes |
| <a name="input_nlb_target_group_arn"></a> [nlb\_target\_group\_arn](#input\_nlb\_target\_group\_arn) | The ARN of the NLB's target group. | `string` | n/a | yes |
| <a name="input_status_s3_bucket"></a> [status\_s3\_bucket](#input\_status\_s3\_bucket) | The name of the S3 bucket that will store the pending and active IP information produced by the Lambda function. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Tags applied to each AWS resource. | `map(string)` | `{}` | no |

## Outputs

No outputs.
<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->

## Developer Setup

Install dependencies (macOS)

```shell
brew install pre-commit go terraform terraform-docs
pre-commit install --install-hooks
```

### Testing

[Terratest](https://github.com/gruntwork-io/terratest) is being used for
automated testing with this module. Tests in the `test` folder can be run
locally by running the following command:

```text
make test
```

Or with aws-vault:

```text
AWS_VAULT_KEYCHAIN_NAME=<NAME> aws-vault exec <PROFILE> -- make test
```
