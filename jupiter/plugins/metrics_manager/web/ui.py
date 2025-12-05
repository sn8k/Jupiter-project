"""
Metrics Manager Plugin - Web UI Module

Provides HTML and JS content for the plugin's WebUI panel.

@version 1.0.0
@module jupiter.plugins.metrics_manager.web.ui
"""

from pathlib import Path


def get_ui_html() -> str:
    """
    Get the HTML content for the plugin's UI panel.
    
    Returns a container div that will be populated by the JS.
    """
    return '''
    <div id="metrics-manager-root" class="plugin-container">
        <p class="loading">Loading Metrics Manager...</p>
    </div>
    '''


def get_ui_js() -> str:
    """
    Get the JavaScript content for the plugin's UI panel.
    
    Returns the content of main.js or a fallback if not found.
    """
    js_path = Path(__file__).parent / "panels" / "main.js"
    
    if js_path.exists():
        return js_path.read_text(encoding="utf-8")
    
    # Fallback minimal JS
    return '''
    // Metrics Manager Plugin - Fallback JS
    export function mount(container, bridge) {
        container.innerHTML = '<p>Metrics Manager plugin UI not found.</p>';
    }
    export function unmount() {}
    '''
