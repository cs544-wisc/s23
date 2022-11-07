# Project 1: Key/Value Store Service

## Overview

One of the simplest storage systems records the values associated with
keys, much like a Python `dict`, but via a service that could be
shared by code running on different computers.

In this project, you'll build a simple K/V store server that records
numbers for different string values.  You can use a Python `dict` for
this purpose, but you'll need to use threads and locking for
efficiency and safety.  A client will communicate with your server via
RPC calls.

Learning objectives:
* communicate between servers and clients via gRPC
* use locking for safety
* cache the results of expensive operations for efficiency
* measure performance statistics like cache hit rate and tail latency
* deploy your code in a Docker container

## Part 1: gRPC Interface

Read this guide for gRPC with Python:
* https://grpc.io/docs/languages/python/quickstart/
* https://grpc.io/docs/languages/python/basics/

Install the tools (be sure to upgrade pip first, as described in the directions):

```
pip3 install grpcio grpcio-tools
```

Create a file called `numstore.proto` containing a service called `NumStore`, which contains two RPCs:

1. `SetNum` takes a `key` (string) and `value` (int64) as parameters and returns a `total` (int64)
2. `Fact` takes a `key` (string) as a parameter and returns a `value` (int64), `hit` (bool), and `error` (string)

Specify `syntax="proto3";` at the top of your file.  Build it:

```
python3 -m grpc_tools.protoc -I=. --python_out=. --grpc_python_out=. numstore.proto
```

Verify `numstore_pb2.py` and `numstore_pb2_grpc.py` were generated.

## Part 2: Server Implementation

Create `server.py` file and add a class that inherits from
`numstore_pb2_grpc.NumStoreServicer` and overrides the two methods.

At the end, add a `server()` function and call it (adapting the
example from the gRPC documentation).  You can import `features` like
this:

```python
from concurrent import futures
```

Requirements:
* have 8 worker threads
* use `numstore_pb2_grpc.add_NumStoreServicer_to_server`
* use port 5440

### `SetNum(key, value)`

Your server should have a two globals variables, a `dict` of values, and in `int` that equals the sum of all the values in the `dict`.

When `SetNum(key, value)` is called, it should set `YOUR_DICTS_NAME[key] = value` and update the variable storing the total sum.  It should return the new total.

Requirement:
* don't loop over all the entries in your dict each time to update the total (instead, compare the new value to the old value to determine how the total should change)

### `Fact(key)`

This should key the value (from the global dictionary) corresponding
to that value, then it should return the factorial of that value.

The error will normally be unset, but return an error message of the
key can't be found.

### Manual testing:

So far, the following client code should produce the expected output (as indicated by the comments):

```python
import sys
import grpc
import numstore_pb2, numstore_pb2_grpc

port = "5440"
addr = f"127.0.0.1:{port}"
channel = grpc.insecure_channel(addr)
stub = numstore_pb2_grpc.NumStoreStub(channel)

# TEST SetNum
resp = stub.SetNum(numstore_pb2.SetNumRequest(key="A", value=1))
print(resp.total) # should be 1
resp = stub.SetNum(numstore_pb2.SetNumRequest(key="B", value=10))
print(resp.total) # should be 11
resp = stub.SetNum(numstore_pb2.SetNumRequest(key="A", value=5))
print(resp.total) # should be 15
resp = stub.SetNum(numstore_pb2.SetNumRequest(key="B", value=0))
print(resp.total) # should be 5

# TEST Fact
resp = stub.Fact(numstore_pb2.FactRequest(key="A"))
print(resp.value) # should be 120
```

### Caching

For large numbers, it may be slow to compute the factorial.  Add a
structure to remember previously computed answers for specific
numbers.

Requirements:
* the cache should hold a maximum of 10 entries
* write a comment specifying your eviction policy (could be random, LRU, FIFO, something you make up...)
* check the cache before doing the calculation for factorial
* in the return value, use `hit=True` or `hit=False` to indicate whether or not the cache was used for the answer

### Locking

Your server has 8 threads, so use a lock (https://docs.python.org/3/library/threading.html#threading.Lock) when accessing any global variables from `SetNum` or `Fact`.

Requirements:
* the lock should protect any access to shared structures
* the lock should always get released, even if there is an exception
* the lock should NOT be heald when factorials are being calculated

## Part 3: Client

The client should start some threads or processes that send random requests to the server.  The port of the server should be specified on the command line, like this:

```
python3 client.py 5440
```

Requirements:
* there should be 4 threads/processes
* each thread/process should send 100 random requests to the server
* for each request, randomly decide between SetNum and Fact (50/50 mix)
* for each request, randomly choose a key (from a list of 100 possible keys)
* for SetNum requests, randomly select a number between 1 and 15

The client should then print some stats at the end.

Requirements:
* print cache hit rate
* print p50 response time
* print p99 response time
* it should be clear from the prints what each output number represents

Feel free to install `numpy` if that helps with computing percentiles.

## Part 4: Docker Deployment

You should write a `Dockerfile` to build an image that runs your server.py.

Requirements:
* it should be possible to run `docker build n-t p1 .`
* it should be possible to run your server like this `docker run -p 54321:5440 p1`

## Submission

You should submit a `p1.zip` file containing your `Dockerfile`, `.py`
files, and `.proto` file.  You should also capture the output of your
client.py program from when you ran it in an `out.txt` file that
should be included in your zip.

We should be able to look at your submission like this (test your zip in an empty directory):

```
unzip p1.zip
docker build -t p1 .
docker run -d -p 54321:5440 p1
python3 client.py 54321
cat out.txt
```
