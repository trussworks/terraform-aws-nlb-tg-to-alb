package test

import (
	"fmt"
	"strings"
	"testing"

	"github.com/gruntwork-io/terratest/modules/aws"
	"github.com/gruntwork-io/terratest/modules/random"
	"github.com/gruntwork-io/terratest/modules/terraform"
)

func TestTerraformSimple(t *testing.T) {
	t.Parallel()

	awsRegion := "us-west-2"
	logsBucketName := fmt.Sprintf("terratest-aws-logs-%s", strings.ToLower(random.UniqueId()))
	environment := "test"
	testName := fmt.Sprintf("test-%s", strings.ToLower(random.UniqueId()))
	vpcAzs := aws.GetAvailabilityZones(t, awsRegion)[:3]

	terraformOptions := &terraform.Options{
		TerraformDir: "../examples/simple/",
		Vars: map[string]interface{}{
			"environment":      environment,
			"logs_bucket_name": logsBucketName,
			"test_name":        testName,
			"vpc_azs":          vpcAzs,
		},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	}

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)
}
