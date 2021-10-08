from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Group1(db.Model):
    __tablename__ = "group1"
    id = db.Column(db.Integer, primary_key=True)
    groupId = db.Column(db.String, unique=True)
    timestamp = db.Column(db.Float)


class Group2(db.Model):
    __tablename__ = "group2"

    id = db.Column(db.Integer, primary_key=True)
    groupId = db.Column(db.String, unique=True)
    timestamp = db.Column(db.Float)


class Group3(db.Model):
    __tablename__ = "group3"

    id = db.Column(db.Integer, primary_key=True)
    groupId = db.Column(db.String, unique=True)
    timestamp = db.Column(db.Float, default=datetime.utcnow().timestamp)
