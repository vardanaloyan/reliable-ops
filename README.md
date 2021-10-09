API CONSUMER

# Introduction

Application consists of two parts

- API
- API Consumer

API does imitation of 3 nodes by accepting "node" parameter in the headers.
So instead of running same web applications with three different configurations
(host, port, db), I am running one web application which has one database,
and inside has three different tables corresponding to the nodes (Group1, Group2, Group3).

Web application was written using Flask web framework and runs using gunicorn

Tree view of the repository
```
reliable-ops/
    ├── Dockerfile
    ├── README.md
    ├── cluster
    │   ├── __init__.py
    │   ├── config
    │   ├── docs
    │   ├── main.py
    │   ├── models
    │   └── requirements.txt
    ├── confs
    │   ├── hosts.txt
    │   ├── nginx.conf
    │   └── start.sh
    ├── docker-compose.yml
    ├── scripts
    │   ├── __pycache__
    │   ├── connector.py
    │   └── job.py
    └── storage
        └── cluster.db
```

Description the structure

- `cluster` - API implementation
- `confs` - Environment configuration
- `scripts` - API Consumer implementation (Connector class and job script implementation)
- `storage` - Attached volume, for keeping db data

`docker-compose -f docker-compose.yml build`

`docker-compose -f docker-compose.yml up -d`

`docker-compose exec cluster bash`

`cd /scripts/`

`curl node01.app.internal.com/ping/`

curl --header "node: node01" node01.app.internal.com/v1/group/1


`curl -X POST --header "node: node01" -d '{"groupId":"1"}' node01.app.internal.com/v1/group`

`python3 job.py`

curl 127.0.0.1:8080/stats 

curl -X DELETE --header "node: node01" -d '{"groupId":"106"}' http://127.0.0.1:8080/group

curl -H "node: node02" 127.0.0.1:8080/group/1
