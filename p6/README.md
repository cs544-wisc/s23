# DRAFT!  Don't start yet.

# P6 (8% of grade): Kafka and Spark Streaming, Weather Data

## Overview

For this project, imagine a scenario where many weather stations are
sending daily records to a Kafka stream.  A regular Python program
consumes the stream to produce JSON files with summary stats for each
station, for use on a web dashboard (you don't need to build the
dashboard yourself).  A Spark streaming job also consumes the streams
to generate datasets for machine learning (the goal being to predict
weather).  Spark is also used to train models on this data.

In this scenario, many computers would be involved (different
stations, many Kafka brokers, etc).  For simplicity, we'll use a
single Kafka broker.  A single producer will generate data for all
stations at an accelerated rate (1 day per second).  Finally,
consumers will be different threads, launching from the same notebook.

Learning objectives:
* write code for Kafka producers
* write code for Kafka consumers
* apply streaming techniques to achive "exactly once" semantics
* use Spark streaming to consumer and transform data from Kafka
* use Spark to train models

Before starting, please review the [general project directions](../projects.md).

## Clarifications/Correction

* none yet

## Part 1: Kafka Producer

Using Docker compose, launch a cluster with Jupyter, HDFS, Spark, and
Kafka. Here are some files that could help: [Container Setup
Files](./containers.md).

Start two notebooks called `kafka.ipynb` (parts 1 and 2) and
`spark.ipynb` (parts 3 and 4) inside the "notebooks" directory within
the "app" container.

Paste the following helper code that generates random weather for a
given number of stations (it's not completely random -- there are
seasonal and day-to-day patterns unique to each station):

```python
import datetime, time, random, string

def one_station(name):
    # temp pattern
    month_avg = [27,31,44,58,70,79,83,81,74,61,46,32]
    shift = (random.random()-0.5) * 30
    month_avg = [m + shift + (random.random()-0.5) * 5 for m in month_avg]
    
    # rain pattern
    start_rain = [0.1,0.1,0.3,0.5,0.4,0.2,0.2,0.1,0.2,0.2,0.2,0.1]
    shift = (random.random()-0.5) * 0.1
    start_rain = [r + shift + (random.random() - 0.5) * 0.2 for r in start_rain]
    stop_rain = 0.2 + random.random() * 0.2

    # day's state
    today = datetime.date(2000, 1, 1)
    temp = month_avg[0]
    raining = False
    
    # gen weather
    while True:
        # choose temp+rain
        month = today.month - 1
        temp = temp * 0.8 + month_avg[month] * 0.2 + (random.random()-0.5) * 20
        if temp < 32:
            raining=False
        elif raining and random.random() < stop_rain:
            raining = False
        elif not raining and random.random() < start_rain[month]:
            raining = True

        yield (today, name, temp, raining)

        # next day
        today += datetime.timedelta(days=1)
        
def all_stations(count=10, sleep_sec=1):
    assert count <= 26
    stations = []
    for name in string.ascii_uppercase[:count]:
        stations.append(one_station(name))
    while True:
        for station in stations:
            yield next(station)
        time.sleep(sleep_sec)
```

Try getting data from it to see how it works:

```python
# loops forever because the weather never ends...
for row in all_stations(3):
    print(row) # date, station, temp, raining
```

Now paste the following to create two streams, each with 6 partitions and a replication factor of 1:

```python
from kafka import KafkaAdminClient, KafkaProducer, KafkaConsumer, TopicPartition
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError, UnknownTopicOrPartitionError

admin = KafkaAdminClient(bootstrap_servers=["kafka:9092"])
try:
    admin.delete_topics(["stations", "stations-json"])
    print("deleted")
except UnknownTopicOrPartitionError:
    print("cannot delete (may not exist yet)")

time.sleep(1)
admin.create_topics([NewTopic("stations", 6, 1)])
admin.create_topics([NewTopic("stations-json", 6, 1)])
admin.list_topics()
```

