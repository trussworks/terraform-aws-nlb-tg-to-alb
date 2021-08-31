# conftest.py
import pytest
from test.unittest_constant import UnittestConstant


@pytest.fixture()
def env_setup(monkeypatch):
    """
    Set up environment variables
    :param monkeypatch:
    """
    monkeypatch.setenv("ALB_DNS_NAME", UnittestConstant.ALB_DNS_NAME)
    monkeypatch.setenv("ALB_LISTENER", UnittestConstant.ALB_LISTENER)
    monkeypatch.setenv("S3_BUCKET", UnittestConstant.S3_BUCKET)
    monkeypatch.setenv("NLB_TG_ARN", UnittestConstant.NLB_TG_ARN)
    monkeypatch.setenv(
        "MAX_LOOKUP_PER_INVOCATION", UnittestConstant.MAX_LOOKUP_PER_INVOCATION
    )
    monkeypatch.setenv(
        "INVOCATIONS_BEFORE_DEREGISTRATION",
        UnittestConstant.INVOCATIONS_BEFORE_DEREGISTRATION,
    )
    monkeypatch.setenv(
        "CW_METRIC_FLAG_IP_COUNT", UnittestConstant.CW_METRIC_FLAG_IP_COUNT
    )
    monkeypatch.setenv("SAME_VPC", UnittestConstant.SAME_VPC)
    monkeypatch.setenv("AWS_REGION", UnittestConstant.AWS_REGION)
