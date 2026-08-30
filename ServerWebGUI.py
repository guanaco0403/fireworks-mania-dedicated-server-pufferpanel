import os
import sys
import json
import time
import argparse
import threading
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

SERVER_BIN_NAME = "FireworksManiaDedicatedLinux.x86_64"
VERSION_FILE = ".installed_version"
HOST_CONFIG_FILE = "host.config"
MODIO_TOKEN_FILE = "modio.token"

def find_server_process():
    """Check if the dedicated server process PID is running."""
    pid = None
    if os.path.exists('/proc'):
        try:
            for pdir in os.listdir('/proc'):
                if pdir.isdigit():
                    cmdline_path = os.path.join('/proc', pdir, 'cmdline')
                    if os.path.exists(cmdline_path):
                        try:
                            with open(cmdline_path, 'rb') as f:
                                content = f.read().replace(b'\x00', b' ').decode('utf-8', errors='replace')
                                if SERVER_BIN_NAME in content:
                                    pid = int(pdir)
                                    break
                        except Exception:
                            pass
        except Exception:
            pass
    return {
        "running": pid is not None,
        "pid": pid
    }

def read_host_config():
    """Read host.config JSON if available."""
    if os.path.exists(HOST_CONFIG_FILE):
        try:
            with open(HOST_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None

def read_installed_version():
    """Read .installed_version file if available."""
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            pass
    return "Unknown"

def read_modio_status():
    """Check if modio.token exists and has content."""
    if os.path.exists(MODIO_TOKEN_FILE):
        try:
            with open(MODIO_TOKEN_FILE, 'r', encoding='utf-8') as f:
                token = f.read().strip()
                return bool(token and token.lower() != "none" and not token.startswith("${"))
        except Exception:
            pass
    return False

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fireworks Mania Server Info Web GUI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0b0f19;
            --bg-card: rgba(23, 31, 48, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(56, 189, 248, 0.2);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-cyan: #38bdf8;
            --accent-purple: #c084fc;
            --accent-green: #34d399;
            --accent-red: #f87171;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            background-image: 
                radial-gradient(at 15% 15%, rgba(56, 189, 248, 0.08) 0px, transparent 50%),
                radial-gradient(at 85% 85%, rgba(192, 132, 252, 0.08) 0px, transparent 50%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem 1.5rem;
        }

        .container { max-width: 1200px; margin: 0 auto; }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border-color);
            flex-wrap: wrap;
            gap: 1rem;
        }

        .brand { display: flex; align-items: center; gap: 1rem; }

        .brand-icon {
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, #0ea5e9, #8b5cf6);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            box-shadow: 0 4px 20px rgba(14, 165, 233, 0.3);
        }

        .brand-title h1 {
            font-size: 1.4rem;
            font-weight: 700;
            background: linear-gradient(90deg, #38bdf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-title p { font-size: 0.85rem; color: var(--text-secondary); }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.875rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .status-badge.online {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
            border-color: rgba(16, 185, 129, 0.3);
        }

        .status-badge.offline {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
            border-color: rgba(239, 68, 68, 0.3);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
            box-shadow: 0 0 10px currentColor;
        }

        .grid-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1.25rem;
        }

        .section-title {
            font-size: 1.05rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: var(--text-primary);
        }

        .info-table { width: 100%; border-collapse: collapse; }
        .info-table tr { border-bottom: 1px solid rgba(255, 255, 255, 0.04); }
        .info-table tr:last-child { border-bottom: none; }
        .info-table td { padding: 0.65rem 0; font-size: 0.875rem; }

        .info-label { color: var(--text-secondary); font-weight: 400; width: 45%; }
        .info-val { color: var(--text-primary); font-weight: 600; text-align: right; }

        .toggle-pill {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .toggle-pill.enabled {
            background: rgba(52, 211, 153, 0.15);
            color: var(--accent-green);
            border: 1px solid rgba(52, 211, 153, 0.3);
        }

        .toggle-pill.disabled {
            background: rgba(248, 113, 113, 0.15);
            color: var(--accent-red);
            border: 1px solid rgba(248, 113, 113, 0.3);
        }

        footer {
            margin-top: 2rem;
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-secondary);
            border-top: 1px solid var(--border-color);
            padding-top: 1.5rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <div class="brand-icon">🎆</div>
                <div class="brand-title">
                    <h1>Fireworks Mania Server</h1>
                    <p>Dedicated Server Information</p>
                </div>
            </div>
            <div id="status-badge" class="status-badge offline">
                <span class="status-dot"></span>
                <span id="status-text">Checking...</span>
            </div>
        </header>

        <div class="grid-details">
            <div class="card">
                <div class="section-title">🌐 Network & Connection</div>
                <table class="info-table">
                    <tr><td class="info-label">Server Name</td><td class="info-val" id="cfg-name">--</td></tr>
                    <tr><td class="info-label">Description</td><td class="info-val" id="cfg-desc">--</td></tr>
                    <tr><td class="info-label">Author</td><td class="info-val" id="cfg-author">--</td></tr>
                    <tr><td class="info-label">Listen IP</td><td class="info-val" id="cfg-ip">--</td></tr>
                    <tr><td class="info-label">UDP Port</td><td class="info-val" id="cfg-port">--</td></tr>
                    <tr><td class="info-label">Max Players</td><td class="info-val" id="cfg-players">--</td></tr>
                    <tr><td class="info-label">Who Can Join</td><td class="info-val" id="cfg-join">--</td></tr>
                </table>
            </div>

            <div class="card">
                <div class="section-title">⚙️ Game Rules & Features</div>
                <table class="info-table">
                    <tr><td class="info-label">Active Map</td><td class="info-val" id="cfg-map">--</td></tr>
                    <tr><td class="info-label">Auto Despawn Fireworks</td><td class="info-val" id="cfg-despawn">--</td></tr>
                    <tr><td class="info-label">Enable Destructions</td><td class="info-val" id="cfg-destructions">--</td></tr>
                    <tr><td class="info-label">Enable Fly Mode</td><td class="info-val" id="cfg-fly">--</td></tr>
                    <tr><td class="info-label">Explosion Physics</td><td class="info-val" id="cfg-explosion">--</td></tr>
                    <tr><td class="info-label">Ignition Forces</td><td class="info-val" id="cfg-ignition">--</td></tr>
                    <tr><td class="info-label">Spawn Delay</td><td class="info-val" id="cfg-delay">--</td></tr>
                </table>
            </div>

            <div class="card">
                <div class="section-title">📦 Limits & Mods</div>
                <table class="info-table">
                    <tr><td class="info-label">Max Player Fireworks</td><td class="info-val" id="cfg-max-fireworks">--</td></tr>
                    <tr><td class="info-label">Max Player Props</td><td class="info-val" id="cfg-max-props">--</td></tr>
                    <tr><td class="info-label">Locked Item IDs</td><td class="info-val" id="cfg-locked">--</td></tr>
                    <tr><td class="info-label">Installed Version</td><td class="info-val" id="cfg-version">--</td></tr>
                    <tr><td class="info-label">mod.io Token</td><td class="info-val" id="cfg-modio">--</td></tr>
                    <tr><td class="info-label">Configured Mods Count</td><td class="info-val" id="cfg-mods-count">--</td></tr>
                </table>
            </div>
        </div>

        <footer>
            Fireworks Mania Dedicated Server Web GUI &bull; PufferPanel Integration
        </footer>
    </div>

    <script>
        function createPill(enabled) {
            return enabled ? '<span class="toggle-pill enabled">ENABLED</span>' : '<span class="toggle-pill disabled">DISABLED</span>';
        }

        async function fetchData() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();

                const badge = document.getElementById('status-badge');
                const statusText = document.getElementById('status-text');

                if (data.server && data.server.running) {
                    badge.className = 'status-badge online';
                    statusText.textContent = 'ONLINE';
                } else {
                    badge.className = 'status-badge offline';
                    statusText.textContent = 'OFFLINE';
                }

                const host = (data.host_config && data.host_config.HostConfig) ? data.host_config.HostConfig : {};
                const game = (data.host_config && data.host_config.GameConfig) ? data.host_config.GameConfig : {};

                document.getElementById('cfg-name').textContent = host.Name || '--';
                document.getElementById('cfg-desc').textContent = host.Description || '--';
                document.getElementById('cfg-author').textContent = host.Author || '--';
                document.getElementById('cfg-ip').textContent = host.IP || '--';
                document.getElementById('cfg-port').textContent = host.Port ? (host.Port + ' UDP') : '--';
                document.getElementById('cfg-players').textContent = (host.MaxPlayers !== undefined && host.MaxPlayers !== null) ? host.MaxPlayers : '--';
                
                const joinTypes = { 0: 'Everyone (0)', 1: 'Friends Only (1)' };
                document.getElementById('cfg-join').textContent = joinTypes[host.WhoCanJoin] || ((host.WhoCanJoin !== undefined && host.WhoCanJoin !== null) ? host.WhoCanJoin : '--');

                document.getElementById('cfg-map').textContent = game.Map || '--';
                document.getElementById('cfg-despawn').innerHTML = createPill(game.EnableAutoDespawnUsedFireworks);
                document.getElementById('cfg-destructions').innerHTML = createPill(game.EnableDestructions);
                document.getElementById('cfg-fly').innerHTML = createPill(game.EnableFlyMode);
                document.getElementById('cfg-explosion').innerHTML = createPill(game.EnableExplosionPhysicsForces);
                document.getElementById('cfg-ignition').innerHTML = createPill(game.EnableIgnitionForces);
                document.getElementById('cfg-delay').textContent = game.MinTimeBetweenPlayerSpawnInSeconds ? (game.MinTimeBetweenPlayerSpawnInSeconds + 's') : '--';

                document.getElementById('cfg-max-fireworks').textContent = (game.MaxAllowedPlayerSpawnedFireworks !== undefined && game.MaxAllowedPlayerSpawnedFireworks !== null) ? game.MaxAllowedPlayerSpawnedFireworks : '--';
                document.getElementById('cfg-max-props').textContent = (game.MaxAllowedPlayerSpawnedProps !== undefined && game.MaxAllowedPlayerSpawnedProps !== null) ? game.MaxAllowedPlayerSpawnedProps : '--';
                
                const lockedArr = game.LockedInventoryEntityIds || [];
                document.getElementById('cfg-locked').textContent = Array.isArray(lockedArr) ? (lockedArr.length + ' item(s)') : '--';

                document.getElementById('cfg-version').textContent = data.installed_version || 'Unknown';
                document.getElementById('cfg-modio').innerHTML = createPill(data.modio_token_configured);

                const modsArr = game.Mods || [];
                document.getElementById('cfg-mods-count').textContent = Array.isArray(modsArr) ? (modsArr.length + ' mod(s)') : '--';
            } catch (err) {
                console.error('Error fetching status:', err);
            }
        }

        fetchData();
        setInterval(fetchData, 3000);
    </script>
