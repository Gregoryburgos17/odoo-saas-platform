#!/usr/bin/env python3
"""
RQ Worker Manager for Odoo SaaS Platform
"""
import os
import sys
import signal
import logging
from datetime import datetime

from redis import Redis
from rq import Worker, Queue, Connection

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkerManager:
    """Manages RQ workers"""

    def __init__(self):
        self.redis_host = os.getenv('REDIS_HOST', 'redis')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        self.redis_password = os.getenv('REDIS_PASSWORD', '')

        self.queues = ['high', 'default', 'low']
        self.connection = None
        self.worker = None
        self.running = True

    def get_connection(self) -> Redis:
        """Get Redis connection"""
        if self.connection is None:
            self.connection = Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password if self.redis_password else None,
            )
        return self.connection

    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def shutdown_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.running = False
            if self.worker:
                self.worker.request_stop(signum, frame)

        signal.signal(signal.SIGTERM, shutdown_handler)
        signal.signal(signal.SIGINT, shutdown_handler)

    def run(self):
        """Start the worker"""
        logger.info("=" * 60)
        logger.info("Starting Odoo SaaS Worker")
        logger.info(f"Redis: {self.redis_host}:{self.redis_port}")
        logger.info(f"Queues: {', '.join(self.queues)}")
        logger.info("=" * 60)

        self.setup_signal_handlers()

        try:
            conn = self.get_connection()

            # Test connection
            conn.ping()
            logger.info("Redis connection successful")

            # Create queues
            queues = [Queue(name, connection=conn) for name in self.queues]

            # Create and start worker
            self.worker = Worker(
                queues,
                connection=conn,
                name=f"worker-{os.getpid()}",
            )

            logger.info(f"Worker {self.worker.name} starting...")
            self.worker.work(with_scheduler=True)

        except Exception as e:
            logger.error(f"Worker error: {e}")
            raise

        finally:
            logger.info("Worker stopped")


def get_queue(name: str = 'default') -> Queue:
    """Get a queue by name"""
    redis_conn = Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        password=os.getenv('REDIS_PASSWORD', '') or None,
    )
    return Queue(name, connection=redis_conn)


def enqueue_job(func, *args, queue_name: str = 'default', **kwargs):
    """Enqueue a job"""
    queue = get_queue(queue_name)
    return queue.enqueue(func, *args, **kwargs)


def main():
    """Main entry point"""
    manager = WorkerManager()
    manager.run()


if __name__ == '__main__':
    main()
