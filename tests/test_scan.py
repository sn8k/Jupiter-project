from pathlib import Path
from jupiter.core.scanner import ProjectScanner

def test_scanner_simple(tmp_path):
    # Create a dummy file
    (tmp_path / "test.py").write_text("print('hello')")
    
    scanner = ProjectScanner(root=tmp_path)
    files = list(scanner.iter_files())
    
    assert len(files) == 1
    assert files[0].path.name == "test.py"

def test_scanner_ignore(tmp_path):
    (tmp_path / "test.py").write_text("")
    (tmp_path / "ignore.me").write_text("")
    
    scanner = ProjectScanner(root=tmp_path, ignore_globs=["*.me"])
    files = list(scanner.iter_files())
    
    assert len(files) == 1
    assert files[0].path.name == "test.py"
