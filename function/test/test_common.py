import pytest
from mock import patch, MagicMock, call

MOCKED_DNS_NAME = "mocked.domain.name.com"
MOCKED_DNS_RECORD_TYPE = "A"
MOCKED_DNS_SERVERS = ["1.1.1.1", "2.2.2.2"]


@patch("common.logger", return_value=MagicMock())
def test_precondition(mocked_logger, env_setup):
    import common as common_util

    # Case 1: When pre-condition is True. No exception should be raised
    pre_condition = True
    mocked_error_messages = "mocked_error_messages"
    common_util.precondition(pre_condition, mocked_error_messages)
    mocked_logger.error.assert_not_called()

    # Case 2: When pre-condition is False. exception is raised
    pre_condition = False
    with pytest.raises(ValueError):
        common_util.precondition(pre_condition, mocked_error_messages)
        mocked_logger.error.assert_called_once_with(mocked_error_messages)


@patch("common.dns.resolver", return_value=MagicMock())
@patch("common.logger", return_value=MagicMock())
def test_dns_lookup(mocked_logger, mocked_resolver):
    import common as common_util

    mocked_my_resolver = MagicMock()
    mocked_resolver.Resolver.return_value = mocked_my_resolver

    # Case 1: When no DNS server is given
    common_util.dns_lookup(MOCKED_DNS_NAME, MOCKED_DNS_RECORD_TYPE)
    mocked_logger.info.assert_called_once_with("No given DNS server")
    mocked_my_resolver.query.assert_called_with(MOCKED_DNS_NAME, MOCKED_DNS_RECORD_TYPE)

    # Case 2: When DNS server is given
    common_util.dns_lookup(MOCKED_DNS_NAME, MOCKED_DNS_RECORD_TYPE, MOCKED_DNS_SERVERS)
    mocked_logger.info.assert_called_with(f"Given DNS server: {MOCKED_DNS_SERVERS}")

    # Case 3: When exception is raised
    mocked_my_resolver.query.side_effect = Exception("mocked_error")
    common_util.dns_lookup(MOCKED_DNS_NAME, MOCKED_DNS_RECORD_TYPE, MOCKED_DNS_SERVERS)
    logger_exception_calls = [
        call(
            f"Lookup error with name server - 1.1.1.1. Remaining name server for retry - {['2.2.2.2']}. Error: mocked_error"
        ),
        call(
            "Lookup error with name server - 2.2.2.2. Remaining name server for retry - []. Error: mocked_error"
        ),
    ]
    mocked_logger.exception.assert_has_calls(logger_exception_calls)


@patch("common.dns_lookup")
@patch("common.logger", return_value=MagicMock())
def test_dns_lookup_with_retry(mocked_logger, mocked_dns_lookup):
    import common as common_util

    # Case 1: When there are less than 8 IPs in the DNS lookup. break out from retry
    mocked_dns_lookup.return_value = ["10.10.10.10"]
    common_util.dns_lookup_with_retry(MOCKED_DNS_NAME, MOCKED_DNS_RECORD_TYPE, 10)
    mocked_logger.info.assert_called_with(
        "There are less than 8 IPs in the DNS response. Stop further DNS lookup..."
    )

    # Case 2: When DNS lookup return more than 8 IPs. Complete all retry attempts
    mocked_dns_lookup.return_value = [
        "10.10.10.10",
        "11.11.11.11.11",
        "12.12.12.12",
        "13.13.13.13",
        "14.14.14.14",
        "15.15.15.15",
        "16.16.16.16",
        "17.17.17.17",
    ]
    common_util.dns_lookup_with_retry(MOCKED_DNS_NAME, MOCKED_DNS_RECORD_TYPE, 3)
    dns_lookup_calls = [
        call(MOCKED_DNS_NAME, MOCKED_DNS_RECORD_TYPE, []),
        call(MOCKED_DNS_NAME, MOCKED_DNS_RECORD_TYPE, []),
        call(MOCKED_DNS_NAME, MOCKED_DNS_RECORD_TYPE, []),
    ]
    mocked_dns_lookup.assert_has_calls(dns_lookup_calls)


@patch("common.dns_lookup")
@patch("common.logger", return_value=MagicMock())
def test_get_elb_authoritative_name_server_ip_list(mocked_logger, mocked_dns_lookup):
    import common as common_util

    mocked_elb_dns_name = "internal-alb-internal-12345678.us-east-1.elb.amazonaws.com"
    mocked_dns_server_domain_set = {
        "mocked.dns.server.one.com",
        "mocked.dns.server.two.com",
    }
    mocked_dns_lookup.side_effect = [
        ["mocked.dns.server.one.com", "mocked.dns.server.two.com"],
        ["10.10.10.10"],
        ["11.11.11.11"],
    ]
    expected_result = ["10.10.10.10", "11.11.11.11"]
    actual_result = common_util.get_elb_authoritative_name_server_ip_list(
        mocked_elb_dns_name
    )
    logger_info_calls = [
        call(f"ELB regional DNS name: us-east-1.elb.amazonaws.com"),
        call(f"Authoritative name server domain set: {mocked_dns_server_domain_set}"),
        call(f"Authoritative name server IP list: {['10.10.10.10', '11.11.11.11']}"),
    ]
    mocked_logger.info.assert_has_calls(logger_info_calls)
    assert actual_result == expected_result


