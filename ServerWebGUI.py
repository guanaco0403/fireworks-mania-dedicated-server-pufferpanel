import os
import sys
import json
import time
import argparse
import threading
import subprocess
import select
try:
    import pty
except ImportError:
    pty = None

from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

SERVER_BIN_NAME = "FireworksManiaDedicatedLinux.x86_64"
VERSION_FILE = ".installed_version"
HOST_CONFIG_FILE = "host.config"
MODIO_TOKEN_FILE = "modio.token"
FIFO_PIPE_FILE = "server_input.fifo"
SERVER_LOG_FILES = [
    "server.log",
    "/pufferpanel/server.log",
    os.path.expanduser("~/.config/unity3d/Laumania/FireworksMania/Player.log"),
    os.path.expanduser("~/.config/unity3d/Laumania/Fireworks Mania/Player.log"),
    "Player.log"
]

game_process = None
master_pty_fd = None

def launch_game_server_pty():
    """Launch the Unity dedicated server process inside a PTY pseudo-terminal."""
    global game_process, master_pty_fd

    executable = f"./{SERVER_BIN_NAME}"
    if not os.path.exists(executable):
        print(f"[ERROR] Executable {executable} not found!", flush=True)
        return

    if pty is None:
        print("[WARN] pty module unavailable on this OS. Falling back to external process execution.", flush=True)
        return

    try:
        master_fd, slave_fd = pty.openpty()
        master_pty_fd = master_fd

        game_process = subprocess.Popen(
            [executable],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        os.close(slave_fd)
        print(f"[INFO] Launched {SERVER_BIN_NAME} inside PTY (PID: {game_process.pid})", flush=True)

        def io_pump():
            while True:
                try:
                    r, _, _ = select.select([master_fd], [], [], 0.5)
                    if master_fd in r:
                        data = os.read(master_fd, 4096)
                        if not data:
                            break
                        sys.stdout.buffer.write(data)
                        sys.stdout.buffer.flush()
                except Exception:
                    break

        t = threading.Thread(target=io_pump, daemon=True)
        t.start()
    except Exception as e:
        print(f"[ERROR] Failed to start game server in PTY: {e}", flush=True)

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
        "running": pid is not None or (game_process is not None and game_process.poll() is None),
        "pid": pid or (game_process.pid if game_process else None)
    }

def send_server_command(cmd_string):
    """Inject a command into the running server process stdin via PTY master descriptor."""
    global master_pty_fd
    if not cmd_string or not cmd_string.strip():
        return False, "Command cannot be empty."

    raw_cmd = cmd_string.strip()
    cmd_bytes = (raw_cmd + "\r\n").encode('utf-8')

    # Method 1: PTY Master Descriptor
    if master_pty_fd is not None:
        try:
            os.write(master_pty_fd, cmd_bytes)
            return True, f"Command sent: {raw_cmd}"
        except Exception as e:
            print(f"[WARN] Failed writing to PTY descriptor: {e}", flush=True)

    # Method 2: FIFO Pipe
    if os.path.exists(FIFO_PIPE_FILE):
        try:
            with open(FIFO_PIPE_FILE, "wb") as f:
                f.write(cmd_bytes)
                f.flush()
            return True, f"Command sent via FIFO: {raw_cmd}"
        except Exception:
            pass

    # Method 3: Process stdin /proc/<pid>/fd/0
    proc_info = find_server_process()
    pid = proc_info.get("pid")
    if pid:
        stdin_path = f"/proc/{pid}/fd/0"
        try:
            if os.path.exists(stdin_path):
                with open(stdin_path, "wb") as f:
                    f.write(cmd_bytes)
                    f.flush()
                return True, f"Command sent via /proc/{pid}/fd/0: {raw_cmd}"
        except Exception:
            pass

    return False, "Server process is not running or stdin is unavailable."

