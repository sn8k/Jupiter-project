"""Tests for cache management."""

import json
import time
from pathlib import Path
from jupiter.core.cache import CacheManager

def test_cache_manager_save_load(tmp_path):
    """Test saving and loading scan cache."""
    cache_manager = CacheManager(tmp_path)
    
    data = {"files": [{"path": "test.py", "size": 100}]}
    cache_manager.save_last_scan(data)
    
    loaded = cache_manager.load_last_scan()
    assert loaded == data

def test_analysis_cache(tmp_path):
    """Test saving and loading analysis cache."""
    cache_manager = CacheManager(tmp_path)
    
    data = {"test.py": {"complexity": 5, "mtime": 123456.0}}
    cache_manager.save_analysis_cache(data)
    
    loaded = cache_manager.load_analysis_cache()
    assert loaded == data

def test_clear_cache(tmp_path):
    """Test clearing the cache."""
    cache_manager = CacheManager(tmp_path)
    cache_manager.save_last_scan({"foo": "bar"})
    
    assert (tmp_path / ".jupiter" / "cache" / "last_scan.json").exists()
    
    cache_manager.clear_cache()
    
    assert not (tmp_path / ".jupiter" / "cache" / "last_scan.json").exists()
