import json
import subprocess
import sys
from pathlib import Path
from jupiter.core.analyzer import ProjectAnalyzer
from jupiter.core.scanner import ProjectScanner

def test_dynamic_analysis_integration(tmp_path):
    # Create a script that prints something
    script = tmp_path / "script.py"
    script.write_text("def foo():\n    print('hello')\n\nfoo()")
    
    # Run a scan first to create cache
    scanner = ProjectScanner(root=tmp_path)
    files = list(scanner.iter_files())
    from jupiter.core.report import ScanReport
    from jupiter.core.cache import CacheManager
    report = ScanReport.from_files(root=tmp_path, files=files).to_dict()
    CacheManager(tmp_path).save_last_scan(report)
    
    # Run jupiter run --with-dynamic
    # We need to invoke jupiter module. 
    # Assuming we are running tests from project root and jupiter is in python path.
    
    # We need to set PYTHONPATH to include current dir
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    
    result = subprocess.run(
        [sys.executable, "-m", "jupiter.cli.main", "run", f"{sys.executable} {str(script)}", str(tmp_path), "--with-dynamic"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmp_path
    )
    if result.returncode != 0:
        print(result.stderr)
    assert result.returncode == 0
    
    # Now check if dynamic analysis data is saved in cache
    # We need to manually check the cache file because ProjectAnalyzer reads it
    cache_file = tmp_path / ".jupiter" / "cache" / "last_scan.json"
    if not cache_file.exists():
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert cache_file.exists()
    
    with open(cache_file, "r") as f:
        data = json.load(f)
        assert "dynamic" in data
        assert "calls" in data["dynamic"]
        # script.py::foo should be in calls
        # Note: path might be relative or absolute depending on how tracer works
        # Tracer uses os.path.abspath
        # But keys in dynamic data are usually "path::func"
        
        # Let's check keys
        keys = list(data["dynamic"]["calls"].keys())
        if not any("foo" in k for k in keys):
            print("Keys found:", keys)
        assert any("foo" in k for k in keys)

def test_python_complexity_duplication(tmp_path):
    f1 = tmp_path / "complex.py"
    # Create complex code
    code = "def complex_func(x):\n"
    for i in range(20):
        code += f"    if x == {i}: print({i})\n"
    f1.write_text(code)
    
    f2 = tmp_path / "dup1.py"
    f2.write_text("def dup():\n    print('duplicate code')\n    print('duplicate code')\n    print('duplicate code')\n    print('duplicate code')\n    print('duplicate code')\n    print('duplicate code')")
    
    f3 = tmp_path / "dup2.py"
    f3.write_text("def dup():\n    print('duplicate code')\n    print('duplicate code')\n    print('duplicate code')\n    print('duplicate code')\n    print('duplicate code')\n    print('duplicate code')")
    
    scanner = ProjectScanner(root=tmp_path)
    analyzer = ProjectAnalyzer(root=tmp_path)
    summary = analyzer.summarize(scanner.iter_files())
    
    # Check complexity
    # We expect at least one file with high complexity
    complex_files = [f for f in summary.quality.get("complexity_per_file", []) if f["score"] > 10]
    assert len(complex_files) > 0
    assert complex_files[0]["path"] == str(f1)
    
    # Check duplication
    dups = summary.quality.get("duplication_clusters", [])
    assert len(dups) > 0
    # Should find duplication between dup1 and dup2
    dup_recs = [r for r in summary.refactoring if r["type"] == "duplication"]
    assert dup_recs, "Expected duplication refactoring recommendation"
    first_dup = dup_recs[0]
    assert first_dup.get("locations"), "Duplication recommendation should list occurrences"
    assert any("dup1.py" in loc["path"] or "dup2.py" in loc["path"] for loc in first_dup["locations"])
    assert all("line" in loc and loc["line"] >= 1 for loc in first_dup["locations"])
    assert any((loc.get("function") == "dup") for loc in first_dup["locations"])
    assert first_dup.get("code_excerpt"), "Duplication recommendation should include a code excerpt"

def test_js_complexity_duplication(tmp_path):
    f1 = tmp_path / "complex.js"
    # Create complex JS code
    code = "function complex(x) {\n"
    for i in range(20):
        code += f"    if (x == {i}) {{ console.log({i}); }}\n"
    code += "}"
    f1.write_text(code)
    
    scanner = ProjectScanner(root=tmp_path)
    analyzer = ProjectAnalyzer(root=tmp_path)
    summary = analyzer.summarize(scanner.iter_files())
    
    # Check complexity for JS
    complex_files = [f for f in summary.quality.get("complexity_per_file", []) if f["score"] > 10]
    assert len(complex_files) > 0
    assert complex_files[0]["path"] == str(f1)