def parse_connected_players():
    """Parse recent player list output from server log files."""
    for log_path in SERVER_LOG_FILES:
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    
                    last_list_idx = -1
                    is_empty = False
                    
                    for i in range(len(lines) - 1, -1, -1):
                        line = lines[i]
                        if "Nobody is in the game right now." in line:
                            is_empty = True
                            break
                        if "player(s) in the game:" in line:
                            last_list_idx = i
                            break
                    
                    if is_empty:
                        return []
                    
                    if last_list_idx != -1:
                        players = []
                        start_idx = last_list_idx + 1
                        if start_idx < len(lines) and "ClientId" in lines[start_idx]:
                            start_idx += 1
                        
                        for j in range(start_idx, len(lines)):
                            l = lines[j].strip()
                            if not l or l.startswith("###") or l.startswith(">") or l.startswith("[") or "player(s)" in l or "Reconnect" in l:
                                break
                            parts = l.split()
                            if len(parts) >= 3:
                                client_id = parts[0]
                                username = parts[1]
                                identifier = parts[2]
                                players.append({
                                    "client_id": client_id,
                                    "username": username,
                                    "identifier": identifier
                                })
                        return players
            except Exception:
                pass
    return []

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
    <title>Fireworks Mania Server Control Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
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
            --accent-yellow: #fbbf24;
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

        /* Control Panel Grid */
        .controls-grid {
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
            justify-content: space-between;
            align-items: center;
            color: var(--text-primary);
        }

        /* Action Buttons */
        .btn-group {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin-bottom: 1rem;
        }

        .btn {
            background: rgba(30, 41, 59, 0.8);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            padding: 0.6rem 1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }

        .btn:hover {
            background: rgba(51, 65, 85, 1);
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
        }

        .btn-danger {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
            border-color: rgba(239, 68, 68, 0.3);
        }

        .btn-danger:hover {
            background: rgba(239, 68, 68, 0.3);
            border-color: var(--accent-red);
            color: #fff;
        }

        .btn-warning {
            background: rgba(251, 191, 36, 0.15);
            color: var(--accent-yellow);
            border-color: rgba(251, 191, 36, 0.3);
        }

        .btn-warning:hover {
            background: rgba(251, 191, 36, 0.3);
            border-color: var(--accent-yellow);
            color: #fff;
        }

        .btn-primary {
            background: linear-gradient(135deg, #0ea5e9, #8b5cf6);
            color: #fff;
            border: none;
        }

        .btn-primary:hover { opacity: 0.9; }

        /* Form Inputs */
        .input-group {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 0.75rem;
        }

        .input-field {
            flex: 1;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.6rem 0.8rem;
            border-radius: 8px;
            font-size: 0.875rem;
            font-family: inherit;
            outline: none;
        }

        .input-field:focus { border-color: var(--accent-cyan); }

        /* Tables */
        .info-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
        .info-table tr { border-bottom: 1px solid rgba(255, 255, 255, 0.04); }
        .info-table tr:last-child { border-bottom: none; }
        .info-table td, .info-table th { padding: 0.65rem 0.5rem; font-size: 0.875rem; vertical-align: middle; }

        .info-label { color: var(--text-secondary); font-weight: 400; width: 45%; }
        .info-val { color: var(--text-primary); font-weight: 600; text-align: right; word-break: break-word; overflow-wrap: anywhere; }

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

        /* Toast Popup */
        #toast-container {
            position: fixed;
            bottom: 1.5rem;
            right: 1.5rem;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .toast {
            background: #1e293b;
            color: #fff;
            padding: 0.8rem 1.2rem;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            box-shadow: 0 10px 25px rgba(0,0,0,0.4);
            font-size: 0.875rem;
            display: flex;
            align-items: center;
            gap: 0.6rem;
            animation: fadeIn 0.3s ease;
        }

        .toast.success { border-color: var(--accent-green); color: var(--accent-green); }
        .toast.error { border-color: var(--accent-red); color: var(--accent-red); }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Modal Popup */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(3, 7, 18, 0.75);
            backdrop-filter: blur(8px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 999;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.25s ease;
        }

        .modal-overlay.active {
            opacity: 1;
            pointer-events: auto;
        }

        .modal-box {
            background: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            width: 90%;
            max-width: 440px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
            transform: scale(0.95);
            transition: transform 0.25s ease;
        }

        .modal-overlay.active .modal-box { transform: scale(1); }

        .modal-title { font-size: 1.15rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--text-primary); }
        .modal-desc { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1.25rem; }

        .modal-actions {
            display: flex;
            justify-content: flex-end;
            gap: 0.75rem;
            margin-top: 1.25rem;
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
                    <p>Interactive Dedicated Server Control Dashboard</p>
                </div>
            </div>
            <div id="status-badge" class="status-badge offline">
                <span class="status-dot"></span>
                <span id="status-text">Checking...</span>
            </div>
        </header>

        <!-- Connected Players Live Table -->
        <div class="card" style="margin-bottom: 2rem;">
            <div class="section-title">
                <span>🎮 Live Connected Players</span>
                <span id="player-count-badge" class="toggle-pill enabled">0 Online</span>
            </div>
            <div id="player-list-container" style="overflow-x:auto;">
                <table class="info-table">
                    <thead>
                        <tr style="border-bottom:1px solid var(--border-color); color:var(--text-secondary); text-align:left;">
                            <th style="width:15%;">Client ID</th>
                            <th style="width:35%;">Username</th>
                            <th style="width:30%;">Identifier / Steam ID</th>
                            <th style="width:20%; text-align:right;">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="player-list-tbody">
                        <tr><td colspan="4" style="text-align:center; padding:1.5rem; color:var(--text-secondary);">No players currently connected.</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Quick Controls Grid -->
        <div class="controls-grid">
            <!-- Server Control Buttons -->
            <div class="card">
                <div class="section-title">⚡ Quick Controls</div>
                <div class="btn-group">
                    <button class="btn btn-warning" onclick="sendQuickAction('clear_fireworks')">🧹 Clear All Fireworks</button>
                    <button class="btn" onclick="openBroadcastModal()">📢 Broadcast Message</button>
                    <button class="btn" onclick="sendQuickAction('refresh_players')">🔄 Refresh Players</button>
                </div>

                <div style="margin-top:1rem; margin-bottom:0.5rem;" class="info-label">Set Time of Day</div>
                <div class="btn-group">
                    <button class="btn" onclick="sendQuickAction('set_time_of_day', {time: 12})">☀️ Day (12:00)</button>
                    <button class="btn" onclick="sendQuickAction('set_time_of_day', {time: 18})">🌅 Sunset (18:00)</button>
                    <button class="btn" onclick="sendQuickAction('set_time_of_day', {time: 0})">🌙 Night (00:00)</button>
                </div>

                <div style="margin-top:1rem; margin-bottom:0.5rem;" class="info-label">Set Weather</div>
                <div class="btn-group">
                    <button class="btn" onclick="sendQuickAction('set_weather', {weather: 'Clear'})">🌤️ Clear</button>
                    <button class="btn" onclick="sendQuickAction('set_weather', {weather: 'Rain'})">🌧️ Rain</button>
                    <button class="btn" onclick="sendQuickAction('set_weather', {weather: 'Storm'})">🌩️ Storm</button>
                    <button class="btn" onclick="sendQuickAction('set_weather', {weather: 'Fog'})">🌫️ Fog</button>
                </div>
            </div>

            <!-- Player Kick / Ban Manual Management -->
            <div class="card">
                <div class="section-title">🛑 Manual Player Action</div>
                <div class="modal-desc">Type a player username or ID manually to Kick or Ban with reason modal popup.</div>
                
                <div class="input-group">
                    <input type="text" id="player-target-input" class="input-field" placeholder="Player Name or ID...">
                </div>
                <div class="btn-group" style="margin-top:0.5rem;">
                    <button class="btn btn-warning" onclick="openPlayerModal('kick')">🛑 Kick Player</button>
                    <button class="btn btn-danger" onclick="openPlayerModal('ban')">🔨 Ban Player</button>
                </div>
            </div>

            <!-- Console Command Injection -->
            <div class="card">
                <div class="section-title">💻 Execute Console Command</div>
                <div class="modal-desc">Send any Quantum Processor console command directly to the server.</div>
                
                <div class="input-group">
                    <input type="text" id="raw-command-input" class="input-field" placeholder="e.g. fm-host-settimeofday 15" onkeydown="if(event.key==='Enter') executeRawCommand()">
                    <button class="btn btn-primary" onclick="executeRawCommand()">Send</button>
                </div>
            </div>
        </div>

        <!-- Server Information Details Grid -->
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
            Fireworks Mania Dedicated Server Control GUI &bull; PufferPanel Integration
        </footer>
    </div>

    <!-- Reusable Action Modal -->
    <div id="action-modal" class="modal-overlay">
        <div class="modal-box">
            <div id="modal-header-title" class="modal-title">Action Confirmation</div>
            <div id="modal-header-desc" class="modal-desc">Please specify the details for this action.</div>
            
            <div id="modal-body">
                <!-- Dynamic Input Container -->
            </div>

            <div class="modal-actions">
                <button class="btn" onclick="closeModal()">Cancel</button>
                <button id="modal-submit-btn" class="btn btn-primary" onclick="submitModal()">Confirm</button>
            </div>
        </div>
    </div>

    <!-- Toast Notifications Container -->
    <div id="toast-container"></div>

    <script>
        let currentModalAction = null;

        function escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function showToast(message, type = 'success') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = type === 'success' ? `✅ ${message}` : `❌ ${message}`;
            container.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 300);
            }, 3500);
        }

        function createPill(enabled) {
            return enabled ? '<span class="toggle-pill enabled">ENABLED</span>' : '<span class="toggle-pill disabled">DISABLED</span>';
        }

        async function sendApiCommand(payload) {
            try {
                const res = await fetch('/api/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    showToast(data.message || 'Command executed successfully!', 'success');
                    fetchData();
                } else {
                    showToast(data.message || 'Failed to execute command.', 'error');
                }
            } catch (err) {
                showToast('Error connecting to server backend.', 'error');
            }
        }

        function sendQuickAction(action, extra = {}) {
            sendApiCommand({ action: action, ...extra });
        }

        function executeRawCommand() {
            const input = document.getElementById('raw-command-input');
            const val = input.value.trim();
            if (!val) return;
            sendApiCommand({ action: 'raw_command', command: val });
            input.value = '';
        }

        function openBroadcastModal() {
            currentModalAction = 'broadcast';
            document.getElementById('modal-header-title').textContent = '📢 Broadcast Message';
            document.getElementById('modal-header-desc').textContent = 'Enter a message to display to all connected players.';
            document.getElementById('modal-body').innerHTML = `
                <input type="text" id="modal-input-msg" class="input-field" style="width:100%" placeholder="Type message here...">
            `;
            document.getElementById('modal-submit-btn').className = 'btn btn-primary';
            document.getElementById('action-modal').classList.add('active');
            setTimeout(() => document.getElementById('modal-input-msg').focus(), 100);
        }

        function openPlayerModalDirect(type, username) {
            document.getElementById('player-target-input').value = username;
            openPlayerModal(type);
        }

        function openPlayerModal(type) {
            const targetVal = document.getElementById('player-target-input').value.trim();
            if (!targetVal) {
                showToast('Please enter a Player Name or ID first.', 'error');
                document.getElementById('player-target-input').focus();
                return;
            }

            currentModalAction = type;
            const isKick = type === 'kick';
            document.getElementById('modal-header-title').textContent = isKick ? `🛑 Kick Player: ${targetVal}` : `🔨 Ban Player: ${targetVal}`;
            document.getElementById('modal-header-desc').textContent = `Please specify a reason for this ${isKick ? 'kick' : 'ban'}.`;
            document.getElementById('modal-body').innerHTML = `
                <input type="text" id="modal-input-reason" class="input-field" style="width:100%" placeholder="Enter ${isKick ? 'kick' : 'ban'} reason...">
            `;
            document.getElementById('modal-submit-btn').className = isKick ? 'btn btn-warning' : 'btn btn-danger';
            document.getElementById('action-modal').classList.add('active');
            setTimeout(() => document.getElementById('modal-input-reason').focus(), 100);
        }

        function closeModal() {
            document.getElementById('action-modal').classList.remove('active');
            currentModalAction = null;
        }

        function submitModal() {
            const targetVal = document.getElementById('player-target-input').value.trim();

            if (currentModalAction === 'broadcast') {
                const msg = document.getElementById('modal-input-msg').value.trim();
                if (msg) {
                    sendApiCommand({ action: 'broadcast_message', message: msg });
                }
            } else if (currentModalAction === 'kick') {
                const reason = document.getElementById('modal-input-reason').value.trim() || 'Kicked by administrator';
                sendApiCommand({ action: 'kick_player', target: targetVal, reason: reason });
            } else if (currentModalAction === 'ban') {
                const reason = document.getElementById('modal-input-reason').value.trim() || 'Banned by administrator';
                sendApiCommand({ action: 'ban_player', target: targetVal, reason: reason });
            }

            closeModal();
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

                // Render Players Table
                const players = data.players || [];
                document.getElementById('player-count-badge').textContent = players.length + ' Online';

                const tbody = document.getElementById('player-list-tbody');
                if (players.length > 0) {
                    let rowsHtml = '';
                    players.forEach(p => {
                        rowsHtml += `
                            <tr style="border-bottom:1px solid rgba(255,255,255,0.04);">
                                <td style="padding:0.65rem 0.5rem; font-weight:600; color:var(--text-secondary);">#${escapeHtml(p.client_id)}</td>
                                <td style="padding:0.65rem 0.5rem; font-weight:700; color:var(--accent-cyan);">${escapeHtml(p.username)}</td>
                                <td style="padding:0.65rem 0.5rem; font-family:'JetBrains Mono',monospace; font-size:0.8rem; color:var(--text-secondary);">${escapeHtml(p.identifier)}</td>
                                <td style="padding:0.65rem 0.5rem; text-align:right;">
                                    <button class="btn btn-warning" style="padding:0.3rem 0.65rem; font-size:0.75rem;" onclick="openPlayerModalDirect('kick', '${escapeHtml(p.username)}')">🛑 Kick</button>
                                    <button class="btn btn-danger" style="padding:0.3rem 0.65rem; font-size:0.75rem;" onclick="openPlayerModalDirect('ban', '${escapeHtml(p.username)}')">🔨 Ban</button>
                                </td>
                            </tr>
                        `;
                    });
                    tbody.innerHTML = rowsHtml;
                } else {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:1.5rem; color:var(--text-secondary);">No players currently connected.</td></tr>';
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

                let verText = data.installed_version || 'Unknown';
                if (verText.indexOf(':') !== -1) {
                    const parts = verText.split(':');
                    const tag = parts[1] || '';
                    const asset = parts[2] || '';
                    if (tag && asset) {
                        verText = tag + ' (' + asset.replace('.zip', '') + ')';
                    } else if (tag) {
                        verText = tag;
                    }
                }
                document.getElementById('cfg-version').textContent = verText;
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
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0, s-maxage=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html_content, status_code=200):
        body = html_content.encode('utf-8')
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0, s-maxage=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]

        if path in ['/', '/index.html']:
            self.send_html(HTML_PAGE)
        elif path == '/api/status':
            payload = {
                "server": find_server_process(),
                "players": parse_connected_players(),
                "host_config": read_host_config(),
                "installed_version": read_installed_version(),
                "modio_token_configured": read_modio_status()
            }
            self.send_json(payload)
        else:
            self.send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        path = self.path.split('?')[0]
        if path == '/api/command':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                action = data.get("action")
                success, msg = False, "Unknown action"

                if action == "clear_fireworks":
                    success, msg = send_server_command("fm-host-clear_fireworks")
                elif action == "broadcast_message":
                    message = data.get("message", "")
                    success, msg = send_server_command(f'fm-host-message "{message}"')
                elif action == "set_time_of_day":
                    time_val = data.get("time", 12)
                    success, msg = send_server_command(f'fm-host-settimeofday {time_val}')
                elif action == "set_weather":
                    weather = data.get("weather", "Clear")
                    success, msg = send_server_command(f'fm-host-weather {weather}')
                elif action == "kick_player":
                    target = data.get("target", "")
                    reason = data.get("reason", "Kicked by administrator")
                    success, msg = send_server_command(f'fm-host-kick_player "{target}" "{reason}"')
                elif action == "ban_player":
                    target = data.get("target", "")
                    reason = data.get("reason", "Banned by administrator")
                    success, msg = send_server_command(f'fm-host-ban_player "{target}" "{reason}"')
                elif action == "refresh_players":
                    success, msg = send_server_command("fm-host-list-players")
                elif action == "raw_command":
                    cmd = data.get("command", "")
                    success, msg = send_server_command(cmd)

                status_code = 200 if success else 400
                self.send_json({"success": success, "message": msg}, status_code)
            except Exception as e:
                self.send_json({"success": False, "message": str(e)}, 500)
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

