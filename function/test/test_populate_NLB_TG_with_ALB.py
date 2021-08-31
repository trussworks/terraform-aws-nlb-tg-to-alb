import pytest
from mock import patch, MagicMock, call
from test.unittest_constant import UnittestConstant

mocked_aws_services = MagicMock()

mocked_active_ip_dict_from_previous_invocation = {
    "LoadBalancerName": "internal-alb-internal-12345.us-east-1.elb.amazonaws.com",
    "TimeStamp": "2021-05-17 23:31:12",
    "IPList": ["1.1.1.1", "2.2.2.2"],
    "IPCount": 2,
}

mocked_pending_ip_dict_from_previous_invocation = {"3.3.3.3": "1", "1.1.1.1": "2"}


def test_validate_environment_variable():
    from populate_NLB_TG_with_ALB import validate_environment_variable

    # Raise exception when MAX_LOOKUP_PER_INVOCATION <= 0
    with patch("populate_NLB_TG_with_ALB.LambdaEnv.MAX_LOOKUP_PER_INVOCATION", 0):
        with pytest.raises(ValueError) as e:
            expected_error_message = (
                "MAX_LOOKUP_PER_INVOCATION is required to be a positive number"
            )
            validate_environment_variable()
            assert str(e) == expected_error_message

    # Raise exception when INVOCATIONS_BEFORE_DEREGISTRATION <= 0
    with patch(
        "populate_NLB_TG_with_ALB.LambdaEnv.INVOCATIONS_BEFORE_DEREGISTRATION", 0
    ):
        with pytest.raises(ValueError) as e:
            expected_error_message = (
                "INVOCATIONS_BEFORE_DEREGISTRATION is required to be a positive number"
            )
            validate_environment_variable()
            assert str(e) == expected_error_message


@patch("populate_NLB_TG_with_ALB.sys")
@patch("populate_NLB_TG_with_ALB.get_elb_ip_from_dns")
def test_get_ip_from_dns(mocked_get_elb_ip_from_dns, mocked_sys):
    from populate_NLB_TG_with_ALB import get_ip_from_dns

    # Case 1: When there is no IP found in the DNS. Exit
    mocked_get_elb_ip_from_dns.return_value = set()
    get_ip_from_dns()
    mocked_sys.exit.assert_called_once_with(1)

    # Case 2: When there are IPs in the DNS
    mocked_get_elb_ip_from_dns.return_value = {"1.1.1.1", "2.2.2.2"}
    actual_result = get_ip_from_dns()
    expected_result = {"1.1.1.1", "2.2.2.2"}
    assert actual_result == expected_result


@patch("populate_NLB_TG_with_ALB.AwsServices")
@patch("populate_NLB_TG_with_ALB.logger", return_value=MagicMock())
def test_update_elb_ip_count_metric(mocked_logger, mocked_AwsServices):
    from populate_NLB_TG_with_ALB import update_elb_ip_count_metric

    mocked_AwsServices.return_value = mocked_aws_services
    mocked_active_ip_from_dns_meta_data = {}
    # When CW_METRIC_FLAG_IP_COUNT is set to False
    with patch("populate_NLB_TG_with_ALB.LambdaEnv.CW_METRIC_FLAG_IP_COUNT", False):
        update_elb_ip_count_metric(
            mocked_aws_services, mocked_active_ip_from_dns_meta_data
        )
        mocked_logger.info.assert_called_with(
            "CW_METRIC_FLAG_IP_COUNT is set to False. Skip publish CloudWatch metric..."
        )

    # When CW_METRIC_FLAG_IP_COUNT is set to True
    update_elb_ip_count_metric(mocked_aws_services, mocked_active_ip_from_dns_meta_data)
    mocked_logger.info.assert_called_with(
        "CW_METRIC_FLAG_IP_COUNT is set to True. Publishing ELB node IP count metric"
    )
    mocked_aws_services.publish_elb_ip_count_metric.assert_called_with(
        mocked_active_ip_from_dns_meta_data
    )


@patch("populate_NLB_TG_with_ALB.AwsServices")
@patch("populate_NLB_TG_with_ALB.logger", return_value=MagicMock())
def test_get_ip_from_previous_invocation(mocked_logger, mocked_AwsServices):
    from populate_NLB_TG_with_ALB import get_ip_from_previous_invocation

    mocked_AwsServices.return_value = mocked_aws_services
    mocked_aws_services.download_elb_ip_from_s3.side_effect = [
        mocked_active_ip_dict_from_previous_invocation,
        mocked_pending_ip_dict_from_previous_invocation,
    ]
    (
        actual_active_ip_dict_from_previous_invocation,
        actual_pending_ip_dict_from_previous_invocation,
        actual_active_ip_set_from_previous_invocation,
    ) = get_ip_from_previous_invocation(mocked_aws_services)

    assert (
        actual_active_ip_dict_from_previous_invocation
        == mocked_active_ip_dict_from_previous_invocation
    )
    assert (
        actual_pending_ip_dict_from_previous_invocation
        == mocked_pending_ip_dict_from_previous_invocation
    )
    assert actual_active_ip_set_from_previous_invocation == {"1.1.1.1", "2.2.2.2"}


@patch("populate_NLB_TG_with_ALB.AwsServices", return_value=MagicMock())
@patch("populate_NLB_TG_with_ALB.logger", return_value=MagicMock())
def test_update_target_group(mocked_logger, mocked_AwsServices):
    from populate_NLB_TG_with_ALB import update_target_group

    mocked_AwsServices.return_value = mocked_aws_services

    # When pending registration and deregistration IP sets are empty, expect is_registered is False
    pending_registration_ip_set = set()
    pending_deregistration_ip_set = set()
    expected_result = False
    actual_result = update_target_group(
        pending_registration_ip_set, pending_deregistration_ip_set, mocked_aws_services
    )
    logger_info_calls = [
        call("No pending registration IP found. Skipping ELB target registration..."),
        call(
            "No pending deregistration IP found. Skipping ELB target deregistration..."
        ),
    ]
    mocked_logger.info.assert_has_calls(logger_info_calls)
    assert actual_result == expected_result

    # When pending registration and deregistration IPs are not empty
    pending_registration_ip_set = {"1.1.1.1"}
    pending_deregistration_ip_set = {"2.2.2.2"}
    update_target_group(
        pending_registration_ip_set, pending_deregistration_ip_set, mocked_aws_services
    )
    mocked_aws_services.register_target.assert_called_with(
        UnittestConstant.NLB_TG_ARN, [{"Id": "1.1.1.1", "Port": 80}]
    )
    mocked_aws_services.deregister_target.assert_called_with(
        UnittestConstant.NLB_TG_ARN, [{"Id": "2.2.2.2", "Port": 80}]
    )
