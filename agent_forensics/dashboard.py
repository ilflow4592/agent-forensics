"""
Forensics Dashboard — Visually inspect agent forensics data in the browser.

Runs at http://localhost:8080.
Uses only Python's built-in http.server with no external dependencies.
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from .store import EventStore

STORE = None  # Injected by run_dashboard()


def get_dashboard_html():
    """Main dashboard HTML."""
    sessions = STORE.get_all_sessions()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Agent Forensics Dashboard</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0a; color: #e0e0e0; }}
.header {{ background: #111; border-bottom: 1px solid #333; padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; }}
.header h1 {{ font-size: 20px; color: #fff; }}
.header .badge {{ background: #1a73e8; color: #fff; padding: 4px 12px; border-radius: 12px; font-size: 12px; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 30px 40px; }}
.session-list {{ display: flex; gap: 12px; margin-bottom: 30px; flex-wrap: wrap; }}
.session-btn {{ padding: 10px 20px; border: 1px solid #333; background: #1a1a1a; color: #ccc; border-radius: 8px; cursor: pointer; font-size: 14px; transition: all 0.2s; }}
.session-btn:hover {{ border-color: #1a73e8; color: #fff; }}
.session-btn.active {{ background: #1a73e8; border-color: #1a73e8; color: #fff; }}
.session-btn.incident {{ border-color: #d93025; }}
.session-btn.incident.active {{ background: #d93025; }}
.summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 30px; }}
.stat {{ background: #1a1a1a; border: 1px solid #333; border-radius: 10px; padding: 20px; }}
.stat .label {{ font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; }}
.stat .value {{ font-size: 28px; font-weight: 700; margin-top: 8px; color: #fff; }}
.stat.error .value {{ color: #d93025; }}
.stat.ok .value {{ color: #34a853; }}
.section {{ margin-bottom: 30px; }}
.section h2 {{ font-size: 16px; color: #888; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 1px; }}
.timeline {{ position: relative; }}
.event {{ display: flex; gap: 16px; margin-bottom: 2px; padding: 12px 16px; background: #1a1a1a; border-left: 3px solid #333; transition: background 0.2s; }}
.event:hover {{ background: #222; }}
.event.decision {{ border-left-color: #1a73e8; }}
.event.error {{ border-left-color: #d93025; background: #1a0a0a; }}
.event.tool_call_start {{ border-left-color: #f9ab00; }}
.event.tool_call_end {{ border-left-color: #34a853; }}
.event.final_decision {{ border-left-color: #a142f4; }}
.event.llm_call_start {{ border-left-color: #555; }}
.event.llm_call_end {{ border-left-color: #555; }}
.event .time {{ font-size: 11px; color: #666; font-family: monospace; min-width: 90px; }}
.event .type {{ font-size: 11px; font-weight: 600; min-width: 100px; padding: 2px 8px; border-radius: 4px; text-align: center; }}
.type-decision {{ background: #1a3a5c; color: #5b9bd5; }}
.type-error {{ background: #3a1a1a; color: #e06666; }}
.type-tool_call_start {{ background: #3a3010; color: #f9ab00; }}
.type-tool_call_end {{ background: #1a3a1a; color: #6aa84f; }}
.type-final_decision {{ background: #2a1a3a; color: #b48fe0; }}
.type-llm {{ background: #2a2a2a; color: #888; }}
.event .detail {{ font-size: 13px; flex: 1; }}
.event .detail .action {{ font-weight: 600; color: #ccc; }}
.event .detail .reasoning {{ color: #888; margin-top: 4px; font-size: 12px; }}
.causal {{ background: #111; border: 1px solid #333; border-radius: 10px; padding: 24px; font-family: monospace; font-size: 13px; line-height: 1.8; overflow-x: auto; }}
.causal .node {{ margin: 4px 0; }}
.causal .decision-node {{ color: #5b9bd5; font-weight: bold; }}
.causal .tool-node {{ color: #f9ab00; padding-left: 24px; }}
.causal .result-ok {{ color: #34a853; padding-left: 48px; }}
.causal .result-error {{ color: #d93025; padding-left: 48px; font-weight: bold; }}
.causal .final-node {{ color: #b48fe0; font-weight: bold; margin-top: 8px; }}
.causal .error-node {{ color: #d93025; padding-left: 24px; font-weight: bold; }}
#session-content {{ min-height: 400px; }}
.compliance {{ background: #1a1a1a; border: 1px solid #333; border-radius: 10px; padding: 20px; font-size: 13px; color: #888; }}
.compliance strong {{ color: #ccc; }}
</style>
</head>
<body>

<div class="header">
    <h1>Agent Forensics Dashboard</h1>
    <span class="badge">PoC v0.1</span>
</div>

<div class="container">
    <div class="session-list" id="session-list">
        {''.join(f'<button class="session-btn" onclick="loadSession(this, \'{s}\')">{s}</button>' for s in sessions)}
    </div>
    <div id="session-content">
        <p style="color:#666; text-align:center; padding:60px;">Select a session</p>
    </div>
</div>

<script>
async function loadSession(btn, sessionId) {{
    document.querySelectorAll('.session-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const res = await fetch('/api/session?id=' + sessionId);
    const data = await res.json();
    renderSession(data);
}}

function renderSession(data) {{
    const events = data.events;
    const decisions = events.filter(e => e.event_type === 'decision');
    const errors = events.filter(e => e.event_type === 'error');
    const hasIncident = errors.length > 0 || events.some(e =>
        JSON.stringify(e.output_data).toLowerCase().includes('error') ||
        JSON.stringify(e.output_data).toLowerCase().includes('fail')
    );

    let html = '';

    // Summary
    html += '<div class="summary">';
    html += `<div class="stat"><div class="label">Total Events</div><div class="value">${{events.length}}</div></div>`;
    html += `<div class="stat"><div class="label">Decisions</div><div class="value">${{decisions.length}}</div></div>`;
    html += `<div class="stat ${{errors.length > 0 ? 'error' : 'ok'}}"><div class="label">Errors</div><div class="value">${{errors.length}}</div></div>`;
    html += `<div class="stat ${{hasIncident ? 'error' : 'ok'}}"><div class="label">Status</div><div class="value">${{hasIncident ? 'INCIDENT' : 'OK'}}</div></div>`;
    html += '</div>';

    // Timeline
    html += '<div class="section"><h2>Timeline</h2><div class="timeline">';
    events.forEach((e, i) => {{
        const time = e.timestamp.split('T')[1].split('+')[0].substring(0, 12);
        const typeClass = e.event_type.startsWith('llm') ? 'llm' : e.event_type;
        const typeLabel = {{
            'llm_call_start': 'LLM REQ',
            'llm_call_end': 'LLM RES',
            'tool_call_start': 'TOOL REQ',
            'tool_call_end': 'TOOL RES',
            'decision': 'DECISION',
            'final_decision': 'FINAL',
            'error': 'ERROR'
        }}[e.event_type] || e.event_type;

        const detail = extractDetail(e);

        html += `<div class="event ${{e.event_type}}">`;
        html += `<span class="time">${{time}}</span>`;
        html += `<span class="type type-${{typeClass}}">${{typeLabel}}</span>`;
        html += `<div class="detail"><div class="action">${{e.action}}</div><div class="reasoning">${{detail}}</div></div>`;
        html += '</div>';
    }});
    html += '</div></div>';

    // Causal Chain
    if (hasIncident) {{
        html += '<div class="section"><h2>Causal Chain (Root Cause Analysis)</h2><div class="causal">';
        events.forEach(e => {{
            if (e.event_type === 'decision') {{
                html += `<div class="node decision-node">[DECISION] ${{e.action}}</div>`;
                html += `<div class="node" style="padding-left:24px;color:#666">${{truncate(e.reasoning, 150)}}</div>`;
            }} else if (e.event_type === 'tool_call_start') {{
                html += `<div class="node tool-node">→ [TOOL] ${{e.action}}</div>`;
            }} else if (e.event_type === 'tool_call_end') {{
                const result = JSON.stringify(e.output_data);
                const isErr = result.toLowerCase().includes('error') || result.toLowerCase().includes('fail');
                html += `<div class="node ${{isErr ? 'result-error' : 'result-ok'}}">${{isErr ? '✗' : '✓'}} ${{truncate(result, 120)}}</div>`;
            }} else if (e.event_type === 'error') {{
                html += `<div class="node error-node">✗ ERROR: ${{truncate(JSON.stringify(e.output_data), 150)}}</div>`;
            }} else if (e.event_type === 'final_decision') {{
                html += `<div class="node final-node">[FINAL] ${{truncate(e.output_data.response || JSON.stringify(e.output_data), 150)}}</div>`;
            }}
        }});
        html += '</div></div>';
    }}

    // Compliance
    html += '<div class="section"><h2>Compliance</h2><div class="compliance">';
    html += '<p><strong>EU AI Act Article 14</strong> — Human Oversight requirement supported.</p>';
    html += `<p>All ${{decisions.length}} decision points recorded. ${{errors.length}} errors captured.</p>`;
    html += '</div></div>';

    document.getElementById('session-content').innerHTML = html;

    // Update button style
    document.querySelectorAll('.session-btn.active').forEach(btn => {{
        if (hasIncident) btn.classList.add('incident');
        else btn.classList.remove('incident');
    }});
}}

function extractDetail(e) {{
    if (e.event_type === 'llm_call_start') {{
        const msgs = e.input_data.messages || [];
        if (msgs.length > 0) {{
            const last = msgs[msgs.length - 1];
            return truncate(`[${{last.role}}] ${{last.content}}`, 150);
        }}
        return '';
    }}
    if (e.event_type === 'decision') return truncate(e.reasoning, 150);
    if (e.event_type === 'final_decision') return truncate(e.output_data.response || e.reasoning, 150);
    if (e.event_type === 'tool_call_start') return truncate(JSON.stringify(e.input_data), 150);
    if (e.event_type === 'tool_call_end') return truncate(JSON.stringify(e.output_data), 150);
    if (e.event_type === 'error') return truncate(JSON.stringify(e.output_data), 150);
    return truncate(e.reasoning, 150);
}}

function truncate(text, max) {{
    if (!text) return '';
    return text.length > max ? text.substring(0, max) + '...' : text;
}}
</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(get_dashboard_html().encode("utf-8"))

        elif parsed.path == "/api/session":
            params = parse_qs(parsed.query)
            session_id = params.get("id", [""])[0]
            events = STORE.get_session_events(session_id)

            event_dicts = []
            for e in events:
                event_dicts.append({
                    "event_id": e.event_id,
                    "timestamp": e.timestamp,
                    "event_type": e.event_type,
                    "agent_id": e.agent_id,
                    "action": e.action,
                    "input_data": e.input_data,
                    "output_data": e.output_data,
                    "reasoning": e.reasoning,
                })

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"events": event_dicts}, ensure_ascii=False).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress log output."""
        pass


def run_dashboard(store: EventStore, port: int = 8080):
    """Start the dashboard server."""
    global STORE
    STORE = store
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"\n  Agent Forensics Dashboard")
    print(f"  http://localhost:{port}")
    print(f"  Press Ctrl+C to stop\n")
    server.serve_forever()


if __name__ == "__main__":
    run_dashboard(EventStore("forensics.db"))
