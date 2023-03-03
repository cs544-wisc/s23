FROM ubuntu:22.04
RUN apt-get update; apt-get install -y wget curl openjdk-11-jdk python3-pip net-tools lsof nano
RUN pip3 install jupyterlab==3.4.5 MarkupSafe==2.0.1 pandas

# HDFS
RUN wget https://pages.cs.wisc.edu/~harter/cs639/hadoop-3.2.4.tar.gz; tar -xf hadoop-3.2.4.tar.gz; rm hadoop-3.2.4.tar.gz

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH="${PATH}:/hadoop-3.2.4/bin"