You'll write a produce to send the same data to both streams, but the first will be in protobuf format and the second will be in JSON.

Create a protobuf file with a `Report` message having the following entries, and build it to get a ???_pb2.py file:

* string date (format "YYYY-MM-DD")
* string station
* double degrees
* bool raining

The JSON format will similarly have four keys -- the biggest difference is that we'll use ints (1 or 0) instead of a boolean to indicate rain:

* "date" (format should be "YYYY-MM-DD")
* "station"
* "degrees"
* "raining" (use 1 for raining or 0 for not raining)

Write a function that loops forever over the weather for 15 stations,
sending the data to the two streams.  You could use this for a starter:

```python
def produce():
    producer = KafkaProducer(bootstrap_servers=["kafka:9092"], ????)
    
    for date, station, degrees, raining in all_stations(15):
        # TODO: send to "stations" stream using protobuf
        # TODO: send to "stations-json" using JSON

# TODO: start thread to run produce
# never join thread because we want it to run forever
```


Other requirements:
1. producer: use a setting so that the producer retries up to 10 times when `send` requests fail
2. producer: use a setting so that `send` calls are not acknowledged until all in-sync replicas have received the data
3. stations stream: use a `.SerializeToString()` call to convert a protobuf object to bytes (not a string, despite the name)
4. stations-json stream: use `json.dumps` to convert a dict to a string and `bytes(???, "utf-8")` to convert a string to bytes
5. both streams: use a `key=` argument when sending data.  The key should be a byte representation of the station name

## Part 2: Kafka Consumer

Now, you'll run 3 consumer threads to process the data from the
"stations" stream.  These consumers will generate JSON files
summarizing temperature data for the stations.

