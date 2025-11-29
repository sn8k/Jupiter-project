"""Tests for refactoring recommendations."""

from pathlib import Path
from jupiter.core.analyzer import ProjectAnalyzer, AnalysisSummary, FileMetadata
from jupiter.core.quality.complexity import estimate_complexity
from jupiter.core.quality.duplication import find_duplications

def test_complexity_estimation(tmp_path):
    """Test complexity calculation."""
    f = tmp_path / "complex.py"
    f.write_text("""
def complex_func(x):
    if x:
        for i in range(10):
            if i % 2 == 0:
                print(i)
            else:
                print(x)
    elif x < 0:
        while True:
            break
    """, encoding="utf-8")
    
    score = estimate_complexity(f)
    # Base 1 + if + for + if + elif + while = 6
    assert score >= 5

def test_duplication_detection(tmp_path):
    """Test duplication detection."""
    f1 = tmp_path / "dup1.py"
    f2 = tmp_path / "dup2.py"
    
    content = "\n".join([f"print({i})" for i in range(20)])
    f1.write_text(content, encoding="utf-8")
    f2.write_text(content, encoding="utf-8")
    
    dups = find_duplications([f1, f2], chunk_size=5)
    assert len(dups) > 0
    assert len(dups[0]["occurrences"]) >= 2

def test_refactoring_recommendations(tmp_path):
    """Test that analyzer produces recommendations."""
    # Setup a complex file
    f = tmp_path / "complex.py"
    # Create a very complex function
    code = "def complex():\n"
    for i in range(20):
        code += f"    if {i}:\n        pass\n"
    f.write_text(code, encoding="utf-8")
    
    analyzer = ProjectAnalyzer(tmp_path)
    
    # Mock metadata
    metadata = FileMetadata.from_path(f)
    metadata.language_analysis = {"defined_functions": ["complex"]}
    
    summary = analyzer.summarize([metadata])
    
    assert len(summary.refactoring) > 0
    assert summary.refactoring[0]["type"] == "complexity"
    assert summary.refactoring[0]["severity"] == "medium" or summary.refactoring[0]["severity"] == "high"
