"""PIN-protected local control page."""

from __future__ import annotations

from collections import defaultdict, deque
from functools import wraps
import hmac
import os
from pathlib import Path
import secrets
import tempfile
import time

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)

from .config import AppConfig
from .m3u import parse_m3u

LOGIN_HTML = """
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pocket IPTV Login</title><style>{{ css }}</style></head>
<body><main class="narrow"><h1>Pocket IPTV</h1><p>Local control page</p>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
<form method="post"><label>Six-digit PIN<input name="pin" inputmode="numeric"
autocomplete="one-time-code" required autofocus></label>
<button type="submit">Unlock</button></form></main></body></html>
"""

CONTROL_HTML = """
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pocket IPTV</title><style>{{ css }}</style></head><body>
<main><header><div><h1>Pocket IPTV</h1><p id="connection">Loading…</p></div>
<a class="small" href="{{ url_for('logout') }}">Lock</a></header>
<section class="now"><span id="counter">—</span><h2 id="name">Loading…</h2>
<p id="group"></p><p id="error" class="error"></p></section>
<section class="controls">
<button data-command="prev">◀ Prev</button>
<button data-command="toggle" id="toggle">Pause</button>
<button data-command="next">Next ▶</button>
<button data-command="vol_down">Volume −</button>
<button data-command="vol_up">Volume +</button></section>
<h2>Channels</h2><div id="channels" class="channels"></div>
<details><summary>Replace playlist</summary>
<form action="{{ url_for('upload_playlist') }}" method="post" enctype="multipart/form-data">
<input type="hidden" name="csrf" value="{{ csrf }}">
<label>M3U file<input type="file" name="playlist" accept=".m3u,.m3u8,text/plain"></label>
<label>Or paste M3U<textarea name="playlist_text" rows="8"></textarea></label>
<button type="submit">Validate and replace</button></form></details>
<p class="foot">Private URLs stay on this Pi. Never expose port 8080 to the internet.</p>
</main><script>
const csrf={{ csrf|tojson }};
async function command(command,index=null){
 const body={command}; if(index!==null) body.index=index;
 const response=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(body)});
 if(!response.ok) alert('Command failed'); else await refresh();
}
document.querySelectorAll('[data-command]').forEach(b=>b.onclick=()=>command(b.dataset.command));
async function refresh(){
 const response=await fetch('/api/status'); if(response.status===401){location='/login';return;}
 const s=await response.json();
 document.getElementById('connection').textContent=s.screen_connected?'Screen connected: '+s.screen_port:'Waiting for CYD USB screen';
 document.getElementById('name').textContent=s.channel_name;
 document.getElementById('group').textContent=(s.channel_group||'')+' · Volume '+s.volume+'%';
 document.getElementById('counter').textContent=s.channel_total?(s.channel_index+1)+' / '+s.channel_total:'0 channels';
 document.getElementById('toggle').textContent=s.paused?'Go live':'Pause';
 document.getElementById('error').textContent=s.last_error||'';
 const box=document.getElementById('channels'); box.replaceChildren();
 s.channels.forEach(c=>{const b=document.createElement('button'); b.className='channel'+(c.index===s.channel_index?' active':''); b.textContent=c.name+(c.group?' · '+c.group:''); b.onclick=()=>command('select',c.index); box.appendChild(b);});
}
refresh(); setInterval(refresh,3000);
</script></body></html>
"""

CSS = """
:root{color-scheme:dark;--bg:#071018;--card:#102330;--ink:#f5fbff;--muted:#9eb3c2;--accent:#ffd43b;--bad:#ff7882}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(145deg,#071018,#0d1a24);color:var(--ink);font:16px system-ui,sans-serif;min-height:100vh}
main{max-width:850px;margin:auto;padding:22px}.narrow{max-width:420px;padding-top:12vh}header{display:flex;justify-content:space-between;align-items:center}h1,h2,p{margin-top:0}h1{color:var(--accent)}a{color:var(--accent)}.small{font-size:.9rem}.now,details,form{background:var(--card);padding:18px;border-radius:16px;margin:16px 0}.now h2{font-size:1.7rem;margin:.4rem 0}.now p{color:var(--muted)}button,input,textarea{font:inherit}button{border:0;border-radius:12px;background:#21465d;color:var(--ink);padding:13px 16px;font-weight:700;cursor:pointer}.controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px}.channels{display:grid;gap:8px}.channel{text-align:left;background:var(--card);font-weight:500}.channel.active{outline:3px solid var(--accent)}label{display:block;margin:12px 0;color:var(--muted)}input,textarea{display:block;width:100%;margin-top:7px;padding:12px;border:1px solid #34566a;border-radius:10px;background:#071018;color:var(--ink)}.error{color:var(--bad)!important}.foot{color:var(--muted);font-size:.85rem;margin-top:30px}summary{cursor:pointer;font-weight:700}
"""


def create_app(player, config: AppConfig) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=config.server.secret_key,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
    )
    attempts: dict[str, deque[float]] = defaultdict(deque)

    def authenticated() -> bool:
        return bool(session.get("authenticated"))

    def login_required(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if not authenticated():
                if request.path.startswith("/api/"):
                    return jsonify({"error": "authentication required"}), 401
                return redirect(url_for("login"))
            return function(*args, **kwargs)

        return wrapped

    def valid_csrf() -> bool:
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf", "")
        return hmac.compare_digest(str(session.get("csrf", "")), supplied)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = ""
        if request.method == "POST":
            remote = request.remote_addr or "unknown"
            now = time.monotonic()
            history = attempts[remote]
            while history and now - history[0] > 600:
                history.popleft()
            if len(history) >= 8:
                error = "Too many attempts. Wait ten minutes."
            elif hmac.compare_digest(request.form.get("pin", ""), config.server.admin_pin):
                session.clear()
                session["authenticated"] = True
                session["csrf"] = secrets.token_urlsafe(24)
                attempts.pop(remote, None)
                return redirect(url_for("index"))
            else:
                history.append(now)
                error = "That PIN was not accepted."
        return render_template_string(LOGIN_HTML, css=CSS, error=error)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def index():
        return render_template_string(CONTROL_HTML, css=CSS, csrf=session["csrf"])

    @app.route("/api/status")
    @login_required
    def api_status():
        return jsonify(player.status())

    @app.route("/api/command", methods=["POST"])
    @login_required
    def api_command():
        if not valid_csrf():
            abort(403)
        data = request.get_json(silent=True) or {}
        command = str(data.get("command", "")).lower()
        try:
            if command == "select":
                player.select_channel(int(data["index"]))
            elif command in {"next", "prev", "toggle", "vol_up", "vol_down"}:
                player.handle_command(command)
            else:
                return jsonify({"error": "unknown command"}), 400
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"ok": True})

    @app.route("/playlist", methods=["POST"])
    @login_required
    def upload_playlist():
        if not valid_csrf():
            abort(403)
        uploaded = request.files.get("playlist")
        if uploaded and uploaded.filename:
            raw = uploaded.read().decode("utf-8-sig", errors="replace")
        else:
            raw = request.form.get("playlist_text", "")
        channels = parse_m3u(raw)
        if not channels:
            return "Playlist has no supported channel URLs.", 400
        if any(item.drm_hint for item in channels):
            return "Playlist advertises DRM; this player cannot use it.", 400
        destination = Path(config.playback.playlist)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="channels-", suffix=".m3u", dir=destination.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        player.reload_playlist(destination)
        return redirect(url_for("index"))

    return app
