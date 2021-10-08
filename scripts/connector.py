import json
import logging
import time
from datetime import datetime

import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level="INFO")


def retry(max_retries: int = 2, sleep: float = 2):
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


def create_node_group(group_id, host, node, timestamp):
    header = {"node": node, "timestamp": str(timestamp)}
    body = {"groupId": str(group_id)}
    group_url = f"{host}/group"
    logger.info(f"Trying to create %s, data: %s, headers: %s", group_url, body, header)
    resp = requests.post(group_url, data=json.dumps(body), headers=header)
    logger.info("Response %s, %s", resp, resp.text)
    return resp


def delete_node_group(group_id, host, node, timestamp=None):
    if timestamp:
        header = {"node": node, "timestamp": str(timestamp)}
    else:
        header = {
            "node": node,
        }

    body = {"groupId": str(group_id)}
    group_url = f"{host}/group"
    logger.info(f"Trying to delete %s, data: %s, headers: %s", group_url, body, header)
    resp = requests.delete(group_url, data=json.dumps(body), headers=header)
    logger.info("Response %s, %s", resp, resp.text)
    return resp


def get_node_group(group_id, host, node, timestamp=None):
    if timestamp:
        header = {"node": node, "timestamp": str(timestamp)}
    else:
        header = {
            "node": node,
        }
    group_url = f"{host}/group/{group_id}"
    resp = requests.get(group_url, headers=header)
    return resp


class RollbackError(Exception):
    pass


def check_group_exists(group_id, host, node, timestamp=None):
    while 1:
        resp = get_node_group(group_id, host, node, timestamp)
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


class Connector:
    def __init__(self, hosts):
        self.hosts = hosts
        self.normal_status_codes = [400, 404, 201, 200]
        self.rollback_create_hosts = []
        self.rollback_delete_hosts = []

    def create_group(self, group_id):
        for node, host in self.hosts.items():
            timestamp = datetime.utcnow().timestamp()
            resp = create_node_group(group_id, host, node, timestamp)
            self.rollback_create_hosts.append((node, host, timestamp))
            if resp.status_code not in self.normal_status_codes:
                self.rollback_create(group_id)
                break

    @retry(max_retries=5, sleep=0.2)
    def rollback_create(self, group_id):
        while self.rollback_create_hosts:
            node, host, timestamp = self.rollback_create_hosts[0]
            logger.info("Trying to rollback")
            resp = delete_node_group(group_id, host, node, timestamp)
            if resp.status_code not in self.normal_status_codes:
                raise RollbackError
            else:
                if self.rollback_create_hosts:
                    self.rollback_create_hosts.pop(0)

    def delete_group(self, group_id):
        for node, host in self.hosts.items():
            timestamp = datetime.utcnow().timestamp()
            if check_group_exists(group_id, host, node):
                resp = delete_node_group(group_id, host, node)
            else:
                break
            self.rollback_delete_hosts.append((node, host, timestamp))
            if resp.status_code not in self.normal_status_codes:
                self.rollback_delete(group_id)
                break

    @retry(max_retries=5, sleep=0.2)
    def rollback_delete(self, group_id):
        while self.rollback_delete_hosts:
            node, host, timestamp = self.rollback_delete_hosts[0]
            logger.info("Trying to rollback")
            resp = create_node_group(group_id, host, node, timestamp)
            if resp.status_code not in self.normal_status_codes:
                raise RollbackError
            else:
                if self.rollback_delete_hosts:
                    self.rollback_delete_hosts.pop(0)
