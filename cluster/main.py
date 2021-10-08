import json
import logging
import os
from typing import Any, Optional

logging.basicConfig(
    format="%(asctime)s : %(levelname)s : %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)
logger.setLevel("INFO")
import random

from flask import Flask, request
from models.models import Group1, Group2, Group3, db
from werkzeug.exceptions import (
    BadRequest,
    HTTPException,
    InternalServerError,
    NotAcceptable,
    NotFound,
    RequestTimeout,
)
from werkzeug.wrappers import Response

# Initialize Flask application with configs
app = Flask(__name__)
config_path = os.environ["CONFIG_PATH"]
app.config.from_object(config_path)

# Initialize db
db.init_app(app)


@app.before_first_request
def create_all():
    """
    Function that run only before first request and creates all db structure
    defined in models.py
    """
    db.create_all()


# Making mapping between node name and Model
hosts = {
    "node01": Group1,
    "node02": Group2,
    "node03": Group3,
}


@app.route("/ping")
def ping():
    return "PONG\n", 200


def parse_body() -> Optional[Any]:
    """
    Function parses body from request as json.
    Used in POST and DELETE methods.
    Exceptions:
        NotAcceptable:
            Raises exception if body is missing, or "groupId" parameter is missing in body
    Returns:
        Optional[Any]
    """
    body = request.get_json(
        force=True
    )  # force=True Ignores mimetype ("application/json") and tries to parse json
    if body is None:
        raise NotAcceptable("Invalid Request, Please provide body")
    if "groupId" in body:
        return body
    else:
        raise NotAcceptable("Invalid Request, missing groupId in body")


@app.route("/stats", methods=["GET"])
def statistics():
    """
    Function shows statistics of the group records in each group, and helps user to do quick checks.
    Functionality:
        1. Compares groups' groupIds together in unordered form (set) -> True/False
        2. Calculates the number of records in each node -> Dictionary
    Output looks like following
        [bool, {
            "node01": count_1,
            "node01": count_2,
            "node03": count_3
               }
        ]
    """
    group_1 = Group1.query.all()
    group_2 = Group2.query.all()
    group_3 = Group3.query.all()
    group_1_ids = [record.groupId for record in group_1]
    group_2_ids = [record.groupId for record in group_2]
    group_3_ids = [record.groupId for record in group_3]

    return (
        json.dumps(
            [
                set(group_1_ids) == set(group_2_ids) == set(group_3_ids),
                {
                    "node01": len(group_1),
                    "node02": len(group_2),
                    "node03": len(group_3),
                },
            ]
        ),
        200,
    )


@app.route("/group", methods=["POST", "DELETE"])
@app.route("/group/<groupId>", methods=["GET"])
def group(groupId: Optional[str] = None):
    """
    Endpoint implements the functionality of Unstable API.
    It accepts following request methods
        POST   -> For creating group in node
        DELETE -> Fore deleting group from node
        GET    -> For returning group data from node
    Args:
        groupId: Mandatory only for GET request
    """
    random_exception()  # Unstable connection imitation
    node = request.headers.get(
        "node"
    )  # node parameter in headers replaces running 3 separate servers (nodes)
    timestamp = request.headers.get(
        "timestamp"
    )  # Needed for differentiation of current and existing records
    if timestamp:
        timestamp = float(timestamp)

    if node is None:
        raise NotAcceptable("provide node parameter in request headers")

    Group = hosts.get(node)  # take Group Model corresponding to the node
    if Group is None:
        raise NotAcceptable(
            f"node {node} is not configured. Available nodes {list(hosts.keys())}"
        )

    groups = Group.query.all()
    logger.debug(groups)
    if groups:
        logger.debug([(g.id, g.groupId) for g in Group.query.all()])

    if request.method == "GET":
        """
        Checking of existence of the group record by given groupId
        Afterwards returns response containing groupId or raises NotFound Exception
        """
        group = Group.query.filter_by(groupId=groupId).first()
        if group:
            return {"groupId": groupId}, 200
        else:
            raise NotFound(f"No group record found with id '{groupId}'")

    if request.method == "DELETE":
        """
        This method uses for deleting a group record from the table.
        If timestamp was provided it will first query by given groupId and given timestamp,
        otherwise will query only by groupId.
        If corresponding group record found it will delete group record from the table
        otherwise will raise Not Found error
        """
        body = parse_body()
        group_id = body["groupId"]
        if timestamp:
            group = Group.query.filter_by(groupId=group_id, timestamp=timestamp).first()
            if group:
                logger.info("Will delete group %s %s", group.timestamp, group.groupId)
        else:
            group = Group.query.filter_by(groupId=group_id).first()
        if group:
            db.session.delete(group)
            db.session.commit()
            return "OK\n", 200
        else:
            if timestamp:
                raise NotFound(
                    f"No group record found with id '{group_id}' and timestamp '{timestamp}'"
                )
            else:
                raise NotFound(f"No group record found with id '{group_id}'")

    if request.method == "POST":
        """
        This method uses for creating a group record from the table.
        First it queries for a group by groupId and if group found it will raise
        BadRequest (400) error, because object exists in the table.
        Otherwise if timestamp was provided it will create group object by specifying
        groupId and timestamp, if not provided only by groupId, and will add to the table.
        Here, also in case of DELETE I introduced timestamp parameter for differentiation object
        that created during one procedure from objects that are there before.
        """
        body = parse_body()
        group_id = body["groupId"]
        group = Group.query.filter_by(groupId=group_id).first()
        if group:
            raise BadRequest("Perhaps the object exists.")
        else:
            if timestamp:
                group = Group(groupId=group_id, timestamp=timestamp)
            else:
                group = Group(groupId=group_id)
            db.session.add(group)
            db.session.commit()
            return "CREATED\n", 201


def random_exception():
    """
    Unstable connection imitation.
    Function is randomly raising exception by choosing from the list of exception
        [InternalServerError, RequestTimeout]
    Function has threshold parameter, which is probability of RANDOM behavior.
    It means if threshold (which is RANDOM_BEHAVIOR env parameter) is 0,
    function will not have effect, and API will be stable.
    If no RANDOM_BEHAVIOR provided in environment, by default 0.5 will be taken
    """
    random_number = random.random()
    thresh = app.config.get("RANDOM_BEHAVIOR", 0.5)
    logger.info("RANDOM_BEHAVIOR %s", thresh)
    if random_number < thresh:
        raise random.choice(
            [
                InternalServerError("InternalServerError due to Random Behavior"),
                RequestTimeout("Timeout due to Random Behavior"),
            ]
        )


@app.errorhandler(HTTPException)
def handle_exception(e: HTTPException) -> Response:
    """Return JSON instead of HTML for HTTP errors."""
    response = e.get_response()
    logger.exception(e)
    response.data = json.dumps(
        {
            "message": e.description,
            "status": e.code,
        }
    )
    response.content_type = "application/json"
    return response


if __name__ == "__main__":
    logger.info("System started...")
    app.run(host="localhost", port=5000)
