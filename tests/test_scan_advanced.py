import time
from pathlib import Path
from jupiter.core.scanner import ProjectScanner
from jupiter.core.cache import CacheManager
from jupiter.core.report import ScanReport

def test_incremental_scan(tmp_path):
    # 1. Initial state
    f1 = tmp_path / "f1.py"
    f1.write_text("def foo(): pass")
    
    # 2. First scan
    scanner = ProjectScanner(root=tmp_path)
    files = list(scanner.iter_files())
    report = ScanReport.from_files(root=tmp_path, files=files).to_dict()
    
    # Save to cache
    cache_manager = CacheManager(tmp_path)
    cache_manager.save_last_scan(report)
    
    # Verify cache exists
    assert (tmp_path / ".jupiter" / "cache" / "last_scan.json").exists()
    
    # 3. Modify file
    time.sleep(0.1) # Ensure mtime changes
    f1.write_text("def foo(): pass\ndef bar(): pass")
    
    # 4. Incremental scan
    scanner_inc = ProjectScanner(root=tmp_path, incremental=True)
    files_inc = list(scanner_inc.iter_files())
    
    assert len(files_inc) == 1
    # Since we modified the file, it should be re-analyzed.
    # We can check if the size matches the new content
    assert files_inc[0].size_bytes == f1.stat().st_size

def test_incremental_scan_no_change(tmp_path):
    # 1. Initial state
    f1 = tmp_path / "f1.py"
    f1.write_text("def foo(): pass")
    
    # 2. First scan
    scanner = ProjectScanner(root=tmp_path)
    files = list(scanner.iter_files())
    # Mock analysis result to verify it's reused
    files[0].language_analysis = {"mock": "data"}
    
    report = ScanReport.from_files(root=tmp_path, files=files).to_dict()
    
    # Save to cache
    cache_manager = CacheManager(tmp_path)
    cache_manager.save_last_scan(report)
    
    # 3. Incremental scan without changes
    scanner_inc = ProjectScanner(root=tmp_path, incremental=True)
    files_inc = list(scanner_inc.iter_files())
    
    assert len(files_inc) == 1
    # Should have the mocked analysis data
    assert files_inc[0].language_analysis == {"mock": "data"}

def test_ignore_file(tmp_path):
    (tmp_path / ".jupiterignore").write_text("*.tmp\nsecret/")
    (tmp_path / "test.py").write_text("")
    (tmp_path / "temp.tmp").write_text("")
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "key.txt").write_text("")
    
    scanner = ProjectScanner(root=tmp_path, ignore_file=".jupiterignore")
    files = list(scanner.iter_files())
    
    names = [f.path.name for f in files]
    assert "test.py" in names
    assert "temp.tmp" not in names
    assert "key.txt" not in names

def test_complex_globs(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("")
    (tmp_path / "src" / "test_main.py").write_text("")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_all.py").write_text("")
    
    # Ignore all test files
    scanner = ProjectScanner(root=tmp_path, ignore_globs=["**/test_*.py"])
    files = list(scanner.iter_files())
    
    names = [f.path.name for f in files]
    assert "main.py" in names
    assert "test_main.py" not in names
    assert "test_all.py" not in names
