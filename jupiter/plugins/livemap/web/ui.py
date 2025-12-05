"""
Live Map Plugin - Web UI
========================

HTML and JavaScript templates for the Live Map visualization.

Version: 0.3.0
"""

from __future__ import annotations


def get_ui_html() -> str:
    """Return HTML content for the Live Map view."""
    return """
<div id="livemap-view" class="plugin-view-content">
    <div class="livemap-layout">
        <!-- Main Graph Panel -->
        <section class="livemap-main panel">
            <header>
                <div>
                    <p class="eyebrow" data-i18n="livemap_eyebrow">Visualization</p>
                    <h2 data-i18n="livemap_title">Live Map</h2>
                    <p class="muted" data-i18n="livemap_subtitle">Interactive dependency graph.</p>
                </div>
                <div class="actions">
                    <label class="checkbox-label livemap-option">
                        <input type="checkbox" id="livemap-simplify">
                        <span data-i18n="livemap_simplify">Simplify</span>
                    </label>
                    <button class="btn btn-secondary" id="livemap-reset-zoom" data-i18n="livemap_reset_zoom">Reset Zoom</button>
                    <button class="btn btn-primary" id="livemap-refresh-btn" data-i18n="refresh">Refresh</button>
                </div>
            </header>
            
            <div id="livemap-container" class="livemap-graph-container">
                <div class="livemap-loading" data-i18n="livemap_loading">Loading graph...</div>
            </div>
            
            <footer class="livemap-footer">
                <div id="livemap-stats" class="livemap-stats">
                    <span class="stat-item"><strong id="livemap-node-count">--</strong> <span data-i18n="livemap_nodes">nodes</span></span>
                    <span class="stat-item"><strong id="livemap-link-count">--</strong> <span data-i18n="livemap_links">links</span></span>
                </div>
                <div class="livemap-legend">
                    <span class="legend-item"><span class="legend-dot py"></span> Python</span>
                    <span class="legend-item"><span class="legend-dot js"></span> JS/TS</span>
                    <span class="legend-item"><span class="legend-dot dir"></span> Directory</span>
                    <span class="legend-item"><span class="legend-dot other"></span> Other</span>
                </div>
            </footer>
        </section>
        
        <!-- Help Panel -->
        <aside class="livemap-help panel">
            <header>
                <div>
                    <p class="eyebrow" data-i18n="livemap_help_eyebrow">Guide</p>
                    <h3 data-i18n="livemap_help_title">How to use Live Map</h3>
                </div>
            </header>
            
            <div class="help-content">
                <section class="help-section">
                    <h4 data-i18n="livemap_help_what_title">📊 What is Live Map?</h4>
                    <p class="muted small" data-i18n="livemap_help_what_desc">
                        Live Map visualizes the dependency graph of your project. Each node represents a file 
                        or module, and edges show import relationships between them.
                    </p>
                </section>
                
                <section class="help-section">
                    <h4 data-i18n="livemap_help_interact_title">🖱️ Interactions</h4>
                    <ul class="help-list">
                        <li data-i18n="livemap_help_interact_zoom">Scroll to zoom in/out</li>
                        <li data-i18n="livemap_help_interact_pan">Drag background to pan</li>
                        <li data-i18n="livemap_help_interact_drag">Drag nodes to reposition them</li>
                        <li data-i18n="livemap_help_interact_hover">Hover a node to see its name</li>
                    </ul>
                </section>
                
                <section class="help-section">
                    <h4 data-i18n="livemap_help_options_title">⚙️ Options</h4>
                    <ul class="help-list">
                        <li><strong data-i18n="livemap_simplify">Simplify</strong>: <span class="muted" data-i18n="livemap_help_simplify_desc">Groups files by folder to reduce clutter on large projects.</span></li>
                    </ul>
                </section>
                
                <section class="help-section">
                    <h4 data-i18n="livemap_help_colors_title">🎨 Color Legend</h4>
                    <ul class="help-list color-legend">
                        <li><span class="legend-dot py"></span> <span data-i18n="livemap_help_color_py">Python files (.py)</span></li>
                        <li><span class="legend-dot js"></span> <span data-i18n="livemap_help_color_js">JavaScript/TypeScript files</span></li>
                        <li><span class="legend-dot dir"></span> <span data-i18n="livemap_help_color_dir">Directories (simplified mode)</span></li>
                        <li><span class="legend-dot other"></span> <span data-i18n="livemap_help_color_other">Other files</span></li>
                    </ul>
                </section>
                
                <section class="help-section">
                    <h4 data-i18n="livemap_help_tips_title">💡 Tips</h4>
                    <ul class="help-list">
                        <li data-i18n="livemap_help_tip_scan">Run a scan first to populate the graph</li>
                        <li data-i18n="livemap_help_tip_large">For projects with 1000+ files, Simplify mode is auto-enabled</li>
                        <li data-i18n="livemap_help_tip_settings">Configure defaults in Settings > Plugins > Live Map</li>
                    </ul>
                </section>
            </div>
        </aside>
    </div>
</div>

<style>
#livemap-view {
    height: 100%;
    overflow: hidden;
}

.livemap-layout {
    display: grid;
    grid-template-columns: 1fr 320px;
    gap: 1rem;
    height: 100%;
    min-height: 600px;
}

@media (max-width: 1200px) {
    .livemap-layout {
        grid-template-columns: 1fr;
        grid-template-rows: 1fr auto;
    }
    .livemap-help {
        max-height: 300px;
        overflow-y: auto;
    }
}

.livemap-main {
    display: flex;
    flex-direction: column;
    min-height: 0;
}

.livemap-main header {
    flex-shrink: 0;
}

.livemap-graph-container {
    flex: 1;
    min-height: 400px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-subtle);
    overflow: hidden;
    position: relative;
}

.livemap-graph-container svg {
    width: 100%;
    height: 100%;
}

.livemap-loading {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: var(--fg-muted);
    font-size: 0.9rem;
}

.livemap-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.livemap-stats {
    display: flex;
    gap: 1.5rem;
    font-size: 0.85rem;
}

.stat-item {
    color: var(--fg-muted);
}

.stat-item strong {
    color: var(--fg);
}

.livemap-legend {
    display: flex;
    gap: 1rem;
    font-size: 0.75rem;
    color: var(--fg-muted);
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 0.25rem;
}

.legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}

.legend-dot.py { background: #3572A5; }
.legend-dot.js { background: #f1e05a; }
.legend-dot.dir { background: #6a5acd; }
.legend-dot.other { background: #69b3a2; }

.livemap-option {
    margin-right: 1rem;
    font-size: 0.85rem;
}

/* Help Panel */
.livemap-help {
    display: flex;
    flex-direction: column;
    overflow-y: auto;
}

.livemap-help header {
    flex-shrink: 0;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.75rem;
    margin-bottom: 0.75rem;
}

.help-content {
    flex: 1;
    overflow-y: auto;
}

.help-section {
    margin-bottom: 1.25rem;
}

.help-section h4 {
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
    color: var(--fg);
}

.help-section p {
    line-height: 1.5;
}

.help-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.help-list li {
    padding: 0.35rem 0;
    font-size: 0.85rem;
    color: var(--fg-muted);
    border-bottom: 1px solid var(--border-subtle, var(--border));
}

.help-list li:last-child {
    border-bottom: none;
}

.help-list.color-legend li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Graph node colors */
.livemap-node-py { fill: #3572A5; }
.livemap-node-js { fill: #f1e05a; }
.livemap-node-dir { fill: #6a5acd; }
.livemap-node-other { fill: #69b3a2; }

.livemap-link {
    stroke: #999;
    stroke-opacity: 0.6;
}
</style>
"""


