import os
from datetime import datetime


class LambdaEnv:
    """
    Constant extracted from Lambda environment variables
    """

    ALB_DNS_NAME = os.environ["ALB_DNS_NAME"]
    ALB_LISTENER = int(os.environ["ALB_LISTENER"])
    S3_BUCKET = os.environ["S3_BUCKET"]
    NLB_TG_ARN = os.environ["NLB_TG_ARN"]
    MAX_LOOKUP_PER_INVOCATION = int(os.environ["MAX_LOOKUP_PER_INVOCATION"])
    INVOCATIONS_BEFORE_DEREGISTRATION = int(
        os.environ["INVOCATIONS_BEFORE_DEREGISTRATION"]
    )
    CW_METRIC_FLAG_IP_COUNT = (
        True if os.environ["CW_METRIC_FLAG_IP_COUNT"].lower() == "true" else False
    )
    SAME_VPC = True if os.getenv('SAME_VPC', "true").lower() == "true" else False
    REGION = os.environ["AWS_REGION"]
    ACTIVE_FILENAME = "active_ip.json"
    PENDING_DEREGISTRATION_FILENAME = "pending_ip.json"
    ACTIVE_IP_LIST_KEY = f"{ALB_DNS_NAME}/{ACTIVE_FILENAME}"
    PENDING_IP_LIST_KEY = f"{ALB_DNS_NAME}/{PENDING_DEREGISTRATION_FILENAME}"
    TIME = datetime.strftime((datetime.utcnow()), "%Y-%m-%d %H:%M:%S")
