# Container Setup

## Dockerfile

```
FROM ubuntu:22.04
RUN apt-get update; apt-get install -y wget curl openjdk-8-jdk python3-pip net-tools lsof nano unzip
RUN pip3 install jupyterlab==3.4.5 MarkupSafe==2.0.1 cassandra-driver pyspark==3.2.2 pandas matplotlib

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
    main:
        image: p4-image
        ports:
        - "127.0.0.1:5000:5000"
        - "127.0.0.1:4040:4040"
        volumes:
        - "./nb:/notebooks"
        - "./main.sh:/start.sh"

    worker:
        image: p4-image
        deploy:
            replicas: 2
        volumes:
        - "./worker.sh:/start.sh"
```

## main.sh

```
./spark-3.2.2-bin-hadoop3.2/sbin/start-master.sh

hdfs namenode -format -force
hdfs namenode -D dfs.webhdfs.enabled=true -D dfs.replication=1 -fs hdfs://main:9000 &> /var/log/namenode.log &
hdfs datanode -D dfs.datanode.data.dir=/var/datanode -fs hdfs://main:9000 &> /var/log/datanode.log &

cd /notebooks
python3 -m jupyterlab --no-browser --ip=0.0.0.0 --port=5000 --allow-root --NotebookApp.token=''
```

## worker.sh

```
./spark-3.2.2-bin-hadoop3.2/sbin/start-worker.sh spark://main:7077 -c 1 -m 512M
tail -f /spark-3.2.2-bin-hadoop3.2/logs/*.out
```