def get_ui_js() -> str:
    """Return JavaScript for the Live Map view."""
    return """
(function() {
    const livemapPlugin = {
        simulation: null,
        svg: null,
        g: null,
        zoom: null,
        
        getApiBaseUrl() {
            if (window.state?.apiBaseUrl) return state.apiBaseUrl;
            const origin = window.location?.origin || '';
            if (origin.includes(':8050')) return origin.replace(':8050', ':8000');
            return origin || 'http://127.0.0.1:8000';
        },
        
        getToken() {
            if (window.state?.token) return state.token;
            return localStorage.getItem('jupiter-token') || sessionStorage.getItem('jupiter-token');
        },
        
        buildOptions(options = {}) {
            const opts = { ...options };
            const headers = Object.assign({ Accept: 'application/json' }, opts.headers || {});
            const token = this.getToken();
            if (token && !headers.Authorization) {
                headers.Authorization = `Bearer ${token}`;
            }
            opts.headers = headers;
            return opts;
        },
        
        async request(path, options = {}) {
            const url = path.startsWith('http') ? path : `${this.getApiBaseUrl()}${path}`;
            return fetch(url, this.buildOptions(options));
        },
        
        notify(message, type = 'info') {
            if (typeof window.showNotification === 'function') {
                window.showNotification(message, type, { title: 'Live Map', icon: '🗺️' });
            } else {
                console.log('[LiveMap]', message);
            }
        },
        
        async refresh() {
            const container = document.getElementById('livemap-container');
            if (!container) return;
            
            container.innerHTML = '<div class="livemap-loading">Loading graph...</div>';
            
            const simplify = document.getElementById('livemap-simplify')?.checked || false;
            
            try {
                const response = await this.request(`/plugins/livemap/graph?simplify=${simplify}`);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                const graphData = await response.json();
                this.render(graphData);
            } catch (err) {
                console.error('[LiveMap] Failed to load graph:', err);
                container.innerHTML = `<div class="livemap-loading" style="color: var(--error);">Error: ${err.message}</div>`;
                this.notify('Failed to load graph: ' + err.message, 'error');
            }
        },
        
        resetZoom() {
            if (this.svg && this.zoom) {
                this.svg.transition().duration(500).call(this.zoom.transform, d3.zoomIdentity);
            }
        },
        
        render(graphData) {
            const container = document.getElementById('livemap-container');
            if (!container) return;
            
            container.innerHTML = '';
            
            if (!graphData.nodes || graphData.nodes.length === 0) {
                container.innerHTML = '<div class="livemap-loading">No graph data. Run a scan first.</div>';
                this.updateStats(0, 0);
                return;
            }
            
            this.updateStats(graphData.nodes.length, graphData.links.length);
            
            if (typeof d3 === 'undefined') {
                container.innerHTML = '<div class="livemap-loading" style="color: var(--error);">D3.js not loaded</div>';
                return;
            }
            
            const width = container.clientWidth || 800;
            const height = container.clientHeight || 600;
            
            this.svg = d3.select('#livemap-container').append('svg')
                .attr('width', width)
                .attr('height', height)
                .attr('viewBox', [0, 0, width, height]);
            
            this.g = this.svg.append('g');
            
            // Zoom behavior
            this.zoom = d3.zoom()
                .extent([[0, 0], [width, height]])
                .scaleExtent([0.1, 8])
                .on('zoom', ({transform}) => this.g.attr('transform', transform));
            
            this.svg.call(this.zoom);
            
            // Simulation
            this.simulation = d3.forceSimulation(graphData.nodes)
                .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(60))
                .force('charge', d3.forceManyBody().strength(-100))
                .force('collide', d3.forceCollide().radius(15))
                .force('center', d3.forceCenter(width / 2, height / 2));
            
            // Links
            const link = this.g.append('g')
                .attr('class', 'links')
                .selectAll('line')
                .data(graphData.links)
                .join('line')
                .attr('class', 'livemap-link')
                .attr('stroke-width', d => Math.sqrt(d.weight || 1));
            
            // Nodes
            const node = this.g.append('g')
                .attr('class', 'nodes')
                .selectAll('circle')
                .data(graphData.nodes)
                .join('circle')
                .attr('r', d => d.type === 'directory' ? 8 : 5)
                .attr('fill', d => this.getNodeColor(d))
                .attr('stroke', '#fff')
                .attr('stroke-width', 1.5)
                .call(this.drag(this.simulation));
            
            node.append('title').text(d => d.label);
            
            this.simulation.on('tick', () => {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                
                node
                    .attr('cx', d => d.x)
                    .attr('cy', d => d.y);
            });
        },
        
        updateStats(nodes, links) {
            const nodeEl = document.getElementById('livemap-node-count');
            const linkEl = document.getElementById('livemap-link-count');
            if (nodeEl) nodeEl.textContent = nodes;
            if (linkEl) linkEl.textContent = links;
        },
        
        getNodeColor(d) {
            switch (d.group) {
                case 'py_file': return '#3572A5';
                case 'js_file': return '#f1e05a';
                case 'function': return '#ff7f0e';
                case 'directory': return '#6a5acd';
                default: return '#69b3a2';
            }
        },
        
        drag(simulation) {
            function dragstarted(event) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }
            
            function dragged(event) {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            }
            
            function dragended(event) {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }
            
            return d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended);
        },
        
        bind() {
            document.getElementById('livemap-refresh-btn')?.addEventListener('click', () => this.refresh());
            document.getElementById('livemap-reset-zoom')?.addEventListener('click', () => this.resetZoom());
        },
        
        init() {
            this.bind();
            this.refresh();
        }
    };
    
    // Expose globally
    window.livemapPlugin = livemapPlugin;
    window.livemapRefresh = () => livemapPlugin.refresh();
    
    // Initialize when DOM ready or immediately
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => livemapPlugin.init());
    } else {
        livemapPlugin.init();
    }
})();
"""


