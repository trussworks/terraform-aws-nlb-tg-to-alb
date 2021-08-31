import json
from constant import LambdaEnv
import sys
from aws_services import AwsServices
from common import (
    logger,
    precondition,
    get_elb_ip_from_dns,
    get_pending_registration_ip_set,
    get_invocation_count_per_pending_deregistration_ip,
    get_pending_deregistration_ip_set,
    get_elb_ip_target_from_ip_list,
)

"""
This function checks the DNS records for an internal Application Load Balancer IP addresses.
It populates a Network Load Balancer's target group with Application Load Balancer's IP addresses

WARNING: This function perform multiple DNS looks per each invocation. It is not guaranteed that all
Application Load Balancer IP will be detected by a single invocation. However, the result converges
when more invocations are triggered. This function perform registration aggressively
and deregistration cautiously.

Configure these environment variables in your Lambda environment (CloudFormation Inputs)
1. ALB_DNS_NAME - The full DNS name of the internal Application Load Balancer
2. ALB_LISTENER - The traffic listener port of the internal Application Load Balancer
3. S3_BUCKET - Bucket to track changes between Lambda invocations
4. NLB_TG_ARN - The ARN of the Network Load Balancer's target group
5. MAX_LOOKUP_PER_INVOCATION - The max times of DNS look per invocation
6. INVOCATIONS_BEFORE_DEREGISTRATION  - Then number of required Invocations before a IP is deregistered
7. CW_METRIC_FLAG_IP_COUNT - The controller flag that enables CloudWatch metric of IP count
"""


def validate_environment_variable():
    """
    # Validating the environment variables
    """
    error_message = "MAX_LOOKUP_PER_INVOCATION is required to be a positive number"
    precondition(LambdaEnv.MAX_LOOKUP_PER_INVOCATION > 0, error_message)

    error_message = (
        "INVOCATIONS_BEFORE_DEREGISTRATION is required to be a positive number"
    )
    precondition(LambdaEnv.INVOCATIONS_BEFORE_DEREGISTRATION > 0, error_message)


def get_ip_from_dns():
    """
    Get ALB node IP address through DNS lookup. Exit if no IP found in the DNS
    :return: a set of ELB node IP addresses
    """
    ip_from_dns_set = get_elb_ip_from_dns(
        LambdaEnv.ALB_DNS_NAME, "A", LambdaEnv.MAX_LOOKUP_PER_INVOCATION
    )
    logger.info(
        f"ELB IPs from DNS lookup: {ip_from_dns_set}. Total IP count: {len(ip_from_dns_set)}"
    )

    # Check if there is ALB no IP in the DNS. If so, exit from the current Lambda invocation
    try:
        error_message = (
            f"No IP found from DNS for ALB - {LambdaEnv.ALB_DNS_NAME}. "
            f"The Lambda function will not proceed with making changes to the NLB target group - {LambdaEnv.NLB_TG_ARN}"
        )
        precondition(ip_from_dns_set, error_message)
        return ip_from_dns_set
    except ValueError:
        sys.exit(1)


def update_elb_ip_count_metric(aws_service, active_ip_from_dns_meta_data):
    """
    Publish ELB IP node count CloudWatch Metric
    :param aws_service: aws service object
    :param active_ip_from_dns_meta_data: meta data of active IPs that are currently in DNS
    :return:
    """
    if not LambdaEnv.CW_METRIC_FLAG_IP_COUNT:
        logger.info(
            "CW_METRIC_FLAG_IP_COUNT is set to False. Skip publish CloudWatch metric..."
        )
        return
    logger.info(
        "CW_METRIC_FLAG_IP_COUNT is set to True. Publishing ELB node IP count metric"
    )
    aws_service.publish_elb_ip_count_metric(active_ip_from_dns_meta_data)


def get_ip_from_previous_invocation(aws_service):
    """
    Get active and pending IP from S3. The IPs were collected from the previous invocation
    :param aws_service: aws service object
    :return:
    """
    active_ip_dict_from_previous_invocation = aws_service.download_elb_ip_from_s3(
        LambdaEnv.ACTIVE_IP_LIST_KEY
    )
    pending_ip_dict_from_previous_invocation = aws_service.download_elb_ip_from_s3(
        LambdaEnv.PENDING_IP_LIST_KEY
    )
    logger.info(
        f"Active IPs from previous invocation: {active_ip_dict_from_previous_invocation}"
    )
    logger.info(
        f"Pending IPs from previous invocation: {pending_ip_dict_from_previous_invocation}"
    )
    active_ip_set_from_previous_invocation = set(
        active_ip_dict_from_previous_invocation.get("IPList", [])
    )
    return (
        active_ip_dict_from_previous_invocation,
        pending_ip_dict_from_previous_invocation,
        active_ip_set_from_previous_invocation,
    )


