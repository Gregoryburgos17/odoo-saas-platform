"""
Health Check API for Customer Portal
"""
import os
import logging
from flask import Blueprint, jsonify
import redis

from shared.database import DatabaseManager

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('', methods=['GET'])
@health_bp.route('/', methods=['GET'])
def health():
    """Basic health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'customer-portal',
        'version': os.getenv('APP_VERSION', '1.0.0'),
    }), 200


@health_bp.route('/ready', methods=['GET'])
def readiness():
    """Readiness probe"""
    checks = {
        'database': False,
        'redis': False,
    }
    all_healthy = True

    # Check database
    try:
        checks['database'] = DatabaseManager.health_check()
        if not checks['database']:
            all_healthy = False
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        all_healthy = False

    # Check Redis
    try:
        redis_host = os.getenv('REDIS_HOST', 'redis')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))

        r = redis.Redis(host=redis_host, port=redis_port, socket_timeout=5)
        r.ping()
        checks['redis'] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        all_healthy = False

    status_code = 200 if all_healthy else 503
    return jsonify({
        'status': 'ready' if all_healthy else 'not_ready',
        'checks': checks,
    }), status_code


@health_bp.route('/live', methods=['GET'])
def liveness():
    """Liveness probe"""
    return jsonify({'status': 'alive'}), 200
