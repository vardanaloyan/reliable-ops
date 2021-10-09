from multiprocessing import Pool

import click
import requests
from connector import Connector
import logging

logger = logging.getLogger("JOB")
logging.basicConfig(level="INFO")

# For running job script in local machine
# HOSTS = {
#     "node01": "http://127.0.0.1:8080",
#     "node02": "http://127.0.0.1:8080",
#     "node03": "http://127.0.0.1:8080",
# }

# For running job script in docker container
HOSTS = {
    "node01": "http://node01.app.internal.com/v1",
    "node02": "http://node02.app.internal.com/v1",
    "node03": "http://node03.app.internal.com/v1",
}
N_PROC = 16  # Number of parallel processes

test_groupId_list = [str(i) for i in range(0, 100)]  # groupIds list for tests


@click.group()
def cli():
    pass


@cli.command(name="stats", help="Shows the statistics of the groups")
def stats():
    logger.info("Running stats command for showing statistics of group records")
    url = HOSTS[
        "node01"
    ]  # Could be used, one of the nodes arbitrary /"node02", "node03"/
    resp = requests.get(f"{url}/stats")
    click.echo(resp.json())


@cli.command(
    name="create",
    help="Creates bunch of groups specified in global parameter <test_group_list>",
)
def parallel_creates():
    logger.info("Running parallel creates command on <%s> items", len(test_groupId_list))
    with Pool(N_PROC) as p:
        p.map(Connector(HOSTS).create_group, test_groupId_list)


@cli.command(
    name="delete",
    help="Deletes bunch of groups specified in global parameter <test_group_list>",
)
def parallel_deletes():
    logger.info("Running parallel deletes command on <%s> items", len(test_groupId_list))
    with Pool(N_PROC) as p:
        p.map(Connector(HOSTS).delete_group, test_groupId_list)


@cli.command(
    name="delete-one",
    help="Deletes a specified group record",
)
@click.argument('group_id', required=1)
def delete_one(group_id):
    logger.info("Running delete-one command with groupId <%s>", group_id)
    Connector(HOSTS).delete_group(group_id)


@cli.command(
    name="create-one",
    help="Creates a specified group record",
)
@click.argument('group_id', required=1)
def create_one(group_id):
    logger.info("Running create-one command with groupId <%s>", group_id)
    Connector(HOSTS).create_group(group_id)


if __name__ == "__main__":
    cli()
