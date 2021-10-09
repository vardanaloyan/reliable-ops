API documentation

`/ping/, method=["GET"] # Check connection with web application` 

```bash
root@cf68c839f47d:/scripts# curl node01.app.internal.com/ping/
PONG
```
---
`/v1/stats, method=["GET"] # Get the statistics`
```bash
root@cf68c839f47d:/scripts# curl --header "node: node01" node01.app.internal.com/v1/stats  
[true, {"node01": 24, "node02": 24, "node03": 24}]
```
---
`/v1/group/<groupId>, method=["GET"] # Get the record`
```bash
root@cf68c839f47d:/scripts# curl --header "node: node01" node01.app.internal.com/v1/group/1
{"groupId":"1"}
```

---

`/v1/group, method=["POST"] # Add the record`
```bash
root@cf68c839f47d:/scripts# curl -X POST --header "node: node01" -d '{"groupId":"2"}' node01.app.internal.com/v1/group
CREATED
```

---

`/v1/group, method=["DELETE"] # Remove the record`
```bash
root@cf68c839f47d:/scripts# curl -X DELETE --header "node: node01" -d '{"groupId":"2"}' node01.app.internal.com/v1/group
OK
```
