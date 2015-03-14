Deferrable
==========

Python queueing framework with pluggable backends. Currently supports [https://github.com/gamechanger/dockets](Dockets), [http://aws.amazon.com/sqs/](SQS), and [https://docs.python.org/2/library/queue.html](Python's stdlib Queue).

## Table of Contents

- [Quick Start](#quick-start)
- [Class Hierarchy](#class-hierarchy)
  - [Queues](#queues)
  - [Backends](#backends)
  - [Deferrable Instances](#deferrable-instances)
- [Execution Model](#execution-model)
  - [Retry](#retry)
  - [TTL](#ttl)
  - [Debouncing](#debouncing)
- [Metadata and Events](#metadata-and-events)
- [Running Tests](#running-tests)

## Quick Start

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

Each broker implementation starts with a `Queue`. This class should expose a minimal interface to the underlying queue, including methods like `push`, `pop`, `complete`, and `flush`. Each queue implementation also exposes a `stats` method which allows you to introspect properties of the queue such as its length and the number of queue items that are currently in flight.

Some broker implementations may provide separate implementations for the "main" `Queue` and the "error" `Queue`. For an example of this, see the `Dockets` queue implementation.

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

*NB*: Due to limitations in how pickling works, functions must be defined at module-level to be deferred.

`Deferrable` provides additional functionality around exactly how jobs are processed, including:

### Retry

Retry parameters may be specified within the `@deferrable` decorator and include:

- `error_classes`: Iterable of error classes which should trigger a retry. If an error not included in this iterable is encountered, the job will be pushed to the error queue after any failure.
- `max_attempts`: Total number of times to retry an item before sending it to the error queue. Defaults to 1, e.g. no retry.

```python
# This will be requeued twice after it fails, for a total of three attempts before
# being sent to the error queue
@deferrable_instance.deferred(error_classes=[ZeroDivisionError], max_attempts=3)
def divide():
    return 1 / 0
```

### TTL

To be written...

### Debouncing

To be written...

## Metadata and Events

To be written...

## Running Tests

Tests depend on a Redis 2.8+ instance running at `localhost:6379`. If you've got that, then `python setup.py test` should work.
