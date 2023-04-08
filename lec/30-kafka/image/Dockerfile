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
