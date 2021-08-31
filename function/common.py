import logging
import dns.resolver
from collections import defaultdict
from constant import LambdaEnv

# Timeout on one NS
DNS_RESOLVER_TIMEOUT = 1
# Timeout through out all of the NS
DNS_RESOLVER_LIFETIME = 10

logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)


def precondition(pre_condition, error_message):
    """
    Raise ValueError when pre-condition is False
    :param pre_condition: pre-condition statement
    :param error_message: error message passed to the exception
    """
    if not pre_condition:
        logger.error(f"Pre-condition: {pre_condition}. Error message: {error_message}")
        raise ValueError(error_message)


def dns_lookup(domain_name, record_type, dns_servers=[]):
    """
    Get dns lookup results
    :param dns_servers: list of DNS server IP addresses
    :param record_type: DNS record type
    :param domain_name: DNS name
    :return: list of dns lookup results
    """
    lookup_result_list = []
    my_resolver = dns.resolver.Resolver()
    my_resolver.rotate = True

    # When no specific DNS name server is given
    if not dns_servers:
        logger.info("No given DNS server")
        lookup_answers = my_resolver.query(domain_name, record_type)
        lookup_result_list = [str(answer) for answer in lookup_answers]
        return lookup_result_list

    # When a list of DNS name server (IP addresses) is given. Iterate over them until get the DNS lookup result
    for nameserver in dns_servers.copy():
        try:
            logger.info(f"Given DNS server: {dns_servers}")
            my_resolver.nameservers = [nameserver]
            lookup_answers = my_resolver.query(domain_name, record_type)
            lookup_result_list = [str(answer) for answer in lookup_answers]
            return lookup_result_list
        except Exception as e:
            dns_servers.remove(nameserver)
            logger.exception(
                f"Lookup error with name server - {nameserver}. "
                f"Remaining name server for retry - {dns_servers}. Error: {e}"
            )
            continue


def dns_lookup_with_retry(domain_name, record_type, total_retry_count, dns_servers=[]):
    """
    Get dns lookup results with retry
    :param domain_name:
    :param record_type:
    :param total_retry_count:
    :param dns_servers:
    :return:
    """
    dns_lookup_result_set = set()
    attempt = 1
    while attempt <= total_retry_count:
        lookup_result_per_attempt = dns_lookup(domain_name, record_type, dns_servers)
        dns_lookup_result_set = set(lookup_result_per_attempt) | dns_lookup_result_set
        logger.info(
            f"Attempt-{attempt}: DNS lookup IP count: {len(dns_lookup_result_set)}. "
            f"DNS lookup result: {dns_lookup_result_set}"
        )
        if len(lookup_result_per_attempt) < 8:
            logger.info(
                "There are less than 8 IPs in the DNS response. Stop further DNS lookup..."
            )
            break
        attempt += 1
    return dns_lookup_result_set


def get_elb_authoritative_name_server_ip_list(elb_dns_name):
    """
    Get the IP address of ELB's authoritative DNS name server
    :param elb_dns_name: DNS name of ELB
    :return: list of authoritative name server IP
    """
    authoritative_server_ip_list = []
    elb_regional_dns_name = ".".join(elb_dns_name.split(".")[1:])
    logger.info(f"ELB regional DNS name: {elb_regional_dns_name}")
    authoritative_server_dns_set = set(dns_lookup(elb_regional_dns_name, "NS"))
    logger.info(f"Authoritative name server domain set: {authoritative_server_dns_set}")
    for authoritative_server_dns_name in authoritative_server_dns_set:
        authoritative_server_ip_list += dns_lookup(authoritative_server_dns_name, "A")
    logger.info(f"Authoritative name server IP list: {authoritative_server_ip_list}")
    return authoritative_server_ip_list


def get_elb_ip_from_dns(elb_dns_name, record_type, total_retry_count):
    """
    Get ELB node IP through DNS lookup
    :param elb_dns_name: DNS name of ELB
    :param record_type: DNS record type. e.g. A or AAAA
    :param total_retry_count: Total DNS lookup count
    :return: a set of ELB node IP addresses
    """
    # Get ELB authoritative name server IP addresses
    authoritative_server_ip_list = get_elb_authoritative_name_server_ip_list(
        elb_dns_name
    )

    # Get ELB IP through DNS lookup
    elb_ip_set = dns_lookup_with_retry(
        elb_dns_name, record_type, total_retry_count, authoritative_server_ip_list
    )
    return elb_ip_set


def get_pending_registration_ip_set(
        ip_from_dns_set, ip_from_target_group_set
):
    """
    # Get a set of IPs that are pending for registration:
    # Pending registration IPs that meet all the following conditions:
    # 1. IPs that are currently in the DNS
    # 2. Those IPs must have not been registered yet
    :param ip_from_target_group_set: a set of IPs that are currently registered with a target group
    :param ip_from_dns_set: a set of IPs that are in the DNS
    """

    pending_registration_ip_set = ip_from_dns_set - ip_from_target_group_set
    return pending_registration_ip_set


