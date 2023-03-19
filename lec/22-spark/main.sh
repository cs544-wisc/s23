./spark-3.2.2-bin-hadoop3.2/sbin/start-master.sh

hdfs namenode -format -force
hdfs namenode -D dfs.webhdfs.enabled=true -D dfs.replication=1 -fs hdfs://main:9000 &> /var/log/namenode.log &
hdfs datanode -D dfs.datanode.data.dir=/var/datanode -fs hdfs://main:9000 &> /var/log/datanode.log &

cd /notebooks
python3 -m jupyterlab --no-browser --ip=0.0.0.0 --port=5000 --allow-root --NotebookApp.token=''