def get_settings_html() -> str:
    """Return HTML for the settings section."""
    return """
<section class="plugin-settings livemap-settings" id="livemap-settings">
    <header class="plugin-settings-header">
        <div>
            <p class="eyebrow">🗺️ Live Map</p>
            <h3 data-i18n="livemap_settings_title">Live Map Settings</h3>
            <p class="muted small" data-i18n="livemap_settings_hint">Configure the dependency graph visualization defaults.</p>
        </div>
        <label class="toggle-setting">
            <input type="checkbox" id="livemap-enabled" checked>
            <span data-i18n="livemap_enabled">Enable Live Map</span>
        </label>
    </header>
    <div class="settings-grid livemap-grid">
        <div class="setting-item">
            <label for="livemap-max-nodes" data-i18n="livemap_max_nodes">Max Nodes Before Simplify</label>
            <input type="number" id="livemap-max-nodes" value="1000" min="100" max="5000" step="100">
            <p class="setting-hint" data-i18n="livemap_max_nodes_hint">When file count exceeds this, simplified mode is auto-enabled.</p>
        </div>
        <div class="setting-item">
            <label for="livemap-link-distance" data-i18n="livemap_link_distance">Link Distance</label>
            <input type="number" id="livemap-link-distance" value="60" min="20" max="200" step="10">
            <p class="setting-hint" data-i18n="livemap_link_distance_hint">Distance between linked nodes. Higher = more spread out.</p>
        </div>
        <div class="setting-item">
            <label for="livemap-charge-strength" data-i18n="livemap_charge_strength">Charge Strength</label>
            <input type="number" id="livemap-charge-strength" value="-100" min="-500" max="-10" step="10">
            <p class="setting-hint" data-i18n="livemap_charge_strength_hint">Node repulsion force. More negative = more spread.</p>
        </div>
        <div class="setting-item">
            <label class="checkbox-label" for="livemap-default-simplify">
                <input type="checkbox" id="livemap-default-simplify">
                <span data-i18n="livemap_default_simplify">Simplify by Default</span>
            </label>
            <p class="setting-hint" data-i18n="livemap_default_simplify_hint">Start in simplified mode (group by folder).</p>
        </div>
        <div class="setting-item">
            <label class="checkbox-label" for="livemap-show-functions">
                <input type="checkbox" id="livemap-show-functions">
                <span data-i18n="livemap_show_functions">Show Functions as Nodes</span>
            </label>
            <p class="setting-hint" data-i18n="livemap_show_functions_hint">Include function nodes in the graph (can be slow for large projects).</p>
        </div>
    </div>
    <footer class="plugin-settings-footer">
        <button class="btn btn-primary" id="livemap-save-btn" data-i18n="save">Save</button>
        <span class="setting-result" id="livemap-settings-status">&nbsp;</span>
    </footer>
</section>

<style>
#livemap-settings .livemap-grid {
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}
#livemap-settings .setting-item {
    border: 1px solid var(--border);
    background: var(--panel-contrast);
    padding: 0.75rem;
    border-radius: var(--radius);
}
#livemap-settings .setting-item label {
    font-weight: 500;
    margin-bottom: 0.5rem;
    display: block;
}
#livemap-settings .setting-item input[type="number"] {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg);
    color: var(--fg);
}
#livemap-settings .setting-hint {
    font-size: 0.75rem;
    color: var(--fg-muted);
    margin-top: 0.25rem;
}
#livemap-settings .setting-result {
    min-width: 2rem;
    text-align: center;
}
</style>
"""


