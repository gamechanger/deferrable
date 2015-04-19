"""This may seem like a silly module right now, but we had to
separate this out so that deferrable.py and its sub-modules
could all import it without circular imports."""

# SQS has a hard limit of 900 seconds, and Dockets
# delay queues incur heavy performance penalties,
# so this seems like a reasonable limit for all
MAXIMUM_DELAY_SECONDS = 900
