# DRAFT!  Don't start yet.

# P3 (4% of grade): HDFS Replication

## Overview

HDFS can *partition* large files into blocks to share the storage
across many workers, and it can *replicate* those blocks so that data
is not lost even if some workers die.

In this project, you'll deploy a small HDFS cluster and upload a large
file to it, with different replication settings.  You'll write Python
code to read the file.  When data is partially lost (due to a node
failing), your code will recover as much data as possible from the
damaged file.

Learning objectives:
* use the HDFS command line client to upload files
* use the webhdfs API (https://hadoop.apache.org/docs/r1.0.4/webhdfs.html) to read files
* measure the impact buffering has on read performance
* relate replication count to space efficiency and fault tolerance

Before starting, please review the [general project directions](../projects.md).

## Corrections/Clarifications

* none yet

## Part 1: HDFS Deployment and Data Upload

For this project, you'll create three containers, each from the same
base image (`p3-base`).  Create a directory called `image` that
contains a `Dockerfile` with the following:

```
FROM ubuntu:22.04
RUN apt-get update; apt-get install -y wget curl openjdk-11-jdk python3-pip net-tools lsof nano
RUN pip3 install jupyterlab==3.4.5 MarkupSafe==2.0.1 pandas

# HDFS
RUN wget https://pages.cs.wisc.edu/~harter/cs639/hadoop-3.2.4.tar.gz; tar -xf hadoop-3.2.4.tar.gz; rm hadoop-3.2.4.tar.gz

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH="${PATH}:/hadoop-3.2.4/bin"

CMD ["sh", "/start.sh"]
```

Build it with `docker build -t p3-image ./image`.

Now, create a `docker-compose.yml` that starts your three containers.  You can use the following as a starting point:

```
services:
    main:
        image: p3-image
        ports:
        - "127.0.0.1:5000:5000"
        volumes:
        - "./nb:/notebooks"
        - "./main.sh:/start.sh"

    # worker:
    # TODO: create 2 replicas running the worker

networks:
    default:
        name: cs544net
        driver: bridge
```

Even though all three containers have the same image, they will do
different things because `/start.sh` is the ENTRYPOINT, and you'll map
in different scripts to run startup code (`main.sh` for the main
service, and whatever you call it for the worker service).

The `main` service should do three things:

1. format an HDFS file system
2. start an HDFS Namenode
3. start a Jupyter notebook

The `worker` service should just start a datanode.

**Note:** in this project, you will run your JupyterLab server inside
  a container; you can use the web interface and SSH tunneling for
  development.  We're using this approach because then your code can
  run in the cs544net and easily communicate with the HDFS processes.
  Even if you normally use VSCode, it will be difficult to do so for
  this project (unless you can find a way to use it to connect to the
  container -- the 544 team does not know a way).

Here are some example commands that you can use for inspiration when
writing your .sh files (you'll probably need to modify them):

* `hdfs namenode -format`
* `hdfs namenode -D dfs.namenode.stale.datanode.interval=10000 -D dfs.namenode.heartbeat.recheck-interval=30000 -fs ????`
* `python3 -m jupyterlab --no-browser --ip=0.0.0.0 --port=???? --allow-root --NotebookApp.token=''`
* `hdfs datanode -D dfs.datanode.data.dir=/var/datanode -fs ????`

Hints:

* HDFS formatting sometimes prompts you if you want to overwrite the previous file system.  You can pass `-force` to make it do so without prompting (useful since this is scripted instead of done manually)
* note how the namenode is configured with a couple `-D` options.  You should also have `dfs.webhdfs.enabled` be `true`
* for the `-fs`, you can pass something like `hdfs://SERVER:PORT`.  Use port `9000` and `main` for the server name (matching the Docker service name).
* we want to access Jupyter from outside the container, so when setting the port number, review our port forwarding options from the compose file
* the namenode and Jupyter both run in the foreground by default, so whichever one that runs first will block the other from starting. You will need to send one of them to the background. 

You can use `docker compose up` to start your mini cluster of three containers.  Some docker commands that might be helpful for debugging:

* `docker compose ps -a` to see what containers are running or exited
* `docker logs <CONTAINER NAME>` to see the output of a container
* `docker exec -it <CONTAINER NAME> bash` to get shell inside the container
* `docker compose kill; docker compose rm -f` to get a fresh start

The last command above stops and deletes all the containers in your
cluster.  For simplicity, we recommend this rather than restarting a
single container when you need to change something as it avoids some
tricky issues with HDFS.  For example, if you just restart+reformat
the container with the NameNode, the old DataNodes will not work with
the new NameNode without a more complicated process/config.

If all is well, you should be to connect to Jupyter inside the the
main container and create a notebook called `p3.ipynb` where you'll do
the rest of your work.  You can run `!CMD` inside a cell to run `CMD`
as a shell command.  Use this approach to show both your shell and
Python work for this project.

Note that each line under the `volumes` section in `docker-compose.yml` takes the form of `<path on host>:<path in container>`. This tells the container to directly map certain files / folders from the host machine to inside the container so that when you change its content from inside the container, the changes will show up in the path on the host machine. This is how you ensure that `p3.ipynb` does not get lost even if you removes the container running Jupyter. 

Use a shell command in your notebook to download
https://pages.cs.wisc.edu/~harter/cs639/data/hdma-wi-2021.csv.  Next,
use two `hdfs dfs -cp` commands to upload this same file to HDFS
twice, to the following locations:

* `hdfs://main:9000/single.csv`
* `hdfs://main:9000/double.csv`

In both cases, use a 1MB block size (`dfs.block.size`), and
replication (`dfs.replication`) of 1 and 2 for `single.csv` and
`double.csv`, respectively.

Double check the sizes of the two files with the following commands:

```
hdfs dfs -du -h hdfs://main:9000/
```

You should see something like this:

```
166.8 M  333.7 M  hdfs://main:9000/double.csv
166.8 M  166.8 M  hdfs://main:9000/single.csv
```

The first columns show the logical and physical sizes.  The two CSVs
contain the same data, so the have the same logical sizes.  Note the
difference in physical size due to replication, though.

## Part 2: Block Locations

If you correctly configured the block size, single.csv should have 167
blocks, some of which will be stored on each of your two Datanodes.
Your job is to write some Python code to count how many blocks are
stored on each worker by using the webhdfs interface.

Read about the `OPEN` call here:
https://hadoop.apache.org/docs/r1.0.4/webhdfs.html#OPEN.

Adapt the curl examples to use `requests.get` in Python instead.  Your URLs will be like this:

```
http://main:9870/webhdfs/v1/single.csv?op=OPEN&offset=????
```

Note that `main:9870` is the Namenode, which will reply with a
redirection response that sends you to a Datanode for the actual data.

If you pass `allow_redirects=False` to `requests.get` and look at the
`.headers` of the Namenode's repsonse, you will be able to infer which
Datanode stores that data corresponding to a specific offset in the
file.  Loop over offsets corresponding to the start of each block
(your blocksize is 1MB, so the offsets will be 0, 1MB, 2MB, etc).

Construct and print a dictionary like the following that shows how
many blocks of `single.csv` are on each Datanode:

```
{'http://70d2c4b6ccee:9864/webhdfs/v1/single.csv': 92,
 'http://890e8d910f92:9864/webhdfs/v1/single.csv': 75}
```

Your data will probably be distributed differently between the two,
and you will almost certainly have container names that are different
than `70d2c4b6ccee` and `890e8d910f92`.

## Part 3: Reading the Data

In this part, you'll make a new reader class that makes it easy to
loop over the lines in an HDFS file.

You'll do this by inheriting from the `io.RawIOBase` class: https://docs.python.org/3/library/io.html#class-hierarchy.  Here is some starter code:

```python
import io

class hdfsFile(io.RawIOBase):
    def __init__(self, path):
        self.path = path
        self.offset = 0
        self.length = 0 # TODO

    def readable(self):
        return True

    def readinto(self, b):
        return 0 # TODO
```

In the end, somebody should be able to loop over the lines in an HDFS file like this:

```python
for line in io.BufferedReader(hdfsFile("single.csv")):
    line = str(line, "utf-8")
    print(line)
```

Implementation:

* use `GETFILESTATUS` (https://hadoop.apache.org/docs/r1.0.4/webhdfs.html#GETFILESTATUS) to correctly set `self.length` in the constructor
* whenever `readinto` is called, read some data at position `self.offset` from the HDFS file: https://hadoop.apache.org/docs/r1.0.4/webhdfs.html#OPEN
* the data you read should be put into `b`.  The type of `b` will generally be a `memoryview` which is like a fixed-size list of bytes.  You can use slices to put values here (something like `b[0:3] = b'abc'`).  Since it is fixed size, you should use `len(b)` to determine how much data to request from HDFS.
* `readinto` should return the number of bytes written into `b` -- this will usually be the `len(b)`, but not always (for example, when you get to the end of the HDFS file), so base it on how much data you get from webhdfs.
* before returning from `readinto`, increase `self.offset` so that the next read picks up where the previous one left off
* if `self.offset >= self.length`, you know you're at the end of the file, so `readinto` should return 0 without calling to webhdfs

Use your class to loop over every line of single.csv.

Count how many lines contain the text "Single Family" and how many contain "Multifamily".  Print out your counts like the following:

```
Counts from single.csv
Single Family: 444874
Multi Family: 2493
Seconds: 24.33926248550415
```

Note that by default `io.BufferedReader` uses 8KB for buffering, which
creates many small reads to HDFS, so your code will be unreasonably
slow.  Experiment with passing `buffer_size=????` to use a larger
buffer.

Your code should show at least two different sizes you tried (and the
resulting times).

## Part 4: Disaster Strikes

You have two datanodes.  What do you think will happen to `single.csv`
and `double.csv` if one of these nodes dies?

Find out by manually running a `docker kill <CONTAINER NAME>` command
on your VM to abruptly stop one of the Datanodes.

Wait until the Namenode realizes the Datanode has died before proceeding.  Run `!hdfs dfsadmin -fs hdfs://main:9000/ -report`
in your notebook to see when this happens.  Before proceeding, the report should show one dead Datanode, something
like the following:

<details>
<summary>Expand</summary>
<pre>
Configured Capacity: 83111043072 (77.40 GB)
Present Capacity: 25509035132 (23.76 GB)
DFS Remaining: 24980049920 (23.26 GB)
DFS Used: 528985212 (504.48 MB)
DFS Used%: 2.07%
Replicated Blocks:
	Under replicated blocks: 0
	Blocks with corrupt replicas: 0
	Missing blocks: 0
	Missing blocks (with replication factor 1): 0
	Low redundancy blocks with highest priority to recover: 0
	Pending deletion blocks: 0
Erasure Coded Block Groups: 
	Low redundancy block groups: 0
	Block groups with corrupt internal blocks: 0
	Missing block groups: 0
	Low redundancy blocks with highest priority to recover: 0
	Pending deletion blocks: 0

Live datanodes (1):

Name: 172.19.0.4:9866 (spark-lecture-worker-1.cs544net)
Hostname: 890e8d910f92
Decommission Status : Normal
Configured Capacity: 41555521536 (38.70 GB)
DFS Used: 255594721 (243.75 MB)
Non DFS Used: 28793143071 (26.82 GB)
DFS Remaining: 12490006528 (11.63 GB)
DFS Used%: 0.62%
DFS Remaining%: 30.06%
Configured Cache Capacity: 0 (0 B)
Cache Used: 0 (0 B)
Cache Remaining: 0 (0 B)
Cache Used%: 100.00%
Cache Remaining%: 0.00%
Xceivers: 1
Last contact: Sat Dec 31 20:07:46 GMT 2022
Last Block Report: Sat Dec 31 20:04:00 GMT 2022
Num of Blocks: 242

Dead datanodes (1):

Name: 172.19.0.3:9866 (172.19.0.3)
Hostname: 70d2c4b6ccee
Decommission Status : Normal
Configured Capacity: 41555521536 (38.70 GB)
DFS Used: 273390491 (260.73 MB)
Non DFS Used: 28775310437 (26.80 GB)
DFS Remaining: 12490043392 (11.63 GB)
DFS Used%: 0.66%
DFS Remaining%: 30.06%
Configured Cache Capacity: 0 (0 B)
Cache Used: 0 (0 B)
Cache Remaining: 0 (0 B)
Cache Used%: 100.00%
Cache Remaining%: 0.00%
Xceivers: 1
Last contact: Sat Dec 31 20:06:15 GMT 2022
Last Block Report: Sat Dec 31 20:04:00 GMT 2022
Num of Blocks: 259
</pre>
</details>

Note that HDFS datanodes use heartbeats to inform the namenode of its liveness. That is, the datanodes send a small dummy message (heartbeat) periodically (every 3 seconds by default) to inform the namenode of its presence. Recall that when we start the namenode, we specify `dfs.namenode.stale.datanode.interval=10000` and `dfs.namenode.heartbeat.recheck-interval=30000`. The first says that the namenode considers the datanode stale if it does not receive its heartbeat for 10 seconds (10000 ms) and the second says that it will consider the datanode dead after another 30 seconds. Hence, if you configure your cluster correctly, the namenode will become aware of the loss of datanode within 40 seconds after you killed the datanode. 

Run your code from part 3 again that counts the multi and single
family dwellings in new cells.  Do so on both double.csv and
single.csv.

double.csv should work just like before.  You will have lost some
blocks from single.csv, but modify `readinto` in your `hdfsFile` class
so that it still returns as much data as possible.  If reading a block
from webhdfs fails, `readinto` should do the following:

1. put `\n` into the `b` buffer
2. move `self.offset` forward to the start of the next block
3. return 1 (because `\n` is a single character)

You should get some prints like this:

```
Counts from double.csv
Single Family: 444874
Multi Family: 2493
```

AND

```
Counts from single.csv
Single: 200608
Multi: 929
```

Observe that we're still getting some lines from single.csv, but only
about half as many as before the data loss (exact counts will depend
on how many blocks each datanode was storing).

## Submission

We should be able to run the following on your submission to create the mini cluster:

```
docker build -t p3-image ./image
docker compose up
```

We should then be able to open `http://localhost:5000/lab`, find your
notebook, and run it.

## Approximate Rubric:

The following is approximately how we will grade, but we may make
changes if we overlooked an important part of the specification or did
not consider a common mistake.

1. [x/1] a `Dockerfile` and `docker-compose.yml` can be used to deploy the cluster (part 1)
2. [x/1] `dfs` cp and du commands create (and show) single.csv and double.csv with the correct block size and replication settings (part 1)
3. [x/1] a dict shows the division of blocks between the two Datanodes (part 2)
4. [x/1] `__init__` correctly uses webhdfs `GETFILESTATUS` to get the file length (part 3)
5. [x/1] `readinto` correctly uses webhdfs `OPEN` to get a chunk of the file (part 3)
6. [x/1] the correct single and multi family counts are computed and printed (part 3)
7. [x/1] two different buffer sizes are evaluated with `io.BufferedReader` (part 3)
8. [x/1] the `-report` command shows that one Datanode is alive and one is dead (part 4)
9. [x/1] `readinto` correctly replaces missing blocks with a single newline (part 4)
10. [x/1] counts are correctly shown for both single.csv and double.csv (part 4)
