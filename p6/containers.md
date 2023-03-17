# Container Setup

## Dockerfile

Build the following to get a `p6` image:

```
FROM ubuntu:22.04
RUN apt-get update; apt-get install -y wget curl openjdk-8-jdk python3-pip net-tools lsof nano unzip
RUN pip3 install jupyterlab==3.4.5 MarkupSafe==2.0.1 cassandra-driver pyspark==3.2.2 pandas matplotlib kafka-python grpcio-tools

# HDFS
RUN wget https://pages.cs.wisc.edu/~harter/cs639/hadoop-3.2.4.tar.gz; tar -xf hadoop-3.2.4.tar.gz; rm hadoop-3.2.4.tar.gz

# SPARK
RUN wget https://pages.cs.wisc.edu/~harter/cs639/spark-3.2.2-bin-hadoop3.2.tgz; tar -xf spark-3.2.2-bin-hadoop3.2.tgz; rm spark-3.2.2-bin-hadoop3.2.tgz

ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
ENV PATH="${PATH}:/hadoop-3.2.4/bin:/spark-3.2.2-bin-hadoop3.2/bin"

CMD ["sh", "/start.sh"]
```

## docker-compose.yml

```
services:
  app:
    image: p6
    ports:
    - "127.0.0.1:5000:5000"
    - "127.0.0.1:4040:4040"
    volumes:
    - "./nb:/notebooks"
    entrypoint: ["python3", "-m", "jupyterlab", "--no-browser", "--ip=0.0.0.0", "--port=5000", "--allow-root", "--NotebookApp.token=''"]

  # adapted from here: https://github.com/confluentinc/kafka-images/blob/master/examples/kafka-single-node/docker-compose.yml
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
```
