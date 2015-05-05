Deferrable
==========

Python queueing framework with pluggable backends. Currently supports [Dockets](https://github.com/gamechanger/dockets), [SQS](http://aws.amazon.com/sqs/), and [Python's stdlib Queue](https://docs.python.org/2/library/queue.html).

## Table of Contents

- [Quick Start](#quick-start)
- [Class Hierarchy](#class-hierarchy)
  - [Queues](#queues)
    - [Envelopes and Items](#envelopes-and-items)
  - [Backends](#backends)
  - [Deferrable Instances](#deferrable-instances)
- [Execution Model](#execution-model)
  - [Retry](#retry)
    - [Exponential Backoff](#exponential-backoff)
  - [TTL](#ttl)
  - [Delay](#delay)
  - [Debouncing](#debouncing)
- [Metadata and Events](#metadata-and-events)
  - [MetadataProducerConsumers](#metadataproducerconsumers)
  - [EventConsumers](#eventconsumers)
- [Running Tests](#running-tests)

## Quick Start

After cloning the repository, run ```python setup.py develop``` to set up all of the dependencies/requirements

Just want to get up and running with, for example, an SQS queue? You'll end up writing something like this:

```python
# Set up your Deferrable instance, which we'll call `stats`
from deferrable import Deferrable
from deferrable.backend import SQSBackendFactory

sqs_connection = ... # Boto SQS Connection
factory = SQSBackendFactory(sqs_conn)
stats_backend = factory.create_backend_for_group('stats')
stats = Deferrable(backend=stats_backend)

# Register a function for deferrable execution through your Deferrable instance
@stats.deferrable
def run_some_stats(team_id):
    ...

# In your producer code, call .later() on that function to push it to the queue
run_some_stats.later(ObjectId(...))

# In your consumer, call .run_once() on the Deferrable instance to pop a queued job and run it
stats.run_once()
```

## Class Hierarchy

### Queues

Each broker implementation starts with a `Queue`. This class should expose a minimal interface to the underlying queue, including methods like `push`, `pop`, `touch`, `complete`, and `flush`. Each queue implementation also exposes a `stats` method which allows you to introspect properties of the queue such as its length and the number of queue items that are currently in flight.

Some broker implementations may provide separate implementations for the "main" `Queue` and the "error" `Queue`. For an example of this, see the `Dockets` queue implementation.

#### Envelopes and Items

When you `push` to a queue, the object you supply to the `push` method is called the `item`. This is serialized and pushed to the underlying broker.

When you `pop`, the `Queue` instance returns a tuple with the `envelope` and the `item`. The `item` is deserialized and should be the same as the object you supplied to `push`. The `envelope` is the complete, unaltered object that is returned from the broker. This often includes additional metadata which the broker needs to successfully call `complete`.

While an `envelope` is in-flight, you may invoke the `touch` method on the `Queue` to extend the visibility timeout on the `envelope`. This keeps the job "alive" from the perspective of the broker, and it will not reclaim the job and allow other consumers to see it.

The `complete` function expects to be passed the full `envelope` for the corresponding task which you want to complete.

The typical push-pop-complete flow therefore looks like this:

```python
my_item = {'a': 1}
queue.push(my_item)
popped_envelope, popped_item = queue.pop()
my_item == popped_item # True
queue.complete(popped_envelope)
```

### Backends

A `Backend` groups together a main `Queue`, an error `Queue`, and a `group` which is used to mark and identify these two queues within their broker systems. In our [Quick Start](#quick-start) example, we created a `Backend` in the `stats` group.

To facilitate easy creation of `Backends`, each broker implementation provides a specific `BackendFactory`. To create a `Backend`, first instantiate a general `BackendFactory` with a connection to your broker. You can then create `Backend` instances for multiple `group`s out of your single factory. To expand on our [Quick Start](#quick-start) example, we could make multiple SQS backends like this:

```python
from deferrable import Deferrable
from deferrable.backend import SQSBackendFactory

sqs_connection = ... # Boto SQS Connection
factory = SQSBackendFactory(sqs_conn)
stats_backend = factory.create_backend_for_group('stats')
tournaments_backend = factory.create_backend_for_group('tournaments')
```

These two `Backend`s will share the underlying SQS connection but operate on separate queues identified by their distinct `group`s.

The underlying `Queue`s in the `Backend` are available through the public `Backend.queue` and `Backend.error_queue` attributes. These can be useful when writing tools that need to directly interface with the underlying `Queue`s.

### Deferrable Instances

Once you have a `Backend`, you can wrap it in `Deferrable` to use it for deferred and distributed function execution.

```python
from deferrable import Deferrable
stats = Deferrable(backend=stats_backend)
```

Optionally, you can also provide a Redis client to `Deferrable` to enable the [debouncing](#debouncing) functionality.

```python
from deferrable import Deferrable
redis_client = ...
stats = Deferrable(backend=stats_backend, redis_client=redis_client)
```

A `Deferrable` instance wraps the `Backend` you give it and stores it as a public attribute at `Deferrable.backend`. The `Deferrable` instance exposes two public methods which you use to run deferrable jobs. The stats example is continued in the [Quick Start](#quick-start). The methods themselves are:

- `@deferrable_instance.deferrable`: Registers a module-level function for deferred execution. Once this decorator is applied, you can invoke the decorated function with `.later(...)` in your producer code to defer its execution.
- `deferrable_instance.run_once`: Pops a deferred job off the main queue associated with this `Deferrable` instance's backend. Your consumer code should have `run_once` inside its main loop.

## Execution Model

When `.later(...)` is called on a `@deferred` function, the function and its arguments are serialized using `cPickle` and pushed to the underlying main queue. In the consumer, `run_once` handles popping from the main queue, deserializing the function, executing it, and removing the job from the main queue.

**N.B.**: Due to limitations in how pickling works, functions must be defined at module-level to be deferred.

`Deferrable` provides additional functionality around exactly how jobs are processed, including:

### Retry

Retry parameters may be specified within the `@deferrable` decorator and include:

- `error_classes`: Iterable of error classes which should trigger a retry. If an error not included in this iterable is encountered, the job will be pushed to the error queue after any failure.
- `max_attempts`: Total number of times to retry an item before sending it to the error queue. Defaults to 5.

```python
# This will be requeued twice after it fails, for a total of three attempts before
# being sent to the error queue
@deferrable_instance.deferrable(error_classes=[ZeroDivisionError], max_attempts=3)
def divide():
    return 1 / 0
```

#### Exponential Backoff

By default, items to be retried will be delayed to effect an exponential backoff. Each subsequent attempt will double the time by which the retried item is delayed. This can be disabled via the `use_exponential_backoff` parameter to the `@deferrable` decorator.

```python
@deferrable_instance.deferrable(use_exponential_backoff=False)
def job_without_backoff():
    ...
```

### TTL

Deferrable jobs may be given a TTL through the `ttl_seconds` argument to the `@deferrable` decorator. The job will be considered "expired" and will not execute once the TTL has elapsed since the initial push of the job. This is often useful for time-sensitive tasks such as sending a real-time notification. Using a TTL, you can guarantee you will not send the message hours later (once the user no longer cares) if you run into a processing backlog.

- `ttl_seconds`: Length of the TTL, in seconds

```python
@deferrable_instance.deferrable(ttl_seconds=300)
def send_time_sensitive_message(message):
    ...

# Once this push completes, the TTL window begins. If
# 300 seconds pass before the job is processed, the
# consumer will abort the job without actually running it.
send_time_sensitive_message.later(...)
```

### Delay

Deferrable jobs may be unconditionally delayed through the `delay_seconds` argument to the `@deferrable` decorator. The job will not be available for processing until this many seconds have passed since its initial push.

**N.B.**: Some queue implementations may not support delayed jobs. Check your implementation. :smiley:

```python
@deferrable_instance.deferrable(delay_seconds=30)
def do_this_after_30_seconds():
    ...
```

### Debouncing

Debouncing provides a way to throttle execution of identical jobs (same method, args, and kwargs). If `debounce_seconds` is provided as an argument to the `@deferrable` decorator, the underlying job push will be delayed or skipped to ensure that the job is only made available in the main processing queue once every `debounce_seconds` seconds. The logic for debounce is all handled producer-side.

Only use debouncing with **idempotent** operations! Debouncing will cause some jobs to be skipped entirely, so if you are trying to store data in your job arguments, you're going to have a bad time.

Debouncing uses delay under the hood. You cannot specify both `delay_seconds` and `debounce_seconds` for a single job.

You must provide a `redis_client` to your `Deferrable` instance in order to use debouncing.

```python
deferrable_instance = Deferrable(backend=my_backend, redis_client=my_redis_client)

@deferrable_instance.deferrable(debounce_seconds=30)
def actually_queue_this_at_most_once_every_30_seconds():
    ...

actually_queue_this_at_most_once_every_30_seconds.later() # queued for immediate execution
actually_queue_this_at_most_once_every_30_seconds.later() # delayed by 30 seconds
actually_queue_this_at_most_once_every_30_seconds.later() # skipped, since we are already going to run one 30 seconds from now
```

Debounce supports an additional `debounce_always_delay` argument that, if `True`, will cause the underlying queue pushes to always either be skipped or delayed by the full amount of `debounce_always_delay`. This option can be handy if you know you are going to overqueue a job in a short amount of time.

```python
deferrable_instance = Deferrable(backend=my_backend, redis_client=my_redis_client)

@deferrable_instance.deferrable(debounce_seconds=30, debounce_always_delay=True)
def always_delay_this():
    ...

always_delay_this.later() # delayed by 30 seconds
always_delay_this.later() # skipped
```

*TODO*: Write a diagram or something showing some practical examples of how debounce behaves.

## Metadata and Events

### MetadataProducerConsumers

`MetadataProducerConsumer`s provide a way to pass context information from the producer to the consumer. These do not have access to the underlying item being queued, but can still be useful for passing item-independent information (like correlation ID, hostname of the producer, etc) onto your consumer.

You may register `MetadataProducerConsumer` objects against individual `Deferrable` objects. The base class `MetadataProducerConsumer` can be imported from `deferrable.metadata`. Your subclasses need to implement the following attributes and methods:

- `NAMESPACE`: Class attribute used to isolate information available to each `MetadataProducerConsumer`. This must be unique amongst all `MetadataProducerConsumer` instances registered to a single `Deferrable` instance.
- `produce_metadata(self)`: Called on the producer. Returns an item that is serialized and stored on the item as metadata under this instance's `NAMESPACE`.
- `consume_metadata(self, metadata):` Called on the consumer. Receives whatever `produce_metadata` returned as the `metadata` parameter.

```python
import socket
from deferrable.metadata import MetadataProducerConsumer

class HostnameMetadataProducerConsumer(MetadataProducerConsumer):
    NAMESPACE = "hostname"

    def produce_metadata(self):
        return socket.gethostname()

    def consume_metadata(self, metadata):
       print "Item was produced on host {}".format(metadata)

deferrable_instance.register_metadata_producer_consumer(HostnameMetadataProducerConsumer())
```

### EventConsumers

Each `Deferrable` instance emits events such as `on_push` and `on_pop` at various points in an item's lifecycle. You can register `EventConsumer` instances against a `Deferrable` instance to perform actions against these events. A full list of the events emitted is available in [deferrable.py](deferrable/deferrable.py).

There is no `EventConsumer` base class, you just need to instantiate an `object` with any `on_{event}` methods you want. Each handler method takes `(self, item)` as arguments.

```python
class MyEventConsumer(object):
    def on_push(self, item):
        print "Pushed {}".format(item)

deferrable_instance.register_event_consumer(MyEventConsumer())
```

## Running Tests

Tests depend on a Redis 2.8+ instance running at `localhost:6379`. If you've got that, then `python setup.py test` should work. However, `setuptools` is garbage, so you may need to `pip install` the requirements manually. YMMV.
