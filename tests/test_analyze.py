from jupiter.core.analyzer import ProjectAnalyzer
from jupiter.core.scanner import ProjectScanner

def test_analyzer_summary(tmp_path):
    (tmp_path / "main.py").write_text("def foo(): pass")
    
    scanner = ProjectScanner(root=tmp_path)
    analyzer = ProjectAnalyzer(root=tmp_path)
    
    summary = analyzer.summarize(scanner.iter_files())
    
    assert summary.file_count == 1
    assert summary.python_summary is not None
