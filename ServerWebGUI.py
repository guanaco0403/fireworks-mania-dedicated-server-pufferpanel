import os
import sys
import json
import time
import argparse
import threading
import subprocess
import platform
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Optional psutil import with fallback
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

SERVER_BIN_NAME = "FireworksManiaDedicatedLinux.x86_64"
VERSION_FILE = ".installed_version"
HOST_CONFIG_FILE = "host.config"
MODIO_TOKEN_FILE = "modio.token"
SERVER_LOG_FILES = [
    "server.log",
    "/pufferpanel/server.log",
    os.path.expanduser("~/.config/unity3d/Laumania/FireworksMania/Player.log"),
    os.path.expanduser("~/.config/unity3d/Laumania/Fireworks Mania/Player.log"),
    "Player.log"
]

start_time = time.time()

def find_server_process():
    """Find the dedicated server process PID and metrics."""
    pid = None
    cpu_percent = 0.0
    memory_mb = 0.0
    memory_percent = 0.0
    proc_uptime = 0

    if HAS_PSUTIL:
        try:
            for p in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'cpu_percent', 'memory_info', 'memory_percent']):
                name = p.info.get('name') or ''
                cmdline = ' '.join(p.info.get('cmdline') or [])
                if SERVER_BIN_NAME in name or SERVER_BIN_NAME in cmdline:
                    pid = p.info['pid']
                    try:
                        cpu_percent = round(p.cpu_percent(interval=0.1), 1)
                        mem_info = p.memory_info()
                        memory_mb = round(mem_info.rss / (1024 * 1024), 1)
                        memory_percent = round(p.memory_percent(), 1)
                        proc_uptime = int(time.time() - p.create_time())
                    except Exception:
                        pass
                    break
        except Exception:
            pass
    else:
        # Fallback to ps / pgrep if psutil is not available
        try:
            cmd = f"pgrep -f {SERVER_BIN_NAME}"
            output = subprocess.check_output(cmd, shell=True, text=True).strip()
            if output:
                pids = output.split()
                pid = int(pids[0])
                proc_uptime = int(time.time() - start_time)
        except Exception:
            pid = None

    return {
        "running": pid is not None,
        "pid": pid,
        "cpu_percent": cpu_percent,
        "memory_mb": memory_mb,
        "memory_percent": memory_percent,
        "uptime_seconds": proc_uptime
    }

