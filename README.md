# Truss Terraform Module template

This repository is meant to be a template repo we can just spin up new module repos from with our general format.

## Creating a new Terraform Module

1. Clone this repo, renaming appropriately.
1. Write your terraform code in the root dir.
1. Create an example of the module in use in the `examples` dir.
1. Ensure you've completed the [Developer Setup](#developer-setup).
1. In the root dir, run `go mod init MODULE_NAME` to get a new `go.mod` file. Then run `go mod tidy`. This creates a new `go.sum` file and imports the dependencies and checksums specific to your repository.
1. Run your tests to ensure they work as expected using instructions below.

## Actual readme below  - Delete above here

Please put a description of what this module does here

## Terraform Versions

_This is how we're managing the different versions._
Terraform 0.13. Pin module version to ~> 2.0. Submit pull-requests to master branch.

Terraform 0.12. Pin module version to ~> 1.0.1. Submit pull-requests to terraform012 branch.

Terraform 0.11. Pin module version to ~> 1.0. Submit pull-requests to terraform011 branch.

## Usage

### Put an example usage of the module here

```hcl
module "example" {
  source = "terraform/registry/path"

  <variables>
}
```

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
