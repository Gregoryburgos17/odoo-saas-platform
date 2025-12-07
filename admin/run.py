#!/usr/bin/env python3
"""
Admin Dashboard Entry Point
"""
import os
import sys

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


def main():
    """Run the admin dashboard"""
    # Create application
    app = create_app()

    # Initialize database
    with app.app_context():
        from shared.database import init_db
        try:
            init_db()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Database initialization warning: {e}")

    # Get configuration
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    print(f"Starting Admin Dashboard on {host}:{port}")

    # Run server
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )


if __name__ == '__main__':
    main()