Overview:
* there are 15 stations but only 6 partitions, so naturally some partitions will correspond to multiple stations
* there are 6 partitions and only 3 consumer threads, so each thread will consumer exactly 2 partitions (you'll manually assign this as partitions 0+1 for the first thread, 2+3 for the second, and 4+5 for the third)
* each partition will correspond to one file named "partition-N.json" (where N is the partition number)
* the above point means each thread will be in charge of keeping two JSON files updated

This is an example of a JSON file corresponding to a partition (due to a several factors you'll probably never see this exact data):

```python
{
  "N": {
    "avg": 32.49171033949124,
    "count": 134,
    "end": "2000-05-13",
    "start": "2000-01-01",
    "sum": 4353.8891854918265
  },
  "offset": 134,
  "partition": 0
}{
  "E": {
    "avg": 28.718693603059087,
    "count": 134,
    "end": "2000-05-13",
    "start": "2000-01-01",
    "sum": 3848.3049428099175
  },
  "O": {
    "avg": 34.1969656334807,
    "count": 134,
    "end": "2000-05-13",
    "start": "2000-01-01",
    "sum": 4582.393394886414
  },
  "offset": 268,
  "partition": 1
}{
  "F": {
    "avg": 31.047916671797324,
    "count": 136,
    "end": "2000-05-15",
    "start": "2000-01-01",
    "sum": 4222.516667364436
  },
  "I": {
    "avg": 24.628561218065123,
    "count": 136,
    "end": "2000-05-15",
    "start": "2000-01-01",
    "sum": 3349.4843256568565
  },
  "J": {
    "avg": 54.70145603439249,
    "count": 136,
    "end": "2000-05-15",
    "start": "2000-01-01",
    "sum": 7439.3980206773795
  },
  "offset": 408,
  "partition": 2
}{
  "D": {
    "avg": 45.98143392631751,
    "count": 136,
    "end": "2000-05-15",
    "start": "2000-01-01",
    "sum": 6253.475013979181
  },
  "G": {
    "avg": 39.21380621866297,
    "count": 136,
    "end": "2000-05-15",
    "start": "2000-01-01",
    "sum": 5333.0776457381635
  },
  "M": {
    "avg": 30.725245508290406,
    "count": 136,
    "end": "2000-05-15",
    "start": "2000-01-01",
    "sum": 4178.633389127495
  },
  "offset": 408,
  "partition": 3
}{
  "A": {
    "avg": 39.85364068931509,
    "count": 135,
    "end": "2000-05-14",
    "start": "2000-01-01",
    "sum": 5380.241493057538
  },
  "B": {
    "avg": 30.92598242945998,
    "count": 135,
    "end": "2000-05-14",
    "start": "2000-01-01",
    "sum": 4175.007627977097
  },
  "C": {
    "avg": 58.29112489542931,
    "count": 135,
    "end": "2000-05-14",
    "start": "2000-01-01",
    "sum": 7869.301860882957
  },
  "K": {
    "avg": 34.70506723549445,
    "count": 135,
    "end": "2000-05-14",
    "start": "2000-01-01",
    "sum": 4685.18407679175
  },
  "L": {
    "avg": 49.345066289742846,
    "count": 135,
    "end": "2000-05-14",
    "start": "2000-01-01",
    "sum": 6661.583949115284
  },
  "offset": 675,
  "partition": 4
}{
  "H": {
    "avg": 34.792595639350694,
    "count": 135,
    "end": "2000-05-14",
    "start": "2000-01-01",
    "sum": 4697.000411312343
  },
  "offset": 135,
  "partition": 5
}
```

The dict in the JSON file should have the following keys at the top level:
* "partition": the partition number in the `stations` stream, from which the stats were computed
* "offset": the partition offset to which the consumer read to produce this file
* stations: a key for each station in the partition (in this case, stations "E" and "O")

Each station key has a corresponding dict value with the following entries:
* "sum": sum of temperatures seen so far (yes, this is an odd metric by itself)
* "count": the number of temperatures seen so far
* "avg": the sum/count.  This is the only reason we record the sum -- so we can recompute the average on a running basis without having to remember and loop over all temperatures each time the file is updated
* "start": the date of the first measurement ("YYYY-MM-DD")
* "end": the date of the most recent measurement ("YYYY-MM-DD")

Paste the following cell in your notebook so that everytime we re-run
the notebook, we'll be starting from the same situation (no prior JSON
files).

```python
import os, json

for partition in range(6):
    path = f"partition-{partition}.json"
    if os.path.exists(path):
        os.remove(path)
```

You can use the following starter code for your consumers:

```python
def consume(part_nums=[], iterations=10):
    consumer = ????
    # TODO: create list of TopicPartition objects
    consumer.assign(????)

    # PART 1: initialization
    partitions = {} # key=partition, value=snapshot dict
    # TODO: load partitions from JSON files (if they exist) or create fresh dicts
    # TODO: if offsets were specified in previous JSON files, the consumer
    #       should seek to those; else, seek to offset 0.

    # PART 2: process batches
    for i in range(iterations):
        batch = consumer.poll(1000) # 1s timeout
        for topic, messages in batch.items():
            # perhaps create a separate function for the following?  You decide.
            # TODO: update the partitions based on new messages
            # TODO: save the data back to the JSON file
    print("exiting")

for i in range(2):
    print("ROUND", i)
    t1 = threading.Thread(target=consume, args=([0,1], 30))
    t2 = threading.Thread(target=consume, args=([2,3], 30))
    t3 = threading.Thread(target=consume, args=([4,5], 30))
    t1.start()
    t2.start()
    t3.start()
    t1.join()
    t2.join()
    t3.join()
```

Note that instead of `for i in range(iterations)`, you would
typically have an infinite loop (like `while True`).  For the sake of
assigment simplicity, we just iterate 30 times (so you don't need to
keep restarting your whole notebook to kill+restart the consumer
threads after code changes).

Note that we also do 2 rounds of the 30 iterations.  The point here is
to practice writing your consumers so that if they die and get
restarted, the new consumers can pickup where the previous ones left
off, while avoiding both these problems:

* missing some messages
* double counting some messages

At the end, put the following in a cell so we can see the snapshots
produced by the consumers:

```
!cat partition*.json
```

### Required: Exactly-Once Kafka Messages

Unless the producer repeatedly fails to write a message, each
message/measurement should be counted exactly once in the output stats.

To avoid **undercounting**:
* the producer must use an ackowledgement option so that `send` is not considered successful until all in-sync replicas have received the data
* the produce must use an option to retry up to 10 times upon failure to receive such a message

To avoid **overcounting**:
* when a consumer updates a JSON file, it must record the current read offset in the file (you can get this with `consumer.position(???)`)
* when a new consumer starts, it must start reading from the last offset (you can do this with `consumer.seek(????)`)
* when a consumer reads a message, it should ignore it if the date is <= the previous date processed (the "end" entry in the station dict will help with this).  Remember that producers retry when they don't get an ack, but it's possible for an ack to be lost after a successful write.  So retry could produce duplicates in the stream

### Optional: Atomic File Writes

Remember that we're producing the JSON files so somebody else (not
you) can use them to build a web dashboard.  What if the dashboard app
tries to read the JSON file at the same time your consumer is updating
the file?  It's possible the dashboard app could read an
incomprehensible mix of old and new data.

