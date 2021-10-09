# API CONSUMER

## Introduction

Application consists of three parts

- API
- API Consumer
- Job module

**API** does the imitation of 3 nodes by accepting "node" parameter in the headers.
So instead of running same web applications with three different configurations
(host, port, db), I am running one web application which has one database,
and inside has three different tables corresponding to the nodes (Group1, Group2, Group3).

Web application was written using Flask web framework and runs using gunicorn WSGI HTTP Server.

Click [here](./cluster/docs/APIDoc.md) for API documentation.

API is taking config path from environmental `CONFIG_PATH` variable, which in this case points to 
`config.cluster.py` file.

Worth noting is `RANDOM_BEHAVIOR` parameter in config file, using which You can control probability of random errors
that could occur during the calls. So if it was set to 0 You won't see any kind of Internal or Timeout errors. 
And if it was set to 1, probably you could not do any kind of operation.

Another kind of details were covered in the docstrings.

**API consumer** uses API and implements Connector class which will create and delete objects in the cluster as reliably as possible.

**Job script** is using Connector class to create and delete both single and a bunch of group records. 


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


## HOW TO RUN


```bash
# BUILD IMAGE
docker-compose -f docker-compose.yml build
```

```bash
# RUN IMAGE IN DETACHED MODE
docker-compose -f docker-compose.yml up -d
```

```bash
# CREATE A NEW BASH SESSION IN THE CONTAINER
docker-compose exec -w /scripts cluster bash
```

```bash
# CHECK CONNECTION WITH THE WEB APP
curl node01.app.internal.com/ping/
# If you got PONG in response, then it works !
```