def get_settings_js() -> str:
    """Return JavaScript for the settings section."""
    return """
(function() {
    const livemapSettings = {
        getApiBaseUrl() {
            if (window.state?.apiBaseUrl) return state.apiBaseUrl;
            const origin = window.location?.origin || '';
            if (origin.includes(':8050')) return origin.replace(':8050', ':8000');
            return origin || 'http://127.0.0.1:8000';
        },
        
        getToken() {
            if (window.state?.token) return state.token;
            return localStorage.getItem('jupiter-token') || sessionStorage.getItem('jupiter-token');
        },
        
        notify(message, type = 'info') {
            if (typeof window.showNotification === 'function') {
                window.showNotification(message, type, { title: 'Live Map', icon: '🗺️' });
            } else {
                console.log('[LiveMap Settings]', message);
            }
        },
        
        buildOptions(options = {}) {
            const opts = { ...options };
            const headers = Object.assign({ Accept: 'application/json' }, opts.headers || {});
            const token = this.getToken();
            if (token && !headers.Authorization) {
                headers.Authorization = `Bearer ${token}`;
            }
            if (opts.body && typeof opts.body !== 'string') {
                headers['Content-Type'] = 'application/json';
                opts.body = JSON.stringify(opts.body);
            }
            opts.headers = headers;
            return opts;
        },
        
        async request(path, options = {}) {
            const url = path.startsWith('http') ? path : `${this.getApiBaseUrl()}${path}`;
            return fetch(url, this.buildOptions(options));
        },
        
        setStatus(text = '', variant = null) {
            const statusEl = document.getElementById('livemap-settings-status');
            if (!statusEl) return;
            statusEl.textContent = text;
            statusEl.className = 'setting-result';
            if (variant === 'error') statusEl.style.color = 'var(--error)';
            else if (variant === 'success') statusEl.style.color = 'var(--success)';
            else statusEl.style.color = '';
        },
        
        readPayload() {
            return {
                enabled: document.getElementById('livemap-enabled')?.checked ?? true,
                max_nodes: parseInt(document.getElementById('livemap-max-nodes')?.value, 10) || 1000,
                link_distance: parseInt(document.getElementById('livemap-link-distance')?.value, 10) || 60,
                charge_strength: parseInt(document.getElementById('livemap-charge-strength')?.value, 10) || -100,
                simplify: document.getElementById('livemap-default-simplify')?.checked ?? false,
                show_functions: document.getElementById('livemap-show-functions')?.checked ?? false,
            };
        },
        
        async load() {
            this.setStatus('Loading...', null);
            try {
                const resp = await this.request('/plugins/livemap/config');
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const config = await resp.json();
                
                const enabledEl = document.getElementById('livemap-enabled');
                const maxNodesEl = document.getElementById('livemap-max-nodes');
                const linkDistEl = document.getElementById('livemap-link-distance');
                const chargeEl = document.getElementById('livemap-charge-strength');
                const simplifyEl = document.getElementById('livemap-default-simplify');
                const showFuncEl = document.getElementById('livemap-show-functions');
                
                if (enabledEl) enabledEl.checked = config.enabled !== false;
                if (maxNodesEl) maxNodesEl.value = config.max_nodes ?? 1000;
                if (linkDistEl) linkDistEl.value = config.link_distance ?? 60;
                if (chargeEl) chargeEl.value = config.charge_strength ?? -100;
                if (simplifyEl) simplifyEl.checked = Boolean(config.simplify);
                if (showFuncEl) showFuncEl.checked = Boolean(config.show_functions);
                
                this.setStatus('');
            } catch (err) {
                console.error('[LiveMap Settings] Load failed:', err);
                this.setStatus('Error', 'error');
            }
        },
        
        async save() {
            const button = document.getElementById('livemap-save-btn');
            if (button) button.disabled = true;
            this.setStatus('Saving...', null);
            
            try {
                const resp = await this.request('/plugins/livemap/config', {
                    method: 'POST',
                    body: this.readPayload(),
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                this.setStatus('Saved ✓', 'success');
                this.notify('Live Map settings saved', 'success');
            } catch (err) {
                console.error('[LiveMap Settings] Save failed:', err);
                this.setStatus('Error', 'error');
                this.notify('Failed to save settings', 'error');
            } finally {
                if (button) button.disabled = false;
            }
        },
        
        bind() {
            document.getElementById('livemap-save-btn')?.addEventListener('click', (e) => {
                e.preventDefault();
                this.save();
            });
        },
        
        init() {
            this.bind();
            this.load();
        }
    };
    
    window.livemapSettings = livemapSettings;
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => livemapSettings.init());
    } else {
        livemapSettings.init();
    }
})();
"""