def update_target_group(
        pending_registration_ip_set, pending_deregistration_ip_set, aws_service
):
    """
    Update target group by registering new active IPs and deregistering pending IPs whose invocation count
    is higher than INVOCATIONS_BEFORE_DEREGISTRATION
    :param pending_registration_ip_set: a set of IPs that are pending registration
    :param pending_deregistration_ip_set: a set of IPs that are pending deregistration
    :param aws_service: aws_service object
    :return: a boolean value indicating whether registration API actually succeeded (default: False)
    """
    is_registered = False
    if pending_registration_ip_set:
        pending_registration_ip_target_list = get_elb_ip_target_from_ip_list(
            list(pending_registration_ip_set), LambdaEnv.ALB_LISTENER
        )
        is_registered = aws_service.register_target(
            LambdaEnv.NLB_TG_ARN, pending_registration_ip_target_list
        )

    if not pending_registration_ip_set:
        logger.info(
            "No pending registration IP found. Skipping ELB target registration..."
        )

    # Deregister target
    if pending_deregistration_ip_set:
        pending_deregistration_ip_target_list = get_elb_ip_target_from_ip_list(
            list(pending_deregistration_ip_set), LambdaEnv.ALB_LISTENER
        )
        aws_service.deregister_target(
            LambdaEnv.NLB_TG_ARN, pending_deregistration_ip_target_list
        )

    if not pending_deregistration_ip_set:
        logger.info(
            "No pending deregistration IP found. Skipping ELB target deregistration..."
        )
    return is_registered


def lambda_handler(event, context):
    """
    Main Lambda handler
    This is invoked when Lambda is called
    """

    # Initialize AWS service clients
    aws_service = AwsServices(region=LambdaEnv.REGION, bucket=LambdaEnv.S3_BUCKET)

    # Validate environment variables
    validate_environment_variable()

    # ---- Step 1 -----
    # Get IP from DNS
    logger.info("\n>>>>Step-1: Get IPs from DNS<<<<")
    ip_from_dns_set = get_ip_from_dns()

    # ---- Step 2 -----
    # Get IP that are currently registered with the NLB target group and update CloudWatch metric
    logger.info("\n>>>>Step-2: Get IPs from target group<<<<")
    ip_from_target_group_set = set(
        aws_service.get_ip_target_list_by_target_group_arn(LambdaEnv.NLB_TG_ARN)
    )
    logger.info(
        f"ELB IPs from target group ({LambdaEnv.NLB_TG_ARN}): {ip_from_target_group_set}. "
        f"Total IP count: {len(ip_from_target_group_set)}"
    )

    active_ip_from_dns_meta_data = {
        "LoadBalancerName": LambdaEnv.ALB_DNS_NAME,
        "TimeStamp": LambdaEnv.TIME,
        "IPList": list(ip_from_dns_set),
        "IPCount": len(ip_from_dns_set),
    }
    logger.debug(
        f"Meta data of active IPs in DNS from the current invocation: {active_ip_from_dns_meta_data}"
    )

    # Update ELB IP count metric if CW_METRIC_FLAG_IP_COUNT is set to True
    update_elb_ip_count_metric(aws_service, active_ip_from_dns_meta_data)

    # ---- Step 3 -----
    # Get the active and pending ALB IPs that were collected from the previous invocation
    logger.info(
        "\n>>>>Step-3: Get active and pending IPs from S3 (previous invocation)<<<<"
    )
    (
        active_ip_dict_from_previous_invocation,
        pending_ip_dict_from_previous_invocation,
        active_ip_set_from_previous_invocation,
    ) = get_ip_from_previous_invocation(aws_service)

    # ---- Step 4 -----
    # Get IPs that are pending for registration
    logger.info("\n>>>>Step-4: Get IPs that are pending for registration<<<<")
    pending_registration_ip_set = get_pending_registration_ip_set(
        ip_from_dns_set,
        ip_from_target_group_set
    )
    logger.info(
        f"Pending registration IPs for the current invocation - {pending_registration_ip_set}"
    )

    # ---- Step 5 -----
    # Get IPs that are pending for deregistration and their invocation count
    logger.info("\n>>>>Step-5: Get IPs that are pending for deregistration and their invocation count<<<<")
    invocation_count_per_pending_deregistration_ip = get_invocation_count_per_pending_deregistration_ip(
        ip_from_dns_set,
        ip_from_target_group_set,
        active_ip_set_from_previous_invocation,
        pending_ip_dict_from_previous_invocation,
    )
    pending_deregistration_ip_set = get_pending_deregistration_ip_set(
        invocation_count_per_pending_deregistration_ip,
        LambdaEnv.INVOCATIONS_BEFORE_DEREGISTRATION,
    )

    # ---- Step 6 -----
    # Update IP targets in the NLB target group (registration and deregistration)
    logger.info("\n>>>>Step-6: Update IP targets in the NLB target group (registration and deregistration)<<<<")
    logger.info(f"SAME VPC is set to: {LambdaEnv.SAME_VPC}")
    is_registered = update_target_group(
        pending_registration_ip_set, pending_deregistration_ip_set, aws_service
    )

    # ---- Step 7 -----
    # Upload the active and pending IP from the current invocation to S3
    logger.info("\n>>>>Step-7: Upload the active and pending IP from the current invocation to S3<<<<")
    # Only upload the current active IP to S3 when registration API succeeded
    # The next invocation will skip the IPs that have already been registered
    if is_registered:
        logger.info(f"Upload active IP to S3: {active_ip_from_dns_meta_data}")
        aws_service.write_content_to_s3(
            json.dumps(active_ip_from_dns_meta_data), LambdaEnv.ACTIVE_IP_LIST_KEY
        )
    else:
        logger.info(f"No IPs were registered. Skip uploading active IP to S3: {active_ip_from_dns_meta_data}")

    logger.info(
        f"Upload pending deregistration IP to S3: {invocation_count_per_pending_deregistration_ip}"
    )
    aws_service.write_content_to_s3(
        json.dumps(invocation_count_per_pending_deregistration_ip),
        LambdaEnv.PENDING_IP_LIST_KEY,
    )