def get_invocation_count_per_pending_deregistration_ip(
        ip_from_dns_set,
        ip_from_target_group_set,
        active_ip_set_from_previous_invocation,
        pending_ip_dict_from_previous_invocation,
):
    """
    Get a mapping of pending deregistration IP and the count of Lambda invocations that this IP has been detected
    :param ip_from_dns_set: a set of IPs that are in the DNS
    :param ip_from_target_group_set: a set of IPs that are currently registered with a target group
    :param active_ip_set_from_previous_invocation:  a set of active IPs from the previous invocation
    :param pending_ip_dict_from_previous_invocation:  a dict of pending IPs and their invocation count from the previous invocation
    :return: mapping of pending deregistration IPs and the Lambda invocations count that the IPs have been detected. e.g.
    {'172.16.2.245': 1, '172.16.3.178': 1}
    """
    # Raw pending registration IPs are the ones that: (Without considering INVOCATIONS_BEFORE_DEREGISTRATION)
    # 1. In the active IP list from the previous invocation but no longer in the DNS
    # 2. Currently registered but no longer in the DNS

    pending_ip_from_previous_invocation_set = (
        set(pending_ip_dict_from_previous_invocation.keys())
        if pending_ip_dict_from_previous_invocation
        else set()
    )

    # IPs that are in the active list from the previous invocation while not present in the DNS
    ip_in_previous_active_ip_not_in_dns = (
            active_ip_set_from_previous_invocation - ip_from_dns_set
    )
    logger.info(
        f"IPs are previously active but no longer in the DNS: {ip_in_previous_active_ip_not_in_dns}"
    )

    # IPs that are currently registered but not in the DNS
    ip_in_target_group_not_in_dns = ip_from_target_group_set - ip_from_dns_set
    logger.info(
        f"IPs are currently in the target group but no longer in the DNS: {ip_in_target_group_not_in_dns}"
    )

    # We keep tracking for how many invocations a pending deregistration IP has been detected.
    # The deregistration API is only called when the pending IPs's invocation count is higher than INVOCATIONS_BEFORE_DEREGISTRATION
    invocation_count_per_pending_deregistration_ip = defaultdict(int)
    pending_ip_from_current_invocation_set = (
            ip_in_previous_active_ip_not_in_dns | ip_in_target_group_not_in_dns
    )
    logger.info(
        f"Pending deregistration IPs from current invocation (without considering INVOCATIONS_BEFORE_DEREGISTRATION) - "
        f"{pending_ip_from_current_invocation_set}"
    )

    if pending_ip_from_previous_invocation_set:
        new_pending_ip_set = (
                pending_ip_from_current_invocation_set
                - pending_ip_from_previous_invocation_set
        )
        logger.info(
            f"IPs that are detected as pending deregistration for the first time - {new_pending_ip_set}"
        )
        existing_pending_ip_set = (
                pending_ip_from_current_invocation_set - new_pending_ip_set
        )
        logger.info(
            f"IPs that have already been detected as pending deregistration from previous invocation - {existing_pending_ip_set}"
        )
        invalid_pending_ip_set = (
                pending_ip_from_previous_invocation_set
                - pending_ip_from_current_invocation_set
        )
        logger.info(
            f"IPs that were detected as pending deregistration but no longer considered as pending - {invalid_pending_ip_set}"
        )

        # Set the new pending IP invocation count to 1
        for new_pending_ip in new_pending_ip_set:
            invocation_count_per_pending_deregistration_ip[new_pending_ip] = 1

        # Increase the invocation count for the IPs that are already in the previous pending IP list
        for existing_pending_ip in existing_pending_ip_set:
            invocation_count_per_pending_deregistration_ip[existing_pending_ip] = (
                    pending_ip_dict_from_previous_invocation[existing_pending_ip] + 1
            )

        return invocation_count_per_pending_deregistration_ip

    logger.info("No pending deregistration IP found from the previous invocations")
    for pending_ip in pending_ip_from_current_invocation_set:
        invocation_count_per_pending_deregistration_ip[pending_ip] = 1

    return invocation_count_per_pending_deregistration_ip


def get_pending_deregistration_ip_set(
        invocation_count_per_pending_deregistration_ip, invocation_before_deregistration
):
    """
    Get a set of IPs that are pending deregistration
    :param invocation_before_deregistration: invocation count that has to be reached first before calling deregistration API
    :param invocation_count_per_pending_deregistration_ip: mapping of pending deregistration IPs and the Lambda invocations count that the IPs have been detected. e.g.
    {'172.16.2.245': 1, '172.16.3.178': 1}
    :return: a set of IPs that are pending deregistration. e.g. {'1.1.1.1', '2.2.2.2'}
    """
    pending_deregistration_ip_set = set()
    for ip, invocation_count in invocation_count_per_pending_deregistration_ip.items():
        if invocation_count >= invocation_before_deregistration:
            pending_deregistration_ip_set.add(ip)
    logger.info(
        f"Pending deregistration IPs for the current invocation - {pending_deregistration_ip_set}"
    )
    return pending_deregistration_ip_set


def get_elb_ip_target_from_ip_list(ip_list, elb_listener):
    """
    Get a list of targets for registration or deregistration
    :param ip_list: list of IP
    :param elb_listener: ELB listener port (str)
    :return: a list of targets required by registration/deregistration API
    """
    target_list = []
    for ip in ip_list:
        if LambdaEnv.SAME_VPC:
            target = {"Id": ip, "Port": elb_listener}
        else:
            target = {"Id": ip, "Port": elb_listener, "AvailabilityZone": "all"}
        target_list.append(target)
    return target_list