def get_system_metrics():
    """Retrieve system CPU, Memory, and Disk usage."""
    cpu_usage = 0.0
    mem_total_mb = 0.0
    mem_used_mb = 0.0
    mem_percent = 0.0
    disk_total_gb = 0.0
    disk_used_gb = 0.0
    disk_percent = 0.0

    if HAS_PSUTIL:
        try:
            cpu_usage = psutil.cpu_percent(interval=None)
            vmem = psutil.virtual_memory()
            mem_total_mb = round(vmem.total / (1024 * 1024), 1)
            mem_used_mb = round(vmem.used / (1024 * 1024), 1)
            mem_percent = vmem.percent

            disk = psutil.disk_usage('/')
            disk_total_gb = round(disk.total / (1024 * 1024 * 1024), 1)
            disk_used_gb = round(disk.used / (1024 * 1024 * 1024), 1)
            disk_percent = disk.percent
        except Exception:
            pass
    else:
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                mem_total = 0
                mem_free = 0
                mem_avail = 0
                for line in lines:
                    if line.startswith('MemTotal:'):
                        mem_total = int(line.split()[1])
                    elif line.startswith('MemAvailable:'):
                        mem_avail = int(line.split()[1])
                if mem_total > 0:
                    mem_total_mb = round(mem_total / 1024, 1)
                    mem_used_mb = round((mem_total - mem_avail) / 1024, 1)
                    mem_percent = round(((mem_total - mem_avail) / mem_total) * 100, 1)
        except Exception:
            pass

    return {
        "cpu_percent": cpu_usage,
        "memory_total_mb": mem_total_mb,
        "memory_used_mb": mem_used_mb,
        "memory_percent": mem_percent,
        "disk_total_gb": disk_total_gb,
        "disk_used_gb": disk_used_gb,
        "disk_percent": disk_percent
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

def read_server_logs(max_lines=150):
    """Read recent lines from the server log file."""
    for log_path in SERVER_LOG_FILES:
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                    return [line.rstrip() for line in lines[-max_lines:]]
            except Exception as e:
                return [f"Error reading log file ({log_path}): {e}"]
    return ["No log file found. Logs will appear here when generated by the server process."]

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fireworks Mania Server Web GUI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0b0f19;
            --bg-card: rgba(23, 31, 48, 0.7);
            --bg-card-hover: rgba(30, 41, 63, 0.85);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(56, 189, 248, 0.2);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-cyan: #38bdf8;
            --accent-purple: #c084fc;
            --accent-green: #34d399;
            --accent-red: #f87171;
            --accent-yellow: #fbbf24;
            --status-online: #10b981;
            --status-offline: #ef4444;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

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

        .container {
            max-width: 1320px;
            margin: 0 auto;
        }

        /* Header */
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

        .brand {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .brand-icon {
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, #0ea5e9, #8b5cf6);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 20px rgba(14, 165, 233, 0.3);
            font-size: 1.4rem;
        }

        .brand-title h1 {
            font-size: 1.4rem;
            font-weight: 700;
            background: linear-gradient(90deg, #38bdf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
        }

        .brand-title p {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.875rem;
            backdrop-filter: blur(8px);
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
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(1.15); }
        }

        .btn-refresh {
            background: rgba(30, 41, 59, 0.8);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            font-size: 0.85rem;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .btn-refresh:hover {
            background: rgba(51, 65, 85, 1);
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
        }

        /* Metrics Cards Grid */
        .grid-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }

        .card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1.25rem;
            transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .card:hover {
            border-color: var(--border-glow);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
            transform: translateY(-2px);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }

        .card-title {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            font-weight: 600;
        }

        .card-icon {
            font-size: 1.2rem;
            color: var(--accent-cyan);
        }

        .card-value {
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.4rem;
        }

        .card-subtext {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        /* Progress Bar */
        .progress-bar-bg {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 999px;
            overflow: hidden;
            margin-top: 0.5rem;
        }

        .progress-bar-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
            transition: width 0.4s ease;
        }

        /* Details Sections */
        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: var(--text-primary);
        }

        .grid-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .info-table {
            width: 100%;
            border-collapse: collapse;
        }

        .info-table tr {
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }

        .info-table tr:last-child {
            border-bottom: none;
        }

        .info-table td {
            padding: 0.65rem 0;
            font-size: 0.875rem;
        }

        .info-label {
            color: var(--text-secondary);
            font-weight: 400;
            width: 45%;
        }

        .info-val {
            color: var(--text-primary);
            font-weight: 600;
            text-align: right;
        }

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

        /* Console Log Viewer */
        .log-container {
            background: #070a12;
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1.25rem;
        }

        .log-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }

        .log-box {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            background: #030509;
            color: #d1d5db;
            padding: 1rem;
            border-radius: 8px;
            height: 320px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
            border: 1px solid rgba(255, 255, 255, 0.05);
            line-height: 1.5;
        }

        .log-box::-webkit-scrollbar {
            width: 8px;
        }

        .log-box::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.2);
        }

        .log-box::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 4px;
        }

        /* Footer */
        footer {
            margin-top: 2.5rem;
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-muted);
            border-top: 1px solid var(--border-color);
            padding-top: 1.5rem;
        }

        footer a {
            color: var(--accent-cyan);
            text-decoration: none;
        }

        footer a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div class="brand">
                <div class="brand-icon">🎆</div>
                <div class="brand-title">
                    <h1>Fireworks Mania Dedicated Server</h1>
                    <p>Web Control & Status GUI</p>
                </div>
            </div>
            <div class="header-actions">
                <div id="status-badge" class="status-badge offline">
                    <span class="status-dot"></span>
                    <span id="status-text">Checking...</span>
                </div>
                <button class="btn-refresh" onclick="fetchData()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/></svg>
                    Refresh
                </button>
            </div>
        </header>

        <!-- Metrics Grid -->
        <div class="grid-metrics">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Server Uptime</span>
                    <span class="card-icon">⏱️</span>
                </div>
                <div class="card-value" id="val-uptime">--:--:--</div>
                <div class="card-subtext" id="val-pid">PID: --</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Process CPU</span>
                    <span class="card-icon">⚡</span>
                </div>
                <div class="card-value" id="val-cpu">0%</div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="bar-cpu" style="width: 0%"></div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Process Memory</span>
                    <span class="card-icon">💾</span>
                </div>
                <div class="card-value" id="val-ram">0 MB</div>
                <div class="card-subtext" id="val-ram-pct">0% of system memory</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">System Disk</span>
                    <span class="card-icon">💽</span>
                </div>
                <div class="card-value" id="val-disk">-- GB</div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="bar-disk" style="width: 0%"></div>
                </div>
            </div>
        </div>

        <!-- Server Details Grid -->
        <div class="grid-details">
            <!-- Host Config Card -->
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

            <!-- Gameplay Settings Card -->
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

            <!-- Limits & Mods Card -->
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

        <!-- Live Server Log -->
        <div class="log-container">
            <div class="log-header">
                <div class="section-title" style="margin-bottom:0">📄 Live Server Output Log</div>
                <span class="card-subtext">Auto-refreshing every 3s</span>
            </div>
            <div class="log-box" id="log-box">Loading server log...</div>
        </div>

        <!-- Footer -->
        <footer>
            Fireworks Mania Dedicated Server Web GUI &bull; PufferPanel Integration &bull; Powered by Python
        </footer>
    </div>

    <script>
        function formatSeconds(seconds) {
            if (!seconds || seconds <= 0) return '00:00:00';
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = seconds % 60;
            return [h, m, s].map(v => v < 10 ? '0' + v : v).join(':');
        }

        function createPill(enabled) {
            if (enabled) {
                return '<span class="toggle-pill enabled">ENABLED</span>';
            } else {
                return '<span class="toggle-pill disabled">DISABLED</span>';
            }
        }

        async function fetchData() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();

                // Update Status Badge
                const badge = document.getElementById('status-badge');
                const statusText = document.getElementById('status-text');

                if (data.server && data.server.running) {
                    badge.className = 'status-badge online';
                    statusText.textContent = 'ONLINE';
                } else {
                    badge.className = 'status-badge offline';
                    statusText.textContent = 'OFFLINE';
                }

                // Metrics
                const server = data.server || {};
                document.getElementById('val-uptime').textContent = formatSeconds(server.uptime_seconds);
                document.getElementById('val-pid').textContent = server.pid ? `PID: ${server.pid}` : 'PID: Offline';
                document.getElementById('val-cpu').textContent = `${server.cpu_percent || 0}%`;
                document.getElementById('bar-cpu').style.width = `${Math.min(server.cpu_percent || 0, 100)}%`;
                document.getElementById('val-ram').textContent = `${server.memory_mb || 0} MB`;
                document.getElementById('val-ram-pct').textContent = `${server.memory_percent || 0}% of system memory`;

                const sys = data.system || {};
                document.getElementById('val-disk').textContent = `${sys.disk_used_gb || 0} / ${sys.disk_total_gb || 0} GB`;
                document.getElementById('bar-disk').style.width = `${sys.disk_percent || 0}%`;

                // Host Config
                const host = data.host_config?.HostConfig || {};
                const game = data.host_config?.GameConfig || {};

                document.getElementById('cfg-name').textContent = host.Name || '--';
                document.getElementById('cfg-desc').textContent = host.Description || '--';
                document.getElementById('cfg-author').textContent = host.Author || '--';
                document.getElementById('cfg-ip').textContent = host.IP || '--';
                document.getElementById('cfg-port').textContent = host.Port ? `${host.Port} UDP` : '--';
                document.getElementById('cfg-players').textContent = host.MaxPlayers ?? '--';
                
                const joinTypes = { 0: 'Everyone (0)', 1: 'Friends Only (1)' };
                document.getElementById('cfg-join').textContent = joinTypes[host.WhoCanJoin] || (host.WhoCanJoin ?? '--');

                document.getElementById('cfg-map').textContent = game.Map || '--';
                document.getElementById('cfg-despawn').innerHTML = createPill(game.EnableAutoDespawnUsedFireworks);
                document.getElementById('cfg-destructions').innerHTML = createPill(game.EnableDestructions);
                document.getElementById('cfg-fly').innerHTML = createPill(game.EnableFlyMode);
                document.getElementById('cfg-explosion').innerHTML = createPill(game.EnableExplosionPhysicsForces);
                document.getElementById('cfg-ignition').innerHTML = createPill(game.EnableIgnitionForces);
                document.getElementById('cfg-delay').textContent = game.MinTimeBetweenPlayerSpawnInSeconds ? `${game.MinTimeBetweenPlayerSpawnInSeconds}s` : '--';

                document.getElementById('cfg-max-fireworks').textContent = game.MaxAllowedPlayerSpawnedFireworks ?? '--';
                document.getElementById('cfg-max-props').textContent = game.MaxAllowedPlayerSpawnedProps ?? '--';
                
                const lockedArr = game.LockedInventoryEntityIds || [];
                document.getElementById('cfg-locked').textContent = Array.isArray(lockedArr) ? `${lockedArr.length} item(s)` : '--';

                document.getElementById('cfg-version').textContent = data.installed_version || 'Unknown';
                document.getElementById('cfg-modio').innerHTML = createPill(data.modio_token_configured);

                const modsArr = game.Mods || [];
                document.getElementById('cfg-mods-count').textContent = Array.isArray(modsArr) ? `${modsArr.length} mod(s)` : '--';

            } catch (err) {
                console.error('Error fetching server status:', err);
            }

            // Fetch Logs
            try {
                const resLogs = await fetch('/api/logs');
                const dataLogs = await resLogs.json();
                const logBox = document.getElementById('log-box');
                if (dataLogs.logs && dataLogs.logs.length > 0) {
                    const wasScrolledToBottom = logBox.scrollHeight - logBox.clientHeight <= logBox.scrollTop + 20;
                    logBox.textContent = dataLogs.logs.join('\n');
                    if (wasScrolledToBottom) {
                        logBox.scrollTop = logBox.scrollHeight;
                    }
                } else {
                    logBox.textContent = 'No log entries recorded.';
                }
            } catch (err) {
                console.error('Error fetching logs:', err);
            }
        }

        // Initial fetch and set interval
        fetchData();
        setInterval(fetchData, 3000);
    </script>
