API Consumer

`docker-compose -f docker-compose.yml build`

`docker-compose -f docker-compose.yml up -d`

`docker exec -it node_node1_1 bash`

`cd /scripts/`

`bash start_nginx.sh`

`curl node01.app.internal.com/ping/`

curl --header "node: node01" node01.app.internal.com/v1/group/1


`curl -X POST --header "node: node01" -d '{"groupId":"1"}' node01.app.internal.com/v1/group`

`python3 job.py`

curl 127.0.0.1:8080/stats 

curl -X DELETE --header "node: node01" -d '{"groupId":"106"}' http://127.0.0.1:8080/group

curl -H "node: node02" 127.0.0.1:8080/group/1