You are NOT required to handle this situation for this project.
However, if you want to do it right, the proper technique is to write
a new version of the data to a different file.  For example, say the
original file is "F.txt" -- you might write the new version to
"F.txt.tmp".  After the new data has been completely written, you can
rename F.txt.tmp to F.txt.  This atomically replaces the file
contents.  Anybody trying to read it will see all old data or all new
data.

```python
path = ????
path2 = path + ".tmp"
with open(path2, "w") as f:
    # TODO: write the data
    os.rename(path2, path)
```

Note that this only provides atomicity when the system doesn't crash.
If the computer crashes and restarts, it's possible some of the writes
for the new file might only have been buffered in memory, not yet
written to the storage device.  Feel free to read about `fsync` if
you're curious about this scenario.

## Part 3: Spark Streaming

Remember that part 3 and 4 are in a new notebook, `spark.ipynb`.  It
is important that you leave `kafka.ipynb` running during this work,
though.

Start a local Spark session like this:

```python
from pyspark.sql import SparkSession
spark = (SparkSession.builder.appName("cs544")
         .config("spark.sql.shuffle.partitions", 10)
         .config("spark.ui.showConsoleProgress", False)
         .config('spark.jars.packages', 'org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.2')
         .getOrCreate())
```

Note that we're disabling the progress bar.  While usually convenient,
we'll have streams running indefinitely in the background, and we
don't want constant output to Jupyter.

Use a `spark.readStream` to load the `stations-json` stream to a DataFrame.  Tips:

* the `value` comments will contain the bytes you wrote.  You can use `col(????).cast("string")` to convert bytes to a string (this assumes UTF-8 encoding)
* you can convert a JSON string to a structure using `from_json(????, schema)`.  The schema needs to specify the types.  It will be something like `schema = "station STRING, date DATE, ..."` for you.
* if a column named "value" is a struct, you can access an entry named "station" inside with "value.station"

Requirements
* use `.option("startingOffsets","earliest")` to begin with the earliest data
* in addition to the columns of actual data you recorded, include the "timestamp" column, and configure a 10 minute watermark on that column.

## Stats

Write some Spark code to compute the following stats per station:
* station name
* date of first measurement
* date of most recent measurement
* number of measurements
* average temperature so far
* max temperature so far

Stream these stats to the console every 5 seconds for a total of 30 seconds.  You can use this starter code:

```python
counts_df = ????
s = counts_df.writeStream.format("console").trigger(processingTime="5 seconds").outputMode("complete").start()
s.awaitTermination(30)
s.stop()
```

The output should be something like this:

```
-------------------------------------------
Batch: 0
-------------------------------------------
+-------+----------+----------+------------+------------------+----------+
|station|     start|       end|measurements|               avg|       max|
+-------+----------+----------+------------+------------------+----------+
|      A|2000-01-01|2014-01-28|        5142| 53.42402521596634| 107.04456|
|      B|2000-01-01|2014-01-28|        5142| 43.03918192489779|  95.67471|
|      C|2000-01-01|2014-01-28|        5142| 70.89881298654231| 124.12265|
|      D|2000-01-01|2014-01-28|        5142| 60.29500058855541| 113.63003|
|      E|2000-01-01|2014-01-28|        5142| 46.85979942859048| 99.760445|
|      F|2000-01-01|2014-01-28|        5142| 47.59281675032445|101.321434|
|      G|2000-01-01|2014-01-28|        5142| 53.65835544906299| 101.97021|
|      H|2000-01-01|2014-01-28|        5142|54.311930299616655| 107.25877|
|      I|2000-01-01|2014-01-28|        5142| 42.97768542515161|  93.09192|
|      J|2000-01-01|2014-01-28|        5142| 66.41689743211138| 118.97069|
|      K|2000-01-01|2014-01-28|        5142|46.335176925261464|  97.18328|
|      L|2000-01-01|2014-01-28|        5142| 63.15448890980558| 114.59742|
|      M|2000-01-01|2014-01-28|        5142| 46.84981537639272| 96.246735|
|      N|2000-01-01|2014-01-28|        5142| 51.53710830749858| 108.87489|
|      O|2000-01-01|2014-01-28|        5142| 50.86705852595228| 111.03256|
+-------+----------+----------+------------+------------------+----------+

-------------------------------------------
Batch: 1
-------------------------------------------
...
```

As long as a few batches print out, don't worry if you see this "WARN ProcessingTimeExecutor: Current batch is falling behind. The trigger interval is ???? milliseconds, but spent ???? milliseconds".  Feel free to increase above 30 seconds if you aren't getting a couple batches.  Errors about tasks/batches aborting at the end is fine (the `s.stop()` call triggered this).

## Rain Forecast Dataset

Now lets generate some data so we can train a model (in part 4) to predict rain.

Define DataFrames named `features` and `today` that look like this:
* `DataFrame[station: string, date: date, raining: int]`
* `DataFrame[station: string, date: date, month: int, sub1degrees: float, sub1raining: int, sub2degrees: float, sub2raining: int]`

In `today`, the raining column will be 1 if there was rain at the given station on the given day.

In `features`, the `month` is 1-12 and is extracted from the `date`,
but the other columns indicate weather conditions prior to the date.
For example, sub1degrees indicates the temperature 1 day before the
date.  sub2raining indicates whether it was raining 2 days before the
date.

You can use `date_add("value.date", ????).alias("date")` to move the
date forward (so that weather conditions are in the past relative to
the date).  It's probably easiest to construct `features` by creating
and joining two other DataFrames: one for yesterday and one for two
days ago.

Join `today` with `features` on the `date` and `station` columns, and
stream all the columns of the results to parquet files (you choose the
name).  Requirements:

* repartition the stream so there is only 1 partition
* trigger it every 1 minutes

These configurations are so that we only produce 1 parquet file per
minute (too many very small parquet files makes the next part slow).

## Part 4: Spark ML

## Training and Evaluation

Wait about a minute until at least one parquet file is produced.

Do some imports:

```python
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.classification import DecisionTreeClassifier
```

Read your parquet files from part 3 (depending on how long it has been
running, you may have more or less data -- this is OK).

Use the VectorAssembler to combine the feature columns ("month",
"sub1degrees", "sub1raining", "sub2degrees", "sub2raining") into a
single column.

Split your data into train and test (you decide the ratios/seed).

Train a `DecisionTreeClassifier` on your training data to predict
raining based on the features.

Print the decision tree with `toDebugString` -- something like this:

```
DecisionTreeClassificationModel: uid=DecisionTreeClassifier_bbd99682b231, depth=5, numNodes=17, numClasses=2, numFeatures=5
  If (feature 2 <= 0.5)
   Predict: 0.0
  Else (feature 2 > 0.5)
   If (feature 1 <= 39.70075035095215)
    If (feature 1 <= 34.9547119140625)
     If (feature 0 <= 2.5)
      If (feature 3 <= 45.0179557800293)
       Predict: 0.0
      Else (feature 3 > 45.0179557800293)
       Predict: 1.0
     Else (feature 0 > 2.5)
      Predict: 0.0
    Else (feature 1 > 34.9547119140625)
     If (feature 0 <= 11.5)
      If (feature 0 <= 2.5)
       Predict: 0.0
      Else (feature 0 > 2.5)
       Predict: 1.0
     Else (feature 0 > 11.5)
      If (feature 3 <= 45.0179557800293)
       Predict: 0.0
      Else (feature 3 > 45.0179557800293)
       Predict: 1.0
   Else (feature 1 > 39.70075035095215)
    Predict: 1.0
```

Use the model to make predictions on the test data.  What is the
*accuracy* (percent of times the model is correct)?  What percent of
the time is is raining?  You might print these numbers in the
following way, or feel free to choose your own format:

```
+------------------+------------------+
|      avg(correct)|      avg(raining)|
+------------------+------------------+
|0.8127599577017977|0.3017624250969334|
+------------------+------------------+
```

In this example, it rains 30% of the time, so a model could easily be
correct 70% of the time (by always predicting no rain).  Apparently
this model is bit better (81% correct).

## Model Deployment

Remember the `features` DataFrame stream you defined in part 3?  Use
`features` as a source and apply your model to stream weather
predictions to the screen.  Something like this:

```
...
-------------------------------------------
Batch: 2
-------------------------------------------
+-------+----------+----------+
|station|      date|prediction|
+-------+----------+----------+
|      A|2021-11-13|       0.0|
|      A|2021-11-11|       0.0|
|      A|2021-11-10|       1.0|
|      A|2021-11-12|       0.0|
|      A|2021-11-17|       1.0|
|      A|2021-11-15|       1.0|
|      A|2021-11-16|       1.0|
|      A|2021-11-14|       0.0|
+-------+----------+----------+
...
```

Note that since we're artificially generating a day's worth of weather
every second, the predictions are struggling to keep up.  A few days
pass before we share our predictions -- too late to be useful even if
it's correct!  We'll ignore this problem for the assignment (if
weather weren't being simulated an an accelerated rate, it wouldn't be
a problem).

Stop your notebook/stream after a few batches and save it.

## Submission

We should be able to run the following on your submission to create the mini cluster:

```
docker build -t 6 ./image
docker compose up -d
```

We should be able to open Jupyter on the VM at localhost:5000 and find
and run your kafka.ipynb and spark.ipynb files in the notebooks
directory.

## Approximate Rubric:

The following is approximately how we will grade, but we may make
changes if we overlooked an important part of the specification or did
not consider a common mistake.

1. [x/1] The Dockerfile and docker-compose.yml setup the cluster (part 1)
2. [x/1] The producer writes correctly formatted/serialized messages to both the `stations` and `stations-json` streams (part 1)
3. [x/1] The producer does its part to achieve exactly-once semantics (part 1)
4. [x/1] The consumer threads produce JSON files with the correct format (part 2)
5. [x/1] The consumer threads produce JSON files with the correct content, based on consumed messages (part 2)
6. [x/1] The consumer does its part to achieve exactly-once semantics -- double check consintency of start/end dates and count (part 2)
7. [x/1] The counts are correctly streamed to the console (part 3)
8. [x/1] The forecast training data is correctly streamed to parquet files (part 3)
9. [x/1] The model is correctly trained on training data and evaluated on test data (part 4)
10. [x/1] The model is used to stream predictions for station A to the console (part 4)
