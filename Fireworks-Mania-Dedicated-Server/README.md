# Fireworks Mania Dedicated Server - PufferPanel Template

This PufferPanel template installs, configures, and manages a [Fireworks Mania](https://store.steampowered.com/app/1079260/Fireworks_Mania__An_Explosive_Simulator/) Dedicated Server on Linux.

## Details

- **Type**: **Fireworks-Mania**
- **Display**: **Fireworks-Mania-Dedicated-Server**
- **Environment**: Docker (**python:3.12-slim**)

## Prerequisites

- **Docker**: Requires host Docker environment support in PufferPanel.
- **Network**: Port **7777** (UDP) for game traffic. *(Customizable in PufferPanel settings)*
- **GitHub Access Token** *(Optional)*: A GitHub PAT with **public_repo** scope to avoid API rate limits when downloading server releases.
- **mod.io Access Token** *(Optional)*: Required if you wish to download and load custom community mods via mod.io.

## Installation & Maintenance

When a new server is created or installed in PufferPanel with this template:
1. PufferPanel installs Python dependencies (**`requests`**, **`PyGithub`**) inside the container.
2. Downloads **`ServerAutoUpdate.py`**.
3. Runs **`ServerAutoUpdate.py --install`** to download and overwrite the target release (ignoring `.installed_version`), ensuring a fresh and clean installation.
4. On startup, if **`auto-update-on-start`** is enabled, **`ServerAutoUpdate.py`** checks **`.installed_version`** against GitHub and updates only if a newer version is released.
5. Generates **`host.config`** and **`modio.token`** files automatically before each launch.
6. Launches **`FireworksManiaDedicatedLinux.x86_64`**.
