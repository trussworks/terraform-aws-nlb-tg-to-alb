class UnittestConstant:
    """
    Constant used for unit test
    """

    ALB_DNS_NAME = "mocked_alb.dns.name.com"
    ALB_LISTENER = "80"
    S3_BUCKET = "mocked_s3_bucket"
    NLB_TG_ARN = (
        "arn:aws:elasticloadbalancing:us-east-1:12345:targetgroup/TG-mocked/12345abcde"
    )
    MAX_LOOKUP_PER_INVOCATION = "10"
    INVOCATIONS_BEFORE_DEREGISTRATION = "3"
    CW_METRIC_FLAG_IP_COUNT = "TRUE"
    SAME_VPC = "TRUE"
    AWS_REGION = "us-east-1"
    ACTIVE_FILENAME = "active_ip.json"
    PENDING_DEREGISTRATION_FILENAME = "pending_ip.json"
    ACTIVE_IP_LIST_KEY = f"{ALB_DNS_NAME}/{ACTIVE_FILENAME}"
    PENDING_IP_LIST_KEY = f"{ALB_DNS_NAME}/{PENDING_DEREGISTRATION_FILENAME}"
    TIME = "2021-05-19 00:19:46"
