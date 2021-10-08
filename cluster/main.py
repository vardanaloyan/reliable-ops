import json
import logging
import os

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

# Initialize Flask application with development configs
app = Flask(__name__)
config_path = os.environ["CONFIG_PATH"]
app.config.from_object(config_path)

# Initialize db
db.init_app(app)


@app.before_first_request
def create_all():
    """
    Function that run only in first request and creates all db structure
    defined in models.py
    Returns: None
    """
    db.create_all()


hosts = {
    "node01": Group1,
    "node02": Group2,
    "node03": Group3,
}


@app.route("/ping")
def ping():
    return "PONG\n", 200


def parse_body():
    body = request.get_json(force=True)
    if body is None:
        raise NotAcceptable("Invalid Request, Please provide body")
    if "groupId" in body:
        return body
    else:
        raise NotAcceptable("Invalid Request, missing groupId in body")


# write statistics endpoint for showing datas
@app.route("/stats", methods=["GET"])
def statistics():
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
def group(groupId=None):
    random_exception()
    node = request.headers.get("node")
    timestamp = request.headers.get("timestamp")
    if timestamp:
        timestamp = float(timestamp)

    if node is None:
        raise NotAcceptable("provide node parameter in request headers")

    Group = hosts.get(node)
    if Group is None:
        raise NotAcceptable(
            f"node {node} is not configured. Available nodes {list(hosts.keys())}"
        )

    groups = Group.query.all()
    logger.debug(groups)
    if groups:
        logger.debug([(g.id, g.groupId) for g in Group.query.all()])

    if request.method == "GET":
        group = Group.query.filter_by(groupId=groupId).first()
        if group:
            return {"groupId": groupId}, 200
        else:
            raise NotFound(f"No group record found with id '{groupId}'")

    if request.method == "DELETE":
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