</body>
</html>
"""

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    daemon_threads = True

class WebGUIRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress standard HTTP request logging to keep console clean
        return

    def send_json(self, data, status_code=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html_content, status_code=200):
        body = html_content.encode('utf-8')
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]

        if path in ['/', '/index.html']:
            self.send_html(HTML_PAGE)
        elif path == '/api/status':
            payload = {
                "server": find_server_process(),
                "system": get_system_metrics(),
                "host_config": read_host_config(),
                "installed_version": read_installed_version(),
                "modio_token_configured": read_modio_status()
            }
            self.send_json(payload)
        elif path == '/api/logs':
            payload = {
                "logs": read_server_logs()
            }
            self.send_json(payload)
        else:
            self.send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        path = self.path.split('?')[0]
        if path == '/api/command':
            # Phase 2 Command Endpoint Stub
            self.send_json({
                "status": "not_implemented",
                "message": "Command execution endpoint ready for Phase 2."
            }, 501)
        else:
            self.send_json({"error": "Not Found"}, 404)

CLR_RESET = "\033[0m"
CLR_BOLD = "\033[1m"
CLR_GREEN = "\033[1;32m"
CLR_CYAN = "\033[1;36m"
CLR_YELLOW = "\033[1;33m"

def monitor_game_server_ready(host, port, timeout=120):
    """Background thread to monitor game server startup and print colored notification when ready."""
    start_wait = time.time()
    announced = False
    
    while time.time() - start_wait < timeout:
        proc_info = find_server_process()
        logs = read_server_logs(max_lines=50)
        log_text = "\n".join(logs)
        
        if (proc_info["running"] or "Listening on" in log_text or "running and ready" in log_text) and not announced:
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
    
    # Start background thread to announce colored banner when game server becomes ready
    t = threading.Thread(target=monitor_game_server_ready, args=(host, port), daemon=True)
    t.start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down Web GUI server.", flush=True)
        httpd.server_close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fireworks Mania Dedicated Server Web GUI")
    parser.add_argument('--port', type=int, default=8080, help="Port to run the Web GUI on (default: 8080)")
    parser.add_argument('--host', type=str, default='0.0.0.0', help="Host address to bind to (default: 0.0.0.0)")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)