def self_update_and_restart():
    """Auto-download latest ServerWebGUI.py from GitHub and overwrite local script if changed."""
    if os.environ.get("SERVERWEBGUI_UPDATED") == "1":
        return

    url = f"https://raw.githubusercontent.com/guanaco0403/fireworks-mania-dedicated-server-pufferpanel/main/ServerWebGUI.py?t={int(time.time())}"
    current_script = os.path.abspath(__file__)

    try:
        import urllib.request
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                new_code = response.read().decode('utf-8')
                
                try:
                    with open(current_script, 'r', encoding='utf-8') as f:
                        current_code = f.read()
                except Exception:
                    current_code = ""

                if new_code and len(new_code) > 500 and new_code != current_code:
                    print(f"[INFO] Auto-updating {os.path.basename(current_script)} from GitHub...", flush=True)
                    with open(current_script, 'w', encoding='utf-8') as f:
                        f.write(new_code)
                    print(f"[SUCCESS] Successfully updated {os.path.basename(current_script)}! Restarting script...", flush=True)
                    
                    env = dict(os.environ)
                    env["SERVERWEBGUI_UPDATED"] = "1"
                    os.execve(sys.executable, [sys.executable, current_script] + sys.argv[1:], env)
    except Exception as e:
        print(f"[WARN] Web GUI self-update check skipped ({e}).", flush=True)

def run_server(host='0.0.0.0', port=8080, launch_server=False):
    self_update_and_restart()
    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, WebGUIRequestHandler)
    print(f"[INFO] Fireworks Mania Web GUI service listening on http://{host}:{port}", flush=True)
    
    t1 = threading.Thread(target=monitor_game_server_ready, args=(host, port), daemon=True)
    t1.start()

    if launch_server:
        print("[INFO] Launching game server inside PTY wrapper...", flush=True)
        launch_game_server_pty()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down Web GUI server.", flush=True)
        httpd.server_close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fireworks Mania Dedicated Server Web GUI")
    parser.add_argument('--port', type=int, default=8080, help="Port to run the Web GUI on (default: 8080)")
    parser.add_argument('--host', type=str, default='0.0.0.0', help="Host address to bind to (default: 0.0.0.0)")
    parser.add_argument('--launch-server', action='store_true', help="Launch the dedicated server process directly inside a PTY")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port, launch_server=args.launch_server)
