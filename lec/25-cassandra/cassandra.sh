echo "-Xms128M" >> /apache-cassandra-4.0.7/conf/jvm-server.options
echo "-Xmx128M" >> /apache-cassandra-4.0.7/conf/jvm-server.options

sed -i "s/^listen_address:.*/listen_address: "`hostname`"/" /apache-cassandra-4.0.7/conf/cassandra.yaml
sed -i "s/^rpc_address:.*/rpc_address: "`hostname`"/" /apache-cassandra-4.0.7/conf/cassandra.yaml
sed -i "s/- seeds:.*/- seeds: 25-cassandra-db-1,25-cassandra-db-2,25-cassandra-db-3/" /apache-cassandra-4.0.7/conf/cassandra.yaml

/apache-cassandra-4.0.7/bin/cassandra -R

sleep infinity
