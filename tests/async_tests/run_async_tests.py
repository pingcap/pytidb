#!/usr/bin/env python3
"""
Run async tests without main conftest.py interference.

This script runs the async tests in isolation to avoid conflicts
with the main test configuration.
"""
import sys
import os
import pytest

if __name__ == "__main__":
    # Add the project root to Python path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

    # Run pytest with specific configuration to avoid main conftest.py
    args = [
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "-p", "no:main_conftest",  # Disable main conftest
        os.path.dirname(__file__)  # Run only tests in this directory
    ]

    # Add any additional arguments from command line
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])

    sys.exit(pytest.main(args))