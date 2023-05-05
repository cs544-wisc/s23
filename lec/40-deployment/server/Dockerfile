FROM ubuntu:22.04
RUN apt-get update; apt-get install -y wget curl python3-pip
RUN pip3 install jupyterlab==3.4.5
COPY server.sh /server.sh
CMD ["sh", "server.sh"]