Run `python3 job.py --help` to see available commands. It is command line utility made using using [click](https://click.palletsprojects.com/en/8.0.x/) library.

```bash
# RUN JOB HELP
root@1fb3bf8be20d:/scripts# python3 job.py --help
Usage: job.py [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  create      Creates bunch of groups specified in global parameter...
  create-one  Creates a specified group record
  delete      Deletes bunch of groups specified in global parameter...
  delete-one  Deletes a specified group record
  stats       Shows the statistics of the groups
```
To see the number of group records in nodes and to be sure that group ids are matching between nodes type

```bash
root@1fb3bf8be20d:/scripts# python3 job.py stats 
INFO:JOB:Running stats command for showing statistics of group records
[True, {'node01': 0, 'node02': 0, 'node03': 0}]
```
True means that group ids are the same within all nodes, and in dictionary we see the number of records corresponding to the nodes

---

So for creating one item run command below, and if Random errors will not happen, Your output will look like following

```bash
# python3 job.py create-one <groupId>
root@1fb3bf8be20d:/scripts# python3 job.py create-one 1
INFO:JOB:Running create-one command with groupId <1>

INFO:connector:Trying to create http://node01.app.internal.com/v1/group, data: {'groupId': '1'}, headers: {'node': 'node01', 'timestamp': '1633786070.879454'}
INFO:connector:Response <Response [201]>, CREATED

INFO:connector:Trying to create http://node01.app.internal.com/v1/group, data: {'groupId': '1'}, headers: {'node': 'node02', 'timestamp': '1633786071.001518'}
INFO:connector:Response <Response [201]>, CREATED

INFO:connector:Trying to create http://node01.app.internal.com/v1/group, data: {'groupId': '1'}, headers: {'node': 'node03', 'timestamp': '1633786071.135351'}
INFO:connector:Response <Response [201]>, CREATED
```

Creating a bunch of records in parallel for groupIds in range [0-99].
```bash
python3 job.py create
```

Deleting a bunch of records in parallel for groupIds in range [0-99].
```bash
python3 job.py delete
```

To see the number of group records in nodes and to be sure that group ids are matching between nodes type
```bash
python3 job.py stats
```


## Explanation of Algorithm behind Connector class

### Reliable create

Every time when there was a create command of group record,
it loops over all nodes and sends request to corresponding node, 
afterwards information about node,host and timestamp will be added to the list (`rollback_create_hosts`).
Then if response's status code is not from the list of `acceptable_status_codes`,
loop will break and enter to `rollback_create` process. Rollback of create
process is delete.

Flow of `rollback_create` process is following.

It is decorated by retry decorator, which will retry calling the function in case of 
`RollbackError` Exception. And `RollbackError` Exception will be raised if the response's status code
of delete call will not be from the list of `acceptable_status_codes`. And decorator will repeat the delete command 
till the deletion will be success or by reaching max_retries.

In case of successful deletion, tuple of host, node, and timestamp will be popped out from the list of `rollback_create_hosts`.

And the process are going to be repeated untill all tuples will be popped out from the list.

### Reliable delete

Reliable deletion algorithm is very similar to the creation algorithm, but has one difference.

Before running deletion request, we are checking the existence of the group record using `check_group_exists` function. 
I am doing that to prevent wrong data insertion. I describe the situation in the docstring of `check_group_exists` function.

### Example of the processes

I will explain each process (create and delete) using job.py command line tool, in real examples.

#### Creation process

Let's start from creation. We will create group record with groupId equal to 5 by running
`python3 job.py create-one 5` command.

I got following output, which shows, that we don't get any Random error, and our record was created.
```bash
root@cf68c839f47d:/scripts# python3 job.py create-one 5
INFO:JOB:Running create-one command with groupId <5>
INFO:connector:Trying to create http://node01.app.internal.com/v1/group, data: {'groupId': '5'}, headers: {'node': 'node01', 'timestamp': '1633806680.426599'}
INFO:connector:Response <Response [201]>, CREATED

INFO:connector:Trying to create http://node01.app.internal.com/v1/group, data: {'groupId': '5'}, headers: {'node': 'node02', 'timestamp': '1633806680.463768'}
INFO:connector:Response <Response [201]>, CREATED

INFO:connector:Trying to create http://node01.app.internal.com/v1/group, data: {'groupId': '5'}, headers: {'node': 'node03', 'timestamp': '1633806680.50237'}
INFO:connector:Response <Response [201]>, CREATED
```

We can check it by running stats (statistics) command

```bash
root@cf68c839f47d:/scripts# python3 job.py stats
INFO:JOB:Running stats command for showing statistics of group records
[True, {'node01': 1, 'node02': 1, 'node03': 1}]
```

Let's create group record with groupId 6.

```bash
root@cf68c839f47d:/scripts# python3 job.py create-one 6
INFO:JOB:Running create-one command with groupId <6>
INFO:connector:Trying to create http://node01.app.internal.com/v1/group, data: {'groupId': '6'}, headers: {'node': 'node01', 'timestamp': '1633806862.284902'}
INFO:connector:Response <Response [408]>, {"message": "Timeout due to Random Behavior", "status": 408}
INFO:connector:Trying to rollback
INFO:connector:Trying to delete http://node01.app.internal.com/v1/group, data: {'groupId': '6'}, headers: {'node': 'node01', 'timestamp': '1633806862.284902'}
INFO:connector:Response <Response [404]>, {"message": "No group record found with id '6' and timestamp '1633806862.284902'", "status": 404}
```

Here we faced to the Random behavior. We got it while doing the request to the `node1`. We got 408 error. So process will switch to Rollback process, 
because we don't know (actually we know, but in real life we will not know) either the group record was created and afterwards we got 408 error or not.
So process will try to delete group record of groupId 6 from node1, and it gets 404, it means that it haven't been created.

Let's check the statistics to be sure that everything is correct

```bash
root@cf68c839f47d:/scripts# python3 job.py stats       
INFO:JOB:Running stats command for showing statistics of group records
[True, {'node01': 1, 'node02': 1, 'node03': 1}]
# NOTE one object is the group record of groupId 5 which we created above.
```

Let's try to create group record with groupId 6 again. Here we got interesting scenario and will finish explanation of creation process by this sample.

```bash
root@cf68c839f47d:/scripts# python3 job.py create-one 6
INFO:JOB:Running create-one command with groupId <6>
INFO:connector:Trying to create http://node01.app.internal.com/v1/group, data: {'groupId': '6'}, headers: {'node': 'node01', 'timestamp': '1633807521.507381'}
INFO:connector:Response <Response [201]>, CREATED

INFO:connector:Trying to create http://node02.app.internal.com/v1/group, data: {'groupId': '6'}, headers: {'node': 'node02', 'timestamp': '1633807521.542293'}
INFO:connector:Response <Response [201]>, CREATED

INFO:connector:Trying to create http://node03.app.internal.com/v1/group, data: {'groupId': '6'}, headers: {'node': 'node03', 'timestamp': '1633807521.580752'}
INFO:connector:Response <Response [408]>, {"message": "Timeout due to Random Behavior", "status": 408}
INFO:connector:Trying to rollback
INFO:connector:Trying to delete http://node01.app.internal.com/v1/group, data: {'groupId': '6'}, headers: {'node': 'node01', 'timestamp': '1633807521.507381'}
INFO:connector:Response <Response [200]>, OK

INFO:connector:Trying to rollback
INFO:connector:Trying to delete http://node01.app.internal.com/v1/group, data: {'groupId': '6'}, headers: {'node': 'node02', 'timestamp': '1633807521.542293'}
INFO:connector:Response <Response [200]>, OK

INFO:connector:Trying to rollback
INFO:connector:Trying to delete http://node01.app.internal.com/v1/group, data: {'groupId': '6'}, headers: {'node': 'node03', 'timestamp': '1633807521.580752'}
INFO:connector:Response <Response [404]>, {"message": "No group record found with id '6' and timestamp '1633807521.580752'", "status": 404}
```

Here API handles to create group record 6 in first two nodes, but it got exception during the creation in the third node.
So it entered the rollback process and deleted group records of groupId 6 from `node01` and `node02`. And while trying
to delete from the third node, it got 404.

#### Deletion process

Let's delete group record with groupId 5, which we created above.

```bash
root@cf68c839f47d:/scripts# python3 job.py delete-one 5
INFO:JOB:Running delete-one command with groupId <5>
INFO:connector:Checking existence of group with groupId: 5, node: node01, status_code: 200, response: {"groupId":"5"}

INFO:connector:Trying to delete http://node01.app.internal.com/v1/group, data: {'groupId': '5'}, headers: {'node': 'node01'}
INFO:connector:Response <Response [200]>, OK

INFO:connector:Checking existence of group with groupId: 5, node: node02, status_code: 200, response: {"groupId":"5"}

INFO:connector:Trying to delete http://node02.app.internal.com/v1/group, data: {'groupId': '5'}, headers: {'node': 'node02'}
INFO:connector:Response <Response [200]>, OK

INFO:connector:Checking existence of group with groupId: 5, node: node03, status_code: 500, response: {"message": "InternalServerError due to Random Behavior", "status": 500}
INFO:connector:Checking existence of group with groupId: 5, node: node03, status_code: 500, response: {"message": "InternalServerError due to Random Behavior", "status": 500}
INFO:connector:Checking existence of group with groupId: 5, node: node03, status_code: 200, response: {"groupId":"5"}

INFO:connector:Trying to delete http://node03.app.internal.com/v1/group, data: {'groupId': '5'}, headers: {'node': 'node03'}
INFO:connector:Response <Response [200]>, OK
```

In this sample, we successfully deleted records from the first and second nodes, but we got two 500 errors while checking 
the existence of group record in the third node, but after 200 response, which confirmed that group record of groupId 5 exists in
the third node, we successfully deleted it without errors and retries.

So out statistics shows the following
```bash
root@cf68c839f47d:/scripts# python3 job.py stats
INFO:JOB:Running stats command for showing statistics of group records
[True, {'node01': 0, 'node02': 0, 'node03': 0}]
```
So with following examples I am finishing explanation.

### Tests with parallel create and parallel delete.

I will skip logs and will past here only stats results.

After the create command (`python3 job.py create`) we got following
```bash
root@cf68c839f47d:/scripts# python3 job.py stats
INFO:JOB:Running stats command for showing statistics of group records
[True, {'node01': 52, 'node02': 52, 'node03': 52}]
```
We requested for creation of 100 groups from the range of [0-99], but Job managed to create
only 52 out of 100.

Lets run parallel delete command for deletion groups with groupIds [0-99].

After the delete command (`python3 job.py delete`) we got following
```bash
root@cf68c839f47d:/scripts# python3 job.py stats
INFO:JOB:Running stats command for showing statistics of group records
[True, {'node01': 24, 'node02': 24, 'node03': 24}]
```
So it managed to delete only 28 records out of 52.

Although my RANDOM_BEHAVIOR coefficient is 0.2 in above tests, You won't get same results when you test, because of Random behavior of the API.
But for sure Your stats' first parameter will be True. 
Actually due to retry decorator limits (max_retries=10) it could theoretically fail 10 times, but it is already the matter of configuration.
Basically we could replace decorator with infinite while loop, but it is bad practice and not always good choice, although in `check_group_exists` function 
I used while loop and wrote about it in docstring of the function.
