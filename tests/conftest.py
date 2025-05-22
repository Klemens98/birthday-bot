"""Test configuration and fixtures."""
import os
import sys
import pytest
import tempfile
import sqlite3
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database import DatabaseService

@pytest.fixture
def test_db():
    """Create a temporary test database."""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)  # Close the file descriptor immediately
    
    # Initialize the test database
    db = DatabaseService(db_path)
    
    yield db
    
    # Clean up - make sure connection is closed before deleting
    db._conn.close() if hasattr(db, '_conn') else None
    try:
        os.unlink(db_path)
    except PermissionError:
        pass  # If file is locked, let the OS clean it up later

@pytest.fixture
def test_config():
    """Create test configuration."""
    return {
        'DISCORD': {
            'TOKEN': 'test-token',
            'APPLICATION_ID': 123456789,
            'CHANNEL_ID': 987654321
        },
        'TIMEZONE': 'Europe/Berlin'
    }