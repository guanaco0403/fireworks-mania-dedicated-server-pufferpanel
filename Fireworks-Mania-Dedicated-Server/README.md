# Fireworks Mania Dedicated Server - PufferPanel Template

This PufferPanel template for installing, configuring, and managing a [Fireworks Mania](https://store.steampowered.com/app/1079260/Fireworks_Mania__An_Explosive_Simulator/) Dedicated Server on Linux.

## Details

- **Type**: **Fireworks-Mania**
- **Display**: **Fireworks-Mania-Dedicated-Server**
- **Environment**: Docker (**pufferpanel/ubuntu**)

## Prerequisites

- **Docker**: Requires host Docker environment support in PufferPanel.
- **Network**: Port **7777** (UDP) for game traffic and Port **8080** (HTTP) for the Web GUI dashboard. **Note: both ports are customizable in PufferPanel settings.**
- **GitHub Access Token** *(Optional)*: A GitHub PAT with **public_repo** scope to avoid API rate limits when downloading server releases.
- **mod.io Access Token** *(Optional)*: Required if you wish to download and load custom community mods via mod.io.

## Installation & Maintenance

When a new server is created in PufferPanel with this template:
1. PufferPanel installs Python 3 and dependencies inside the Ubuntu container.
2. Downloads **ServerAutoUpdate.py** and **ServerWebGUI.py**.
3. **ServerAutoUpdate.py** checks the targeted repository (**Laumania/FireworksMania.DedicatedServer** by default) for the specified release tag (**latest** by default).
4. Extracts **FireworksManiaDedicatedLinux.x86_64** and sets execution permissions.
5. Generates **host.config** and **modio.token** files automatically before each launch.
6. Launches **ServerWebGUI.py** in the background on your configured HTTP port to display real-time server status, process metrics, and server logs.
