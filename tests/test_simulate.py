from jupiter.core.simulator import ProjectSimulator

def test_simulate_remove_file():
    files = [
        {
            "path": "lib/utils.py",
            "language_analysis": {
                "defined_functions": ["helper"],
                "imports": [],
                "function_calls": []
            }
        },
        {
            "path": "main.py",
            "language_analysis": {
                "defined_functions": ["main"],
                "imports": ["lib.utils"],
                "function_calls": ["helper"]
            }
        }
    ]
    
    sim = ProjectSimulator(files)
    result = sim.simulate_remove_file("lib/utils.py")
    
    assert result.risk_score == "high"
    assert len(result.impacts) >= 1
    
    # Check for broken import
    broken_imports = [i for i in result.impacts if i.impact_type == "broken_import"]
    assert len(broken_imports) > 0
    assert broken_imports[0].target == "main.py"

def test_simulate_remove_function():
    files = [
        {
            "path": "lib/utils.py",
            "language_analysis": {
                "defined_functions": ["helper", "unused"],
                "imports": [],
                "function_calls": []
            }
        },
        {
            "path": "main.py",
            "language_analysis": {
                "defined_functions": ["main"],
                "imports": ["lib.utils"],
                "function_calls": ["helper"]
            }
        }
    ]
    
    sim = ProjectSimulator(files)
    
    # Remove used function
    result = sim.simulate_remove_function("lib/utils.py", "helper")
    assert result.risk_score == "high"
    assert any(i.target == "main.py" for i in result.impacts)
    
    # Remove unused function
    result_unused = sim.simulate_remove_function("lib/utils.py", "unused")
    assert result_unused.risk_score == "low"
    assert len(result_unused.impacts) == 0
