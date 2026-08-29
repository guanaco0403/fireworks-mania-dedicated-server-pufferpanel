# Fireworks Mania Dedicated Server - PufferPanel Template

PufferPanel template for installing, configuring, and managing a [Fireworks Mania](https://store.steampowered.com/app/1079260/Fireworks_Mania__An_Explosive_Simulator/) Dedicated Server on Linux.

## Details

- **Type**: `Fireworks-Mania`
- **Display**: `Fireworks-Mania-Dedicated-Server`
- **Environment**: Docker (`pufferpanel/ubuntu`)

## Prerequisites

- **Docker**: Requires host Docker environment support in PufferPanel.
- **Network**: Port `7777` (UDP) forwarded and exposed on your host network.
- **GitHub Access Token** *(Optional)*: A GitHub PAT with `public_repo` scope to avoid API rate limits when checking and downloading server releases.
- **mod.io Access Token** *(Optional)*: Required if you wish to download and load custom community mods via mod.io.

## Variables & Configuration

| Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `server-name` | string | `My Server` | Server name shown in the server list |
| `server-description` | string | `My brand new server` | Server description |
| `server-author` | string | `Unknown` | Author / Host name |
| `server-ip` | string | `0.0.0.0` | IP address to bind server |
| `server-port` | integer | `7777` | UDP Port for game connections |
| `max-players` | integer | `10` | Maximum simultaneous player slots |
| `max-fireworks` | integer | `20` | Maximum fireworks per player |
| `max-props` | integer | `60` | Maximum props per player |
| `spawn-delay` | string | `0.2` | Minimum spawn delay between items per player (seconds) |
| `server-map` | string | `Flat` | Map name to launch (`Flat`, `Ranch`, `Town`, etc.) |
| `server-mods` | string | `[]` | JSON Array of mod.io Mod IDs (e.g. `[12345, 67890]`) |
| `auto-despawn-enabled` | boolean | `true` | Auto-despawn used fireworks |
| `enable-destructions` | boolean | `true` | Enable destructible map elements |
| `enable-fly-mode` | boolean | `true` | Allow fly mode for players |
| `explosion-forces-enabled` | boolean | `true` | Enable physics forces from explosions |
| `ignition-forces-enabled` | boolean | `true` | Enable physics forces from ignition |
| `locked-items` | string | `[]` | JSON Array of locked item IDs |
| `modio-token` | string | `""` | Personal Access Token from mod.io |
| `github-token` | string | `""` | GitHub Personal Access Token for auto-updater |

## Installation & Maintenance

When a new server is created in PufferPanel with this template:
1. PufferPanel installs Python 3 and dependencies inside the Ubuntu container.
2. `ServerAutoUpdate.py` checks [Laumania/FireworksMania.DedicatedServer](https://github.com/Laumania/FireworksMania.DedicatedServer) for the latest release zip.
3. Extracts `FireworksManiaDedicatedLinux.x86_64` and sets execution permissions.
4. Generates `host.config` and `modio.token` files automatically before each launch.
