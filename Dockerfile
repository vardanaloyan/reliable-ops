FROM ubuntu/nginx
COPY ./cluster /app
RUN apt-get update
RUN apt-get install -y python3 python3-pip inetutils-ping curl
RUN pip install -r /app/requirements.txt
WORKDIR /app
EXPOSE 8080