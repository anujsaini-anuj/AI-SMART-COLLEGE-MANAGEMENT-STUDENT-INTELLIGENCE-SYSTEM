import os

from dotenv import load_dotenv
from redis import Redis
from rq import Queue, Retry

load_dotenv()

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

redis_connection = Redis.from_url(
    REDIS_URL,
    socket_connect_timeout=5,
)

rag_queue = Queue(
    "rag-indexing",
    connection=redis_connection,
    default_timeout=7200,
)


def get_retry_policy():
    """
    Failed indexing jobs ko retry karo:
    1 minute, 5 minutes aur 15 minutes ke intervals par.
    """

    return Retry(
        max=3,
        interval=[60, 300, 900],
    )