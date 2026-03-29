"""
Forensics Dashboard V2 — Visually inspect agent forensics data in the browser.

Runs at http://localhost:8080.
Uses only Python's built-in http.server with no external dependencies.

V2 features:
  - Failure classification summary with severity badges
  - Guardrail pass/block visualization
  - Event search & filter (by type, action, keyword)
  - Session diff comparison (side-by-side)
  - CSV export
"""

import csv
import io
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from .store import EventStore
from .classifier import classify_failures

STORE = None  # Injected by run_dashboard()


def get_dashboard_html():
    """Main dashboard HTML."""
    sessions = STORE.get_all_sessions()
    session_buttons = "".join(
        f'<button class="session-btn" onclick="loadSession(this, \'{s}\')">{s}</button>'
        for s in sessions
    )
    session_options = "".join(
        f'<option value="{s}">{s}</option>' for s in sessions
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Agent Forensics Dashboard</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0a; color: #e0e0e0; }}

/* Header */
.header {{ background: #111; border-bottom: 1px solid #333; padding: 16px 40px; display: flex; justify-content: space-between; align-items: center; }}
.header h1 {{ font-size: 20px; color: #fff; }}
.header-right {{ display: flex; gap: 10px; align-items: center; }}
.badge {{ background: #1a73e8; color: #fff; padding: 4px 12px; border-radius: 12px; font-size: 12px; }}

/* Tabs */
.tabs {{ display: flex; background: #111; border-bottom: 1px solid #333; padding: 0 40px; }}
.tab {{ padding: 12px 24px; cursor: pointer; color: #888; font-size: 14px; border-bottom: 2px solid transparent; transition: all 0.2s; }}
.tab:hover {{ color: #ccc; }}
.tab.active {{ color: #1a73e8; border-bottom-color: #1a73e8; }}

/* Container */
.container {{ max-width: 1400px; margin: 0 auto; padding: 24px 40px; }}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}

/* Sessions */
.session-list {{ display: flex; gap: 10px; margin-bottom: 24px; flex-wrap: wrap; }}
.session-btn {{ padding: 8px 16px; border: 1px solid #333; background: #1a1a1a; color: #ccc; border-radius: 8px; cursor: pointer; font-size: 13px; transition: all 0.2s; }}
.session-btn:hover {{ border-color: #1a73e8; color: #fff; }}
.session-btn.active {{ background: #1a73e8; border-color: #1a73e8; color: #fff; }}
.session-btn.incident {{ border-color: #d93025; }}
.session-btn.incident.active {{ background: #d93025; }}

/* Summary cards */
.summary {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px; }}
.stat {{ background: #1a1a1a; border: 1px solid #333; border-radius: 10px; padding: 16px; }}
.stat .label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; }}
.stat .value {{ font-size: 24px; font-weight: 700; margin-top: 6px; color: #fff; }}
.stat.error .value {{ color: #d93025; }}
.stat.ok .value {{ color: #34a853; }}
.stat.warn .value {{ color: #f9ab00; }}

/* Filter bar */
.filter-bar {{ display: flex; gap: 10px; margin-bottom: 16px; align-items: center; }}
.filter-bar input, .filter-bar select {{ padding: 8px 12px; border: 1px solid #333; background: #1a1a1a; color: #e0e0e0; border-radius: 6px; font-size: 13px; }}
.filter-bar input {{ flex: 1; max-width: 300px; }}
.filter-bar select {{ min-width: 140px; }}
.btn {{ padding: 8px 16px; border: 1px solid #333; background: #1a1a1a; color: #ccc; border-radius: 6px; cursor: pointer; font-size: 13px; transition: all 0.2s; }}
.btn:hover {{ border-color: #1a73e8; color: #fff; }}
.btn-primary {{ background: #1a73e8; border-color: #1a73e8; color: #fff; }}
.btn-primary:hover {{ background: #1557b0; }}

/* Section */
.section {{ margin-bottom: 24px; }}
.section h2 {{ font-size: 14px; color: #888; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }}

/* Timeline */
.event {{ display: flex; gap: 12px; margin-bottom: 2px; padding: 10px 14px; background: #1a1a1a; border-left: 3px solid #333; transition: background 0.2s; align-items: flex-start; }}
.event:hover {{ background: #222; }}
.event.decision {{ border-left-color: #1a73e8; }}
.event.error {{ border-left-color: #d93025; background: #1a0a0a; }}
.event.tool_call_start {{ border-left-color: #f9ab00; }}
.event.tool_call_end {{ border-left-color: #34a853; }}
.event.final_decision {{ border-left-color: #a142f4; }}
.event.llm_call_start, .event.llm_call_end {{ border-left-color: #555; }}
.event.context_injection {{ border-left-color: #00bcd4; }}
.event.prompt_drift {{ border-left-color: #ff5722; }}
.event.prompt_state {{ border-left-color: #607d8b; }}
.event.guardrail_pass {{ border-left-color: #34a853; }}
.event.guardrail_block {{ border-left-color: #d93025; }}
.event.hidden {{ display: none; }}
.event .time {{ font-size: 11px; color: #666; font-family: monospace; min-width: 85px; flex-shrink: 0; }}
.event .type {{ font-size: 10px; font-weight: 600; min-width: 90px; padding: 2px 8px; border-radius: 4px; text-align: center; flex-shrink: 0; }}
.type-decision {{ background: #1a3a5c; color: #5b9bd5; }}
.type-error {{ background: #3a1a1a; color: #e06666; }}
.type-tool_call_start {{ background: #3a3010; color: #f9ab00; }}
.type-tool_call_end {{ background: #1a3a1a; color: #6aa84f; }}
.type-final_decision {{ background: #2a1a3a; color: #b48fe0; }}
.type-llm {{ background: #2a2a2a; color: #888; }}
.type-context {{ background: #0a2a2a; color: #00bcd4; }}
.type-drift {{ background: #2a1510; color: #ff5722; }}
.type-prompt {{ background: #1a2020; color: #607d8b; }}
.type-guard-ok {{ background: #1a2a1a; color: #34a853; }}
.type-guard-block {{ background: #3a1a1a; color: #d93025; }}
.event .detail {{ font-size: 13px; flex: 1; min-width: 0; }}
.event .detail .action {{ font-weight: 600; color: #ccc; }}
.event .detail .reasoning {{ color: #888; margin-top: 3px; font-size: 12px; word-break: break-word; }}

/* Failures */
.failure-card {{ background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 14px 16px; margin-bottom: 8px; }}
.failure-header {{ display: flex; justify-content: space-between; align-items: center; }}
.failure-type {{ font-weight: 600; font-size: 14px; color: #e0e0e0; }}
.severity {{ padding: 2px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
.severity-HIGH {{ background: #3a1a1a; color: #e06666; }}
.severity-MEDIUM {{ background: #3a3010; color: #f9ab00; }}
.severity-LOW {{ background: #1a3a1a; color: #6aa84f; }}
.failure-desc {{ color: #888; font-size: 13px; margin-top: 6px; }}
.failure-step {{ color: #666; font-size: 12px; margin-top: 4px; }}

/* Guardrails */
.guardrail-list {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 10px; }}
.guardrail-card {{ background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 14px 16px; }}
.guardrail-card.pass {{ border-left: 3px solid #34a853; }}
.guardrail-card.block {{ border-left: 3px solid #d93025; }}
.guard-status {{ font-weight: 600; font-size: 13px; }}
.guard-status.pass {{ color: #34a853; }}
.guard-status.block {{ color: #d93025; }}
.guard-detail {{ color: #888; font-size: 12px; margin-top: 4px; }}

/* Causal chain */
.causal {{ background: #111; border: 1px solid #333; border-radius: 10px; padding: 20px; font-family: monospace; font-size: 13px; line-height: 1.8; overflow-x: auto; }}
.causal .decision-node {{ color: #5b9bd5; font-weight: bold; }}
.causal .tool-node {{ color: #f9ab00; padding-left: 24px; }}
.causal .result-ok {{ color: #34a853; padding-left: 48px; }}
.causal .result-error {{ color: #d93025; padding-left: 48px; font-weight: bold; }}
.causal .final-node {{ color: #b48fe0; font-weight: bold; margin-top: 8px; }}
.causal .error-node {{ color: #d93025; padding-left: 24px; font-weight: bold; }}
.causal .context-node {{ color: #00bcd4; }}
.causal .drift-node {{ color: #ff5722; font-weight: bold; }}
.causal .guard-node {{ padding-left: 24px; }}
.causal .guard-ok {{ color: #34a853; }}
.causal .guard-block {{ color: #d93025; font-weight: bold; }}

/* Compliance */
.compliance {{ background: #1a1a1a; border: 1px solid #333; border-radius: 10px; padding: 16px; font-size: 13px; color: #888; }}
.compliance strong {{ color: #ccc; }}

/* Diff view */
.diff-controls {{ display: flex; gap: 12px; margin-bottom: 20px; align-items: center; }}
.diff-controls select {{ padding: 8px 12px; border: 1px solid #333; background: #1a1a1a; color: #e0e0e0; border-radius: 6px; font-size: 13px; min-width: 200px; }}
.diff-panels {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
.diff-panel {{ background: #1a1a1a; border: 1px solid #333; border-radius: 10px; padding: 16px; overflow: auto; max-height: 600px; }}
.diff-panel h3 {{ font-size: 13px; color: #888; margin-bottom: 12px; text-transform: uppercase; }}
.diff-event {{ padding: 6px 10px; margin-bottom: 2px; border-radius: 4px; font-size: 12px; font-family: monospace; }}
.diff-match {{ background: #1a1a1a; color: #888; }}
.diff-diverge {{ background: #2a1a10; color: #f9ab00; border-left: 2px solid #f9ab00; }}
.diff-missing {{ background: #1a0a0a; color: #d93025; border-left: 2px solid #d93025; }}
.diff-extra {{ background: #0a1a0a; color: #34a853; border-left: 2px solid #34a853; }}

/* Multi-agent */
.agent-cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; margin-bottom: 16px; }}
.agent-card {{ background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 14px; border-top: 3px solid #1a73e8; }}
.agent-card .agent-name {{ font-weight: 700; font-size: 14px; color: #fff; margin-bottom: 8px; }}
.agent-card .agent-stat {{ font-size: 12px; color: #888; margin: 2px 0; }}
.agent-card .agent-stat span {{ color: #ccc; font-weight: 600; }}
.handoff-flow {{ display: flex; align-items: center; gap: 0; flex-wrap: wrap; margin-bottom: 16px; padding: 16px; background: #111; border: 1px solid #333; border-radius: 10px; }}
.handoff-node {{ background: #1a3a5c; color: #5b9bd5; padding: 8px 16px; border-radius: 6px; font-weight: 600; font-size: 13px; }}
.handoff-arrow {{ color: #f9ab00; font-size: 20px; margin: 0 8px; }}
.event.handoff {{ border-left-color: #f9ab00; background: #1a1a0a; }}
.type-handoff {{ background: #3a3010; color: #f9ab00; }}

#session-content {{ min-height: 300px; }}
</style>
</head>
<body>

<div class="header">
    <h1>Agent Forensics Dashboard</h1>
    <div class="header-right">
        <span class="badge">v2</span>
    </div>
</div>

<div class="tabs">
    <div class="tab active" onclick="switchTab('inspector')">Session Inspector</div>
    <div class="tab" onclick="switchTab('diff')">Session Diff</div>
</div>

<div class="container">

<!-- TAB 1: Session Inspector -->
<div class="tab-content active" id="tab-inspector">
    <div class="session-list" id="session-list">
        {session_buttons}
    </div>
    <div id="session-content">
        <p style="color:#666; text-align:center; padding:60px;">Select a session to inspect</p>
    </div>
</div>

<!-- TAB 2: Session Diff -->
<div class="tab-content" id="tab-diff">
    <div class="diff-controls">
        <label style="color:#888;">Session A:</label>
        <select id="diff-a"><option value="">Select...</option>{session_options}</select>
        <label style="color:#888;">Session B:</label>
        <select id="diff-b"><option value="">Select...</option>{session_options}</select>
        <button class="btn btn-primary" onclick="runDiff()">Compare</button>
    </div>
    <div id="diff-result"></div>
</div>

</div>

<script>
let currentEvents = [];
let currentSessionId = '';

/* ── Tab switching ── */
function switchTab(tab) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector(`.tab-content#tab-${{tab}}`).classList.add('active');
    event.target.classList.add('active');
}}

/* ── Session loading ── */
async function loadSession(btn, sessionId) {{
    document.querySelectorAll('.session-btn').forEach(b => b.classList.remove('active', 'incident'));
    btn.classList.add('active');
    currentSessionId = sessionId;

    const res = await fetch('/api/session?id=' + sessionId);
    const data = await res.json();
    currentEvents = data.events;
    renderSession(data);
}}

/* ── Main render ── */
function renderSession(data) {{
    const events = data.events;
    const failures = data.failures || [];
    const decisions = events.filter(e => e.event_type === 'decision');
    const errors = events.filter(e => e.event_type === 'error');
    const guardrails = events.filter(e => e.event_type === 'guardrail_pass' || e.event_type === 'guardrail_block');
    const hasIncident = errors.length > 0 || failures.length > 0 || events.some(e =>
        JSON.stringify(e.output_data).toLowerCase().includes('error') ||
        JSON.stringify(e.output_data).toLowerCase().includes('fail')
    );

    let html = '';

    /* Summary cards */
    html += '<div class="summary">';
    html += `<div class="stat"><div class="label">Events</div><div class="value">${{events.length}}</div></div>`;
    html += `<div class="stat"><div class="label">Decisions</div><div class="value">${{decisions.length}}</div></div>`;
    html += `<div class="stat ${{errors.length > 0 ? 'error' : 'ok'}}"><div class="label">Errors</div><div class="value">${{errors.length}}</div></div>`;
    html += `<div class="stat ${{failures.length > 0 ? 'warn' : 'ok'}}"><div class="label">Failures</div><div class="value">${{failures.length}}</div></div>`;
    html += `<div class="stat ${{hasIncident ? 'error' : 'ok'}}"><div class="label">Status</div><div class="value">${{hasIncident ? 'INCIDENT' : 'OK'}}</div></div>`;
    html += '</div>';

    /* Multi-Agent Section */
    const agentStats = data.agent_stats || {{}};
    const agents = agentStats.agents || {{}};
    const handoffList = agentStats.handoffs || [];
    const agentNames = Object.keys(agents);

    if (agentNames.length > 1 || handoffList.length > 0) {{
        html += '<div class="section"><h2>Multi-Agent Overview</h2>';

        // Handoff flow
        if (handoffList.length > 0) {{
            html += '<div class="handoff-flow">';
            const chain = agentStats.handoff_chain || [];
            chain.forEach((a, i) => {{
                html += `<div class="handoff-node">${{esc(a)}}</div>`;
                if (i < chain.length - 1) html += '<div class="handoff-arrow">&rarr;</div>';
            }});
            html += '</div>';
        }}

        // Per-agent cards
        html += '<div class="agent-cards">';
        const colors = ['#1a73e8', '#34a853', '#a142f4', '#f9ab00', '#d93025', '#00bcd4'];
        agentNames.forEach((name, idx) => {{
            const a = agents[name];
            const failCount = (a.failures || []).length;
            const color = colors[idx % colors.length];
            html += `<div class="agent-card" style="border-top-color:${{color}}">`;
            html += `<div class="agent-name">${{esc(name)}}</div>`;
            html += `<div class="agent-stat">Events: <span>${{a.events}}</span></div>`;
            html += `<div class="agent-stat">Decisions: <span>${{a.decisions}}</span></div>`;
            html += `<div class="agent-stat">Tools: <span>${{a.tools}}</span></div>`;
            html += `<div class="agent-stat">Errors: <span>${{a.errors}}</span></div>`;
            if (failCount > 0) html += `<div class="agent-stat" style="color:#d93025">Failures: <span style="color:#d93025">${{failCount}}</span></div>`;
            html += '</div>';
        }});
        html += '</div></div>';
    }}

    /* Failure Classification */
    if (failures.length > 0) {{
        html += '<div class="section"><h2>Failure Classification</h2>';
        failures.forEach(f => {{
            html += `<div class="failure-card">`;
            html += `<div class="failure-header"><span class="failure-type">${{f.type}}</span><span class="severity severity-${{f.severity}}">${{f.severity}}</span></div>`;
            html += `<div class="failure-desc">${{esc(f.description)}}</div>`;
            html += `<div class="failure-step">Step ${{f.step}}</div>`;
            html += `</div>`;
        }});
        html += '</div>';
    }}

    /* Guardrail Checkpoints */
    if (guardrails.length > 0) {{
        html += '<div class="section"><h2>Guardrail Checkpoints</h2><div class="guardrail-list">';
        guardrails.forEach(g => {{
            const allowed = g.input_data.allowed;
            const cls = allowed ? 'pass' : 'block';
            html += `<div class="guardrail-card ${{cls}}">`;
            html += `<div class="guard-status ${{cls}}">${{allowed ? 'ALLOWED' : 'BLOCKED'}}</div>`;
            html += `<div class="guard-detail"><strong>Intent:</strong> ${{esc(g.input_data.intent || '')}}</div>`;
            html += `<div class="guard-detail"><strong>Action:</strong> ${{esc(g.input_data.action || '')}}</div>`;
            html += `<div class="guard-detail">${{esc(g.reasoning)}}</div>`;
            html += `</div>`;
        }});
        html += '</div></div>';
    }}

    /* Filter bar + Export */
    html += '<div class="section"><h2>Timeline</h2>';
    html += '<div class="filter-bar">';
    html += '<input type="text" id="filter-keyword" placeholder="Search action or reasoning..." oninput="applyFilters()">';
    html += '<select id="filter-type" onchange="applyFilters()"><option value="">All types</option>';
    const types = [...new Set(events.map(e => e.event_type))].sort();
    types.forEach(t => {{ html += `<option value="${{t}}">${{t}}</option>`; }});
    html += '</select>';
    html += `<button class="btn" onclick="exportCSV()">Export CSV</button>`;
    html += '</div>';

    /* Timeline events */
    html += '<div class="timeline" id="timeline">';
    events.forEach((e, i) => {{
        const time = e.timestamp.split('T')[1].split('+')[0].substring(0, 12);
        const typeClass = getTypeClass(e.event_type);
        const typeLabel = getTypeLabel(e.event_type);
        const detail = extractDetail(e);

        html += `<div class="event ${{e.event_type}}" data-type="${{e.event_type}}" data-action="${{esc(e.action).toLowerCase()}}" data-reasoning="${{esc(e.reasoning).toLowerCase()}}">`;
        html += `<span class="time">${{time}}</span>`;
        html += `<span class="type type-${{typeClass}}">${{typeLabel}}</span>`;
        html += `<div class="detail"><div class="action">${{esc(e.action)}}</div><div class="reasoning">${{esc(detail)}}</div></div>`;
        html += '</div>';
    }});
    html += '</div></div>';

    /* Causal Chain */
    if (hasIncident) {{
        html += '<div class="section"><h2>Causal Chain</h2><div class="causal">';
        events.forEach(e => {{
            if (e.event_type === 'decision') {{
                html += `<div class="decision-node">[DECISION] ${{esc(e.action)}}</div>`;
                html += `<div style="padding-left:24px;color:#666">${{esc(truncate(e.reasoning, 150))}}</div>`;
            }} else if (e.event_type === 'tool_call_start') {{
                html += `<div class="tool-node">&rarr; [TOOL] ${{esc(e.action)}}</div>`;
            }} else if (e.event_type === 'tool_call_end') {{
                const result = JSON.stringify(e.output_data);
                const isErr = result.toLowerCase().includes('error') || result.toLowerCase().includes('fail');
                html += `<div class="${{isErr ? 'result-error' : 'result-ok'}}">${{isErr ? '&#10007;' : '&#10003;'}} ${{esc(truncate(result, 120))}}</div>`;
            }} else if (e.event_type === 'error') {{
                html += `<div class="error-node">&#10007; ERROR: ${{esc(truncate(JSON.stringify(e.output_data), 150))}}</div>`;
            }} else if (e.event_type === 'context_injection') {{
                html += `<div class="context-node">[CONTEXT] ${{esc(e.action)}} &mdash; ${{esc(truncate(e.reasoning, 100))}}</div>`;
            }} else if (e.event_type === 'prompt_drift') {{
                html += `<div class="drift-node">[*** PROMPT DRIFT ***]</div>`;
            }} else if (e.event_type === 'guardrail_pass') {{
                html += `<div class="guard-node guard-ok">[GUARD OK] ${{esc(e.input_data.action || '')}}</div>`;
            }} else if (e.event_type === 'guardrail_block') {{
                html += `<div class="guard-node guard-block">[GUARD BLOCKED] ${{esc(e.input_data.action || '')}}</div>`;
            }} else if (e.event_type === 'handoff') {{
                html += `<div class="drift-node">[HANDOFF] ${{esc(e.input_data.from_agent || '')}} &rarr; ${{esc(e.input_data.to_agent || '')}}</div>`;
                html += `<div style="padding-left:24px;color:#666">${{esc(truncate(e.reasoning, 150))}}</div>`;
            }} else if (e.event_type === 'final_decision') {{
                html += `<div class="final-node">[FINAL] ${{esc(truncate(e.output_data.response || JSON.stringify(e.output_data), 150))}}</div>`;
            }}
        }});
        html += '</div></div>';
    }}

    /* Compliance */
    const contextInj = events.filter(e => e.event_type === 'context_injection').length;
    const promptDrifts = events.filter(e => e.event_type === 'prompt_drift').length;
    const guardPasses = events.filter(e => e.event_type === 'guardrail_pass').length;
    const guardBlocks = events.filter(e => e.event_type === 'guardrail_block').length;
    html += '<div class="section"><h2>Compliance</h2><div class="compliance">';
    html += '<p><strong>EU AI Act Article 14</strong> &mdash; Human Oversight requirement supported.</p>';
    html += `<p>Events: ${{events.length}} | Decisions: ${{decisions.length}} | Errors: ${{errors.length}} | Failures: ${{failures.length}}</p>`;
    html += `<p>Context injections: ${{contextInj}} | Prompt drifts: ${{promptDrifts}} | Guardrails: ${{guardPasses}} passed, ${{guardBlocks}} blocked</p>`;
    html += '</div></div>';

    document.getElementById('session-content').innerHTML = html;

    /* Update button style */
    document.querySelectorAll('.session-btn.active').forEach(btn => {{
        if (hasIncident) btn.classList.add('incident');
    }});
}}

/* ── Filters ── */
function applyFilters() {{
    const keyword = document.getElementById('filter-keyword').value.toLowerCase();
    const typeFilter = document.getElementById('filter-type').value;
    document.querySelectorAll('#timeline .event').forEach(el => {{
        const matchType = !typeFilter || el.dataset.type === typeFilter;
        const matchKeyword = !keyword ||
            el.dataset.action.includes(keyword) ||
            el.dataset.reasoning.includes(keyword);
        el.classList.toggle('hidden', !(matchType && matchKeyword));
    }});
}}

/* ── CSV Export ── */
function exportCSV() {{
    if (!currentSessionId) return;
    window.location.href = '/api/export?id=' + currentSessionId;
}}

/* ── Session Diff ── */
async function runDiff() {{
    const a = document.getElementById('diff-a').value;
    const b = document.getElementById('diff-b').value;
    if (!a || !b) {{ alert('Select two sessions to compare.'); return; }}

    const res = await fetch(`/api/diff?a=${{a}}&b=${{b}}`);
    const data = await res.json();
    renderDiff(data);
}}

function renderDiff(data) {{
    let html = '';

    /* Summary */
    html += '<div class="summary" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 20px;">';
    html += `<div class="stat"><div class="label">Session A Events</div><div class="value">${{data.original_events}}</div></div>`;
    html += `<div class="stat"><div class="label">Session B Events</div><div class="value">${{data.replay_events}}</div></div>`;
    html += `<div class="stat ${{data.matching ? 'ok' : 'error'}}"><div class="label">Matching</div><div class="value">${{data.matching ? 'YES' : 'NO'}}</div></div>`;
    html += `<div class="stat ${{data.divergences.length > 0 ? 'warn' : 'ok'}}"><div class="label">Divergences</div><div class="value">${{data.divergences.length}}</div></div>`;
    html += '</div>';

    /* Side-by-side panels */
    html += '<div class="diff-panels">';

    /* Panel A */
    html += `<div class="diff-panel"><h3>${{esc(data.original_session)}}</h3>`;
    data.steps_a.forEach((step, i) => {{
        const div = getDivergence(data.divergences, i + 1);
        const cls = div ? (div.type === 'missing_in_replay' ? 'diff-missing' : 'diff-diverge') : 'diff-match';
        html += `<div class="diff-event ${{cls}}">${{i+1}}. [${{step.type}}] ${{esc(truncate(step.action, 60))}}</div>`;
    }});
    html += '</div>';

    /* Panel B */
    html += `<div class="diff-panel"><h3>${{esc(data.replay_session)}}</h3>`;
    data.steps_b.forEach((step, i) => {{
        const div = getDivergence(data.divergences, i + 1);
        const cls = div ? (div.type === 'extra_in_replay' ? 'diff-extra' : 'diff-diverge') : 'diff-match';
        html += `<div class="diff-event ${{cls}}">${{i+1}}. [${{step.type}}] ${{esc(truncate(step.action, 60))}}</div>`;
    }});
    html += '</div>';

    html += '</div>';

    document.getElementById('diff-result').innerHTML = html;
}}

function getDivergence(divergences, step) {{
    return divergences.find(d => d.step === step);
}}

/* ── Helpers ── */
function getTypeClass(t) {{
    const map = {{
        'context_injection': 'context',
        'prompt_drift': 'drift',
        'prompt_state': 'prompt',
        'guardrail_pass': 'guard-ok',
        'guardrail_block': 'guard-block',
        'handoff': 'handoff',
    }};
    if (t.startsWith('llm')) return 'llm';
    return map[t] || t;
}}

function getTypeLabel(t) {{
    const map = {{
        'llm_call_start': 'LLM REQ', 'llm_call_end': 'LLM RES',
        'tool_call_start': 'TOOL REQ', 'tool_call_end': 'TOOL RES',
        'decision': 'DECISION', 'final_decision': 'FINAL', 'error': 'ERROR',
        'context_injection': 'CONTEXT', 'prompt_state': 'PROMPT',
        'prompt_drift': 'DRIFT', 'guardrail_pass': 'GUARD OK', 'guardrail_block': 'BLOCKED',
        'handoff': 'HANDOFF',
    }};
    return map[t] || t;
}}

function extractDetail(e) {{
    if (e.event_type === 'llm_call_start') {{
        const msgs = e.input_data.messages || [];
        if (msgs.length > 0) {{ const last = msgs[msgs.length - 1]; return truncate(`[${{last.role}}] ${{last.content}}`, 150); }}
        return '';
    }}
    if (e.event_type === 'decision') return truncate(e.reasoning, 150);
    if (e.event_type === 'final_decision') return truncate(e.output_data.response || e.reasoning, 150);
    if (e.event_type === 'tool_call_start') return truncate(JSON.stringify(e.input_data), 150);
    if (e.event_type === 'tool_call_end') return truncate(JSON.stringify(e.output_data), 150);
    if (e.event_type === 'error') return truncate(JSON.stringify(e.output_data), 150);
    if (e.event_type === 'context_injection') return truncate(`${{e.action}} — ${{e.reasoning}}`, 150);
    if (e.event_type === 'prompt_drift') {{
        const diff = e.input_data.diff || {{}};
        return `+${{(diff.added||[]).length}} lines, -${{(diff.removed||[]).length}} lines changed`;
    }}
    if (e.event_type === 'guardrail_pass' || e.event_type === 'guardrail_block') {{
        const a = e.input_data.allowed ? 'ALLOWED' : 'BLOCKED';
        return `${{a}}: ${{e.input_data.intent || ''}} → ${{e.input_data.action || ''}}`;
    }}
    if (e.event_type === 'handoff') {{
        return `${{e.input_data.from_agent || ''}} → ${{e.input_data.to_agent || ''}}: ${{truncate(e.reasoning, 100)}}`;
    }}
    return truncate(e.reasoning, 150);
}}

function truncate(text, max) {{
    if (!text) return '';
    return text.length > max ? text.substring(0, max) + '...' : text;
}}

function esc(text) {{
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}}
</script>
</body>
</html>"""


def _compute_agent_stats(events, failures):
    """Compute per-agent breakdown for multi-agent visualization."""
    agents = {}
    handoffs = []

    for e in events:
        aid = e.agent_id
        if aid not in agents:
            agents[aid] = {"events": 0, "decisions": 0, "errors": 0, "tools": 0, "failures": []}
        agents[aid]["events"] += 1
        if e.event_type == "decision":
            agents[aid]["decisions"] += 1
        elif e.event_type == "error":
            agents[aid]["errors"] += 1
        elif e.event_type in ("tool_call_start", "tool_call_end"):
            agents[aid]["tools"] += 1
        elif e.event_type == "handoff":
            handoffs.append({
                "from": e.input_data.get("from_agent", ""),
                "to": e.input_data.get("to_agent", ""),
                "reasoning": e.reasoning,
            })

    # Map failures to agents
    for f in failures:
        step = f["step"] - 1
        if 0 <= step < len(events):
            aid = events[step].agent_id
            if aid in agents:
                agents[aid]["failures"].append({"type": f["type"], "severity": f["severity"]})

    chain = []
    if handoffs:
        chain.append(handoffs[0]["from"])
        for h in handoffs:
            chain.append(h["to"])

    return {
        "agents": agents,
        "handoffs": handoffs,
        "handoff_chain": chain,
        "total_agents": len(agents),
        "is_multi_agent": len(agents) > 1,
    }


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "":
            self._html(get_dashboard_html())

        elif parsed.path == "/api/session":
            params = parse_qs(parsed.query)
            session_id = params.get("id", [""])[0]
            events = STORE.get_session_events(session_id)
            failures = classify_failures(events)

            event_dicts = [
                {
                    "event_id": e.event_id,
                    "timestamp": e.timestamp,
                    "event_type": e.event_type,
                    "agent_id": e.agent_id,
                    "action": e.action,
                    "input_data": e.input_data,
                    "output_data": e.output_data,
                    "reasoning": e.reasoning,
                }
                for e in events
            ]

            # Compute agent stats for multi-agent sessions
            agent_stats = _compute_agent_stats(events, failures)

            self._json({"events": event_dicts, "failures": failures, "agent_stats": agent_stats})

        elif parsed.path == "/api/diff":
            params = parse_qs(parsed.query)
            a = params.get("a", [""])[0]
            b = params.get("b", [""])[0]

            events_a = STORE.get_session_events(a)
            events_b = STORE.get_session_events(b)

            # Build step lists for side-by-side display
            steps_a = [{"type": e.event_type, "action": e.action} for e in events_a]
            steps_b = [{"type": e.event_type, "action": e.action} for e in events_b]

            # Compute divergences (simplified — compare decision sequences)
            decisions_a = [
                {"action": e.action, "output": e.output_data}
                for e in events_a
                if e.event_type in ("decision", "final_decision", "tool_call_end")
            ]
            decisions_b = [
                {"action": e.action, "output": e.output_data}
                for e in events_b
                if e.event_type in ("decision", "final_decision", "tool_call_end")
            ]

            divergences = []
            max_len = max(len(decisions_a), len(decisions_b))
            for i in range(max_len):
                da = decisions_a[i] if i < len(decisions_a) else None
                db = decisions_b[i] if i < len(decisions_b) else None
                if da is None:
                    divergences.append({"step": i + 1, "type": "extra_in_replay"})
                elif db is None:
                    divergences.append({"step": i + 1, "type": "missing_in_replay"})
                elif da["action"] != db["action"] or da["output"] != db["output"]:
                    divergences.append({"step": i + 1, "type": "diverged"})

            self._json({
                "original_session": a,
                "replay_session": b,
                "original_events": len(events_a),
                "replay_events": len(events_b),
                "matching": len(divergences) == 0,
                "divergences": divergences,
                "steps_a": steps_a,
                "steps_b": steps_b,
            })

        elif parsed.path == "/api/export":
            params = parse_qs(parsed.query)
            session_id = params.get("id", [""])[0]
            events = STORE.get_session_events(session_id)

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["#", "timestamp", "event_type", "agent_id", "action", "input_data", "output_data", "reasoning"])
            for i, e in enumerate(events, 1):
                writer.writerow([
                    i, e.timestamp, e.event_type, e.agent_id, e.action,
                    json.dumps(e.input_data, ensure_ascii=False),
                    json.dumps(e.output_data, ensure_ascii=False),
                    e.reasoning,
                ])

            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="forensics-{session_id}.csv"')
            self.end_headers()
            self.wfile.write(output.getvalue().encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def _html(self, content):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        """Suppress log output."""
        pass


def run_dashboard(store: EventStore, port: int = 8080):
    """Start the dashboard server."""
    global STORE
    STORE = store
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"\n  Agent Forensics Dashboard v2")
    print(f"  http://localhost:{port}")
    print(f"  Press Ctrl+C to stop\n")
    server.serve_forever()


if __name__ == "__main__":
    run_dashboard(EventStore("forensics.db"))
