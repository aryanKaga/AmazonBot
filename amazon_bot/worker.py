import os
import sys
import logging
from redis import Redis
from rq import Worker, Queue, Connection
from amazon_bot.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    redis_url = get_settings().redis_url
    conn = Redis.from_url(redis_url)
    with Connection(conn):
        worker = Worker(['default'])
        logger.info(f"Starting RQ worker on {redis_url}...")
        worker.work()