</body>
</html>
"""

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class WebGUIRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def send_json(self, data, status_code=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html_content, status_code=200):
        body = html_content.encode('utf-8')
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]

        if path in ['/', '/index.html']:
            self.send_html(HTML_PAGE)
        elif path == '/api/status':
            payload = {
                "server": find_server_process(),
                "host_config": read_host_config(),
                "installed_version": read_installed_version(),
                "modio_token_configured": read_modio_status()
            }
            self.send_json(payload)
        else:
            self.send_json({"error": "Not Found"}, 404)

CLR_RESET = "\033[0m"
CLR_BOLD = "\033[1m"
CLR_GREEN = "\033[1;32m"
CLR_CYAN = "\033[1;36m"
CLR_YELLOW = "\033[1;33m"

def monitor_game_server_ready(host, port, timeout=120):
    start_wait = time.time()
    announced = False
    
    while time.time() - start_wait < timeout:
        proc_info = find_server_process()
        if proc_info["running"] and not announced:
            announced = True
            print(".", flush=True)
            print(f"{CLR_GREEN}========================================================================{CLR_RESET}", flush=True)
            print(f"  {CLR_CYAN}{CLR_BOLD}🎆 Fireworks Mania Dedicated Server & Web GUI are ONLINE!{CLR_RESET}", flush=True)
            print(f"  {CLR_YELLOW}👉 Web GUI Dashboard URL: {CLR_BOLD}http://{host}:{port}{CLR_RESET}", flush=True)
            print(f"{CLR_GREEN}========================================================================{CLR_RESET}", flush=True)
            print(".", flush=True)
            break
        time.sleep(1)

def run_server(host='0.0.0.0', port=8080):
    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, WebGUIRequestHandler)
    print(f"[INFO] Fireworks Mania Web GUI service listening on http://{host}:{port}", flush=True)
    
    t = threading.Thread(target=monitor_game_server_ready, args=(host, port), daemon=True)
    t.start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down Web GUI server.", flush=True)
        httpd.server_close()

def auto_update_script_if_needed():
    """Auto-update ServerWebGUI.py from GitHub if local file is missing simplified architecture."""
    try:
        url = f"https://raw.githubusercontent.com/guanaco0403/fireworks-mania-dedicated-server-pufferpanel/main/ServerWebGUI.py?t={int(time.time())}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            content = resp.read().decode('utf-8')
            if "Fireworks Mania Server Info Web GUI" in content and len(content) > 1000:
                script_path = os.path.abspath(__file__)
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print("[INFO] ServerWebGUI.py updated automatically from GitHub.", flush=True)
    except Exception:
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fireworks Mania Dedicated Server Web GUI")
    parser.add_argument('--port', type=int, default=8080, help="Port to run the Web GUI on (default: 8080)")
    parser.add_argument('--host', type=str, default='0.0.0.0', help="Host address to bind to (default: 0.0.0.0)")
    args = parser.parse_args()

    auto_update_script_if_needed()
    run_server(host=args.host, port=args.port)
