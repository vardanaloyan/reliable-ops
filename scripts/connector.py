import json
import logging
import time
from datetime import datetime
from typing import Optional

import requests
from requests import Response

logger = logging.getLogger(__name__)


def retry(max_retries: int = 2, sleep: float = 2):
    """
    Simple retry decorator
    Args:
        max_retries: Number of maximum retries
        sleep: timeout between retries
    """

    def inner_decorator(func):
        def wrapper(*args, **kwargs):
            for i in range(1, max_retries + 2):
                try:
                    return func(*args, **kwargs)
                except RollbackError as e:
                    if i <= max_retries:
                        time.sleep(sleep)
                        logger.info(
                            "Retrying %s. Retry %s after %s seconds...",
                            func.__qualname__,
                            i,
                            sleep,
                        )
                        continue
                    else:
                        logger.info(
                            "Giving up retrying %s after %s retries...",
                            func.__name__,
                            max_retries,
                        )
                        raise e

        return wrapper

    return inner_decorator


def create_node_group(
    group_id: str, host: str, node: str, timestamp: Optional[float]
) -> Response:
    """
    Atomic function for creating one group record in one node. Function is doing API call POST method
    Args:
        group_id: id of group record
        host: url of the host
        node: node name
        timestamp: timestamp in seconds

    If timestamp was provided it would be added into headers

    Returns:
        Response
    """
    header = {
        "node": node,
        "timestamp": str(timestamp),
    }
    body = {
        "groupId": str(group_id),
    }
    group_url = f"{host}/group"
    logger.info(f"Trying to create %s, data: %s, headers: %s", group_url, body, header)
    resp = requests.post(group_url, data=json.dumps(body), headers=header)
    logger.info("Response %s, %s", resp, resp.text)
    return resp


def delete_node_group(
    group_id: str, host: str, node: str, timestamp: Optional[float] = None
):
    """
    Atomic function for deleting one group record in one node. Function is doing API call DELETE method
    Args:
        group_id: id of group record
        host: url of the host
        node: node name
        timestamp: timestamp in seconds

    If timestamp was provided it would be added into headers

    Returns:
        Response
    """
    if timestamp:
        header = {
            "node": node,
            "timestamp": str(timestamp),
        }
    else:
        header = {
            "node": node,
        }

    body = {
        "groupId": str(group_id),
    }
    group_url = f"{host}/group"
    logger.info(f"Trying to delete %s, data: %s, headers: %s", group_url, body, header)
    resp = requests.delete(group_url, data=json.dumps(body), headers=header)
    logger.info("Response %s, %s", resp, resp.text)
    return resp


def get_node_group(group_id: str, host: str, node: str) -> Response:
    """
    Function implements GET method, for returning group record by specified group_id
    Args:
        group_id: id of group record
        host: url of the host
        node: node name

    Returns:
        Response
    """
    header = {
        "node": node,
    }
    group_url = f"{host}/group/{group_id}"
    resp = requests.get(group_url, headers=header)
    return resp


def check_group_exists(group_id: str, host: str, node: str) -> bool:
    """
    Function is used in Connection.delete_group method and it's mandatory to cover the case,
    when you are requesting to delete non existing item and it's failing due to random behavior.
    If we don't check the existing of the record in the table before deleting in it could cause,
    wrong data insertion.
    Consider following situation
        Request for deletion object (non existing) and it fails due to random behavior.
        It will enter to rollback process. But as we got InternalError or RequestTimeout error,
        theoretically we don't know does backand manage delete the record or not. So in rollback
        procedure it will recreate it again if we won't check either it exists or no.
        But doing a pre-check before deletion, we could prevent that situation.

    Here Infinite loop is not best solution, with retry decorator it will be more proper,
    but I leave everything simple. I am sure that modification of this function is pretty simple
    and straightforward.

    Args:
        group_id: id of group record
        host: url of the host
        node: node name

    Returns:
        True/False
    """
    while 1:
        resp = get_node_group(group_id, host, node)
        logger.info(
            "Checking existence of group with groupId: %s, node: %s, status_code: %s, response: %s",
            group_id,
            node,
            resp.status_code,
            resp.text,
        )
        if resp.status_code == 200:
            return True
        elif resp.status_code == 404:
            return False


class RollbackError(Exception):
    """
    Handled in retry decorator
    """

    pass


class Connector:
    """
    Connector class which makes creation and deletion of the group records in a cluster more reliable
    Class has 2 major methods:
        1. create_group
             |-> rollback_create               # If random errors occurred called rollback_create
                     |-> delete_node_group     # rollback of creating is deletion

        2. delete_group
             |-> rollback_delete               # If random errors occurred called rollback_delete
                     |-> create_node_group     # rollback of deleting is creation
    """

    def __init__(self, hosts):
        self.hosts = hosts
        # All status_codes that provides API without influence of random effects
        self.acceptable_status_codes = [400, 404, 201, 200]
        # containers for collecting temporary data needed for rollback
        self.rollback_create_hosts = []
        self.rollback_delete_hosts = []

    def create_group(self, group_id: str):
        for node, host in self.hosts.items():
            timestamp = datetime.utcnow().timestamp()
            resp = create_node_group(group_id, host, node, timestamp)
            self.rollback_create_hosts.append((node, host, timestamp))
            if resp.status_code not in self.acceptable_status_codes:
                self.rollback_create(group_id)
                break

    @retry(max_retries=10, sleep=0.1)
    def rollback_create(self, group_id: str):
        while self.rollback_create_hosts:
            node, host, timestamp = self.rollback_create_hosts[0]
            logger.info("Trying to rollback")
            resp = delete_node_group(group_id, host, node, timestamp)
            if resp.status_code not in self.acceptable_status_codes:
                raise RollbackError
            else:
                if self.rollback_create_hosts:
                    self.rollback_create_hosts.pop(0)

    def delete_group(self, group_id: str):
        for node, host in self.hosts.items():
            timestamp = datetime.utcnow().timestamp()
            if check_group_exists(group_id, host, node):
                resp = delete_node_group(group_id, host, node)
            else:
                break
            self.rollback_delete_hosts.append((node, host, timestamp))
            if resp.status_code not in self.acceptable_status_codes:
                self.rollback_delete(group_id)
                break

    @retry(max_retries=10, sleep=0.1)
    def rollback_delete(self, group_id: str):
        while self.rollback_delete_hosts:
            node, host, timestamp = self.rollback_delete_hosts[0]
            logger.info("Trying to rollback")
            resp = create_node_group(group_id, host, node, timestamp)
            if resp.status_code not in self.acceptable_status_codes:
                raise RollbackError
            else:
                if self.rollback_delete_hosts:
                    self.rollback_delete_hosts.pop(0)
