#!/usr/bin/env python3
"""
Worker Entry Point
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.worker import main

if __name__ == '__main__':
    main()