@patch("common.dns_lookup_with_retry")
@patch("common.get_elb_authoritative_name_server_ip_list")
def test_get_elb_ip_from_dns(
        mocked_get_elb_authoritative_name_server_ip_list, mocked_dns_lookup_with_retry
):
    import common as common_util

    mocked_get_elb_authoritative_name_server_ip_list.return_value = [
        "1.1.1.1",
        "2.2.2.2",
    ]

    common_util.get_elb_ip_from_dns(MOCKED_DNS_NAME, MOCKED_DNS_RECORD_TYPE, 5)
    mocked_dns_lookup_with_retry.assert_called_once_with(
        MOCKED_DNS_NAME, MOCKED_DNS_RECORD_TYPE, 5, ["1.1.1.1", "2.2.2.2"]
    )


@patch("common.logger", return_value=MagicMock())
def test_get_pending_registration_ip_set(mocked_logger):
    import common as common_util

    # Return the IPs that are in DNS but not in the target group
    ip_from_dns_set = {"1.1.1.1", "2.2.2.2", "3.3.3.3"}
    ip_from_target_group_set = {"1.1.1.1"}

    expected_result = {"2.2.2.2", "3.3.3.3"}
    actual_result = common_util.get_pending_registration_ip_set(
        ip_from_dns_set,
        ip_from_target_group_set
    )
    assert actual_result == expected_result


@patch("common.logger", return_value=MagicMock())
def test_get_invocation_count_per_pending_deregistration_ip_without_pending(
        mocked_logger,
):
    # When there is no pending IP from the previous invocation
    # Pending deregistration IPs (Without considering INVOCATIONS_BEFORE_DEREGISTRATION) are:
    # 1. In the active IP list from the previous invocation but no longer in the DNS
    # 2. Currently registered but no longer in the DNS

    import common as common_util

    ip_from_dns_set = {"1.1.1.1", "2.2.2.2", "3.3.3.3"}
    ip_from_target_group_set = {"1.1.1.1", "5.5.5.5"}
    active_ip_set_from_previous_invocation = {"2.2.2.2", "6.6.6.6"}

    # 6.6.6.6 is no longer in the DNS while it is in the active IP list from the previous invocation
    # 5.5.5.5 is no longer in the DNS while it is in the target group
    pending_ip_dict_from_previous_invocation = {}
    expected_result = {"5.5.5.5": 1, "6.6.6.6": 1}
    actual_result = common_util.get_invocation_count_per_pending_deregistration_ip(
        ip_from_dns_set,
        ip_from_target_group_set,
        active_ip_set_from_previous_invocation,
        pending_ip_dict_from_previous_invocation,
    )

    assert actual_result == expected_result


@patch("common.logger", return_value=MagicMock())
def test_get_invocation_count_per_pending_deregistration_ip_with_pending(mocked_logger):
    # When there are pending IPs from the previous invocation
    # Pending deregistration IPs (Without considering INVOCATIONS_BEFORE_DEREGISTRATION) are:
    # 1. In the active IP list from the previous invocation but no longer in the DNS
    # 2. Currently registered but no longer in the DNS

    import common as common_util

    ip_from_dns_set = {"1.1.1.1", "2.2.2.2", "3.3.3.3"}
    ip_from_target_group_set = {"1.1.1.1", "5.5.5.5"}
    active_ip_set_from_previous_invocation = {"2.2.2.2", "6.6.6.6"}

    pending_ip_dict_from_previous_invocation = {
        "1.1.1.1": 1,
        "2.2.2.2": 2,
        "5.5.5.5": 3,
    }
    expected_result = {"5.5.5.5": 4, "6.6.6.6": 1}
    actual_result = common_util.get_invocation_count_per_pending_deregistration_ip(
        ip_from_dns_set,
        ip_from_target_group_set,
        active_ip_set_from_previous_invocation,
        pending_ip_dict_from_previous_invocation,
    )
    assert actual_result == expected_result


@patch("common.logger", return_value=MagicMock())
def test_get_pending_deregistration_ip_set(mocked_logger):
    import common as common_util

    invocation_count_per_pending_deregistration_ip = {
        "1.1.1.1": 1,
        "2.2.2.2": 2,
        "3.3.3.3": 3,
    }
    invocation_before_deregistration = 3
    actual_result = common_util.get_pending_deregistration_ip_set(
        invocation_count_per_pending_deregistration_ip, invocation_before_deregistration
    )
    expected_result = {"3.3.3.3"}
    assert actual_result == expected_result


def test_get_elb_ip_target_from_ip_list_same_vpc():
    import common as common_util

    ip_list = ["1.1.1.1", "2.2.2.2"]
    elb_listener = "80"
    actual_result = common_util.get_elb_ip_target_from_ip_list(ip_list, elb_listener)
    expected_result = [
        {"Id": "1.1.1.1", "Port": "80", },
        {"Id": "2.2.2.2", "Port": "80", },
    ]
    assert actual_result == expected_result


def test_get_elb_ip_target_from_ip_list_different_vpc():
    import common as common_util

    ip_list = ["1.1.1.1", "2.2.2.2"]
    elb_listener = "80"
    with patch("common.LambdaEnv.SAME_VPC", False):
        actual_result = common_util.get_elb_ip_target_from_ip_list(
            ip_list, elb_listener
        )
        expected_result = [
            {"Id": "1.1.1.1", "Port": "80", "AvailabilityZone": "all"},
            {"Id": "2.2.2.2", "Port": "80", "AvailabilityZone": "all"},
        ]
        assert actual_result == expected_result
