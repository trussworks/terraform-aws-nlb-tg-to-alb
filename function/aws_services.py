import boto3
from common import precondition, logger
from botocore.exceptions import ClientError
import json


class AwsServices:
    """
    Provides common methods to interact with AWS services (S3, CloudWatch, ELBv2)
    """

    def __init__(self, region, bucket):
        precondition(region, "region is required")
        precondition(bucket, "bucket is required")

        self.s3 = boto3.resource("s3", region_name=region)
        self.s3_client = boto3.client("s3", region_name=region)
        self.cw = boto3.client("cloudwatch", region_name=region)
        self.elbv2 = boto3.client("elbv2", region_name=region)
        self.region = region
        self.bucket = bucket

    def publish_elb_ip_count_metric(self, ip_dict):
        """
        Add IPCount to CloudWatch metric for tracking ALB node count
        :param ip_dict: IP meta data dict e.g.
        {
            'LoadBalancerName': 'internal-alb-internal-abc1234.us-east-1.elb.amazonaws.com',
            'TimeStamp': '2021-05-17 23:31:12',
            'IPList': ['172.16.2.13', '172.16.3.220'],
            'IPCount': 2
        }
        """
        try:
            self.cw.put_metric_data(
                Namespace="AWS/ApplicationELB",
                MetricData=[
                    {
                        "MetricName": "LoadBalancerIPCount",
                        "Dimensions": [
                            {
                                "Name": "LoadBalancerName",
                                "Value": ip_dict["LoadBalancerName"],
                            },
                        ],
                        "Value": float(ip_dict["IPCount"]),
                        "Unit": "Count",
                    },
                ],
            )
        except ClientError as e:
            logger.exception(f"Failed to put data to CloudWatch metric. Error: {e}")

    def write_content_to_s3(self, content, object_key):
        """
        Adds an object to a bucket
        :param content: bytes or seekable file-like object
        :param object_key: S3 object key
        """
        try:
            s3_object = self.s3.Object(self.bucket, object_key)
            s3_object.put(Body=content, ServerSideEncryption="AES256")
            logger.debug(
                f"Successfully write content to - s3://{self.bucket}/{object_key}"
            )
        except ClientError as e:
            logger.error(
                f"Failed to write to s3://{self.bucket}/{object_key}. Error: {e}"
            )

    def download_elb_ip_from_s3(self, object_key):
        """
        Download object from S3
        :param object_key: S3 object key
        :return: Active or pending ELB node IP stored in S3
        """
        ip_from_previous_invocation = {}
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=object_key)
            logger.info(f"Get {object_key} from S3 bucket - {self.bucket}")
            logger.debug(f"Get object from S3 response - {response}")
            ip_from_previous_invocation = json.loads(response["Body"].read())
        except Exception as e:
            logger.warning(
                f"Failed to download ELB IPs collected from the previous Lambda invocation. "
                f"It is normal for the first time when the Lambda is triggered or ELB IPs remain the same. Error: {e}"
            )
        return ip_from_previous_invocation

    def register_target(self, tg_arn, new_target_list):
        """
        Register given targets to the given target group
        :param tg_arn: ARN of target group
        :param new_target_list: list of targets
        """
        logger.info(f"Register new_target_list:{new_target_list}")
        is_registered = False
        try:
            self.elbv2.register_targets(TargetGroupArn=tg_arn, Targets=new_target_list)
            is_registered = True
        except Exception as e:
            logger.exception(
                f"Failed to register target to target group. "
                f"Targets: {new_target_list}. Target group: {tg_arn}"
            )
        return is_registered

    def deregister_target(self, tg_arn, new_target_list):
        """
        Deregister given targets to the given target group
        :param tg_arn: ARN of target group
        :param new_target_list: list of targets
        """
        logger.info(f"Deregistering targets: {new_target_list}")
        try:
            self.elbv2.deregister_targets(
                TargetGroupArn=tg_arn, Targets=new_target_list
            )
        except ClientError as e:
            logger.exception(
                f"Failed to deregister target to target group. "
                f"Targets: {new_target_list}. Target group: {tg_arn}"
            )

    def get_ip_target_list_by_target_group_arn(self, tg_arn):
        """
        Get a list of IP targets that are registered with the given target group
        :param tg_arn: ARN of target group
        :return: list of target IP
        """
        registered_ip_list = []
        try:
            response = self.elbv2.describe_target_health(TargetGroupArn=tg_arn)
            for target in response["TargetHealthDescriptions"]:
                registered_ip_list.append(target["Target"]["Id"])
        except ClientError:
            logger.exception(f"Failed to get target list from target group - {tg_arn}")

        logger.info(
            f"ELB IPs that are currently registered with the target group: {registered_ip_list}. "
            f"Total IP count: {len(registered_ip_list)}"
        )
        return registered_ip_list
