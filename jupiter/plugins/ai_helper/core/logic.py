"""
core/logic.py - Business logic for AI Helper plugin.
Version: 1.2.0

This module contains business logic called by CLI, API, or UI.
It does not depend directly on FastAPI or argparse.

Supported providers:
- mock: Heuristic-based suggestions (default, no API needed)
- ollama: Local LLM via Ollama (http://localhost:11434)
- openai: OpenAI API (requires api_key)
- anthropic: Anthropic Claude API (requires api_key)
- azure_openai: Azure OpenAI / GitHub Models (requires api_key)

Conforme a plugins_architecture.md v0.4.0
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class AISuggestion:
    """Represents a single AI-generated suggestion."""
    path: str
    type: str  # refactoring, doc, security, optimization, testing, cleanup
    details: str
    severity: str  # info, low, medium, high, critical
    code_snippet: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None


def generate_suggestions(
    summary: Dict[str, Any],
    config: Dict[str, Any],
    bridge=None
) -> List[AISuggestion]:
    """
    Generate AI suggestions based on analysis summary.
    
    Args:
        summary: Analysis summary from jupiter.core.analyzer.
        config: Plugin configuration.
        bridge: Optional Bridge instance for services access.
    
    Returns:
        List of AI suggestions.
    """
    suggestions: List[AISuggestion] = []
    
    provider = config.get("provider", "mock")
    allowed_types = config.get("suggestion_types", ["refactoring", "doc", "testing"])
    large_threshold = config.get("large_file_threshold_kb", 50) * 1024
    func_threshold = config.get("max_functions_threshold", 20)
    
    if provider == "mock":
        suggestions.extend(_generate_mock_suggestions(
            summary, allowed_types, large_threshold, func_threshold
        ))
    elif provider == "ollama":
        suggestions.extend(_generate_ollama_suggestions(summary, config, allowed_types))
    elif provider == "openai":
        suggestions.extend(_generate_openai_suggestions(summary, config, allowed_types))
    elif provider == "anthropic":
        suggestions.extend(_generate_anthropic_suggestions(summary, config, allowed_types))
    elif provider == "azure_openai":
        suggestions.extend(_generate_azure_openai_suggestions(summary, config, allowed_types))
    else:
        # Fallback to mock for unknown providers
        suggestions.extend(_generate_mock_suggestions(
            summary, allowed_types, large_threshold, func_threshold
        ))
    
    return suggestions


def _generate_ollama_suggestions(
    summary: Dict[str, Any],
    config: Dict[str, Any],
    allowed_types: List[str]
) -> List[AISuggestion]:
    """
    Generate suggestions using Ollama local LLM.
    
    Requires Ollama running locally (default: http://localhost:11434).
    Supported models: codellama, mistral, llama2, deepseek-coder, etc.
    """
    import json
    import urllib.request
    import urllib.error
    
    suggestions: List[AISuggestion] = []
    
    ollama_url = config.get("ollama_url", "http://localhost:11434")
    model = config.get("ollama_model", "codellama")
    
    # Build context from summary
    context_parts = []
    if "python_summary" in summary:
        py = summary["python_summary"]
        context_parts.append(f"Python files: {py.get('total_python_files', 0)}")
        context_parts.append(f"Total functions: {py.get('total_functions', 0)}")
        context_parts.append(f"Potentially unused: {py.get('total_potentially_unused_functions', 0)}")
    
    if "hotspots" in summary:
        hotspots = summary["hotspots"]
        if hotspots.get("largest_files"):
            top_files = [f["path"] for f in hotspots["largest_files"][:3]]
            context_parts.append(f"Largest files: {', '.join(top_files)}")
    
    context = "\n".join(context_parts)
    
    prompt = f"""You are a code analysis assistant. Based on this project summary, suggest improvements.
Focus on: {', '.join(allowed_types)}

Project Summary:
{context}

Provide 3-5 actionable suggestions in JSON format:
[{{"path": "file or Global", "type": "refactoring|doc|security|optimization|testing|cleanup", "details": "description", "severity": "info|low|medium|high|critical"}}]

Only output valid JSON array, no other text."""

    try:
        req_data = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3}
        }).encode("utf-8")
        
        req = urllib.request.Request(
            f"{ollama_url}/api/generate",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            response_text = result.get("response", "")
            
            # Parse JSON from response
            try:
                # Try to extract JSON array from response
                start = response_text.find("[")
                end = response_text.rfind("]") + 1
                if start >= 0 and end > start:
                    json_str = response_text[start:end]
                    parsed = json.loads(json_str)
                    
                    for item in parsed:
                        if item.get("type") in allowed_types:
                            suggestions.append(AISuggestion(
                                path=item.get("path", "Global"),
                                type=item.get("type", "refactoring"),
                                details=item.get("details", ""),
                                severity=item.get("severity", "info")
                            ))
            except json.JSONDecodeError:
                # Ollama response wasn't valid JSON, add fallback suggestion
                suggestions.append(AISuggestion(
                    path="Global",
                    type="doc",
                    details=f"Ollama ({model}) analysis completed but response parsing failed.",
                    severity="info"
                ))
                
    except urllib.error.URLError as e:
        suggestions.append(AISuggestion(
            path="Global",
            type="doc",
            details=f"Ollama connection failed: {e.reason}. Is Ollama running on {ollama_url}?",
            severity="low"
        ))
    except Exception as e:
        suggestions.append(AISuggestion(
            path="Global",
            type="doc",
            details=f"Ollama error: {str(e)}",
            severity="low"
        ))
    
    return suggestions


def _generate_openai_suggestions(
    summary: Dict[str, Any],
    config: Dict[str, Any],
    allowed_types: List[str]
) -> List[AISuggestion]:
    """Generate suggestions using OpenAI API."""
    # Placeholder - requires openai package
    return [AISuggestion(
        path="Global",
        type="doc",
        details="OpenAI provider not yet implemented. Use 'ollama' or 'mock' for now.",
        severity="info"
    )]


def _generate_anthropic_suggestions(
    summary: Dict[str, Any],
    config: Dict[str, Any],
    allowed_types: List[str]
) -> List[AISuggestion]:
    """Generate suggestions using Anthropic Claude API."""
    # Placeholder - requires anthropic package
    return [AISuggestion(
        path="Global",
        type="doc",
        details="Anthropic provider not yet implemented. Use 'ollama' or 'mock' for now.",
        severity="info"
    )]


def _generate_azure_openai_suggestions(
    summary: Dict[str, Any],
    config: Dict[str, Any],
    allowed_types: List[str]
) -> List[AISuggestion]:
    """Generate suggestions using Azure OpenAI API (compatible with GitHub Models)."""
    # Placeholder - requires azure-openai package
    return [AISuggestion(
        path="Global",
        type="doc",
        details="Azure OpenAI provider not yet implemented. Use 'ollama' or 'mock' for now.",
        severity="info"
    )]


def analyze_single_file(
    file_path: str,
    config: Dict[str, Any],
    bridge=None
) -> Dict[str, Any]:
    """
    Analyze a single file and return results.
    
    Called by CLI and API for targeted file analysis.
    
    Args:
        file_path: Path to the file to analyze.
        config: Plugin configuration.
        bridge: Optional Bridge instance.
    
    Returns:
        Analysis result with suggestions list.
    """
    from pathlib import Path
    
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    content = path.read_text(encoding="utf-8", errors="replace")
    suggestions = analyze_file(str(path), content, config)
    
    return {
        "file": str(path),
        "analyzed": True,
        "suggestions": [asdict(s) for s in suggestions],
        "timestamp": datetime.now().isoformat()
    }


def _generate_mock_suggestions(
    summary: Dict[str, Any],
    allowed_types: List[str],
    large_threshold: int,
    func_threshold: int
) -> List[AISuggestion]:
    """
    Generate heuristic-based mock suggestions.
    
    Args:
        summary: Analysis summary.
        allowed_types: Types of suggestions to generate.
        large_threshold: Size threshold for large file warnings.
        func_threshold: Function count threshold for god object warnings.
    
    Returns:
        List of mock suggestions.
    """
    suggestions: List[AISuggestion] = []
    
    # Documentation suggestions
    if "doc" in allowed_types and "python_summary" in summary:
        py_sum = summary.get("python_summary", {})
        if py_sum.get("avg_functions_per_file", 0) > 3:
            suggestions.append(AISuggestion(
                path="Global",
                type="doc",
                details="High function density detected. Consider adding module-level docstrings.",
                severity="info"
            ))
    
    # Cleanup suggestions
    if "cleanup" in allowed_types and "python_summary" in summary:
        py_sum = summary.get("python_summary", {})
        unused = py_sum.get("total_potentially_unused_functions", 0)
        if unused > 10:
            suggestions.append(AISuggestion(
                path="Global",
                type="cleanup",
                details=f"Found {unused} potentially unused functions. Run 'jupiter check' to verify.",
                severity="low"
            ))
    
    # Refactoring suggestions for large files
    if "refactoring" in allowed_types and "hotspots" in summary:
        hotspots = summary.get("hotspots", {})
        
        for item in hotspots.get("largest_files", []):
            try:
                size_str = item.get("details", "0").split()[0]
                size = int(size_str)
                if size > large_threshold:
                    suggestions.append(AISuggestion(
                        path=item["path"],
                        type="refactoring",
                        details=f"File is large ({size // 1024}KB). Consider splitting into smaller modules.",
                        severity="medium"
                    ))
            except (ValueError, IndexError):
                pass
        
        # God Object detection
        for item in hotspots.get("most_functions", []):
            try:
                count_str = item.get("details", "0").split()[0]
                count = int(count_str)
                if count > func_threshold:
                    suggestions.append(AISuggestion(
                        path=item["path"],
                        type="refactoring",
                        details=f"High function count ({count}). This might be a 'God Object'. Consider extracting logic.",
                        severity="high"
                    ))
            except (ValueError, IndexError):
                pass
    
    # Security suggestions
    if "security" in allowed_types and "python_summary" in summary:
        py_sum = summary.get("python_summary", {})
        # Check for common security patterns (placeholder)
        if py_sum.get("has_exec_usage", False):
            suggestions.append(AISuggestion(
                path="Global",
                type="security",
                details="Usage of exec() detected. Consider safer alternatives.",
                severity="high"
            ))
    
    return suggestions


def get_status(state, bridge=None) -> Dict[str, Any]:
    """
    Get plugin status for health checks.
    
    Args:
        state: Plugin internal state.
        bridge: Optional Bridge instance.
    
    Returns:
        Status dictionary with health information.
    """
    provider_healthy = True
    provider_message = "OK"
    
    if state.provider != "mock" and state.enabled:
        if not state.api_key:
            provider_healthy = False
            provider_message = "API key not configured"
    
    is_healthy = state.enabled and provider_healthy
    
    return {
        "healthy": is_healthy,
        "details": {
            "enabled": state.enabled,
            "provider": state.provider,
            "provider_connected": provider_healthy,
            "message": provider_message if not provider_healthy else "AI Helper operational"
        }
    }


def validate_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate plugin configuration before saving.
    
    Args:
        config: Configuration to validate.
    
    Returns:
        Tuple (is_valid, error_message).
    """
    # Validate provider
    valid_providers = ["mock", "openai", "anthropic", "ollama", "azure_openai"]
    if "provider" in config:
        if config["provider"] not in valid_providers:
            return False, f"Invalid provider. Must be one of: {valid_providers}"
    
    # Validate API key presence for cloud providers
    cloud_providers = ["openai", "anthropic", "azure_openai"]
    if config.get("provider") in cloud_providers:
        if not config.get("api_key"):
            return False, f"API key required for {config.get('provider')} provider"
    
    # Validate Ollama URL if provider is ollama
    if config.get("provider") == "ollama":
        if not config.get("ollama_url"):
            # Default URL is fine, but warn if model not specified
            if not config.get("ollama_model"):
                return False, "Ollama model must be specified (e.g., 'codellama', 'mistral', 'llama2')"
    
    # Validate suggestion types
    valid_types = ["refactoring", "doc", "security", "optimization", "testing", "cleanup"]
    if "suggestion_types" in config:
        for t in config["suggestion_types"]:
            if t not in valid_types:
                return False, f"Invalid suggestion type: {t}. Valid types: {valid_types}"
    
    # Validate severity threshold
    valid_severities = ["info", "low", "medium", "high", "critical"]
    if "severity_threshold" in config:
        if config["severity_threshold"] not in valid_severities:
            return False, f"Invalid severity threshold. Must be one of: {valid_severities}"
    
    return True, None


def analyze_file(file_path: str, content: str, config: Dict[str, Any]) -> List[AISuggestion]:
    """
    Analyze a single file for suggestions.
    
    Args:
        file_path: Path to the file.
        content: File content.
        config: Plugin configuration.
    
    Returns:
        List of suggestions for the file.
    """
    suggestions: List[AISuggestion] = []
    
    allowed_types = config.get("suggestion_types", ["refactoring", "doc", "testing"])
    lines = content.split("\n")
    
    # Documentation checks
    if "doc" in allowed_types:
        # Check for missing docstrings in Python files
        if file_path.endswith(".py"):
            if not content.strip().startswith('"""') and not content.strip().startswith("'''"):
                suggestions.append(AISuggestion(
                    path=file_path,
                    type="doc",
                    details="Module is missing a docstring at the top.",
                    severity="info",
                    line_start=1,
                    line_end=1
                ))
    
    # Size checks for refactoring
    if "refactoring" in allowed_types:
        if len(lines) > 500:
            suggestions.append(AISuggestion(
                path=file_path,
                type="refactoring",
                details=f"File has {len(lines)} lines. Consider splitting into smaller modules.",
                severity="medium"
            ))
    
    # Testing suggestions
    if "testing" in allowed_types:
        if "def " in content and "test" not in file_path.lower():
            if "import unittest" not in content and "import pytest" not in content:
                suggestions.append(AISuggestion(
                    path=file_path,
                    type="testing",
                    details="This module defines functions but has no visible test imports.",
                    severity="info"
                ))
    
    return suggestions
