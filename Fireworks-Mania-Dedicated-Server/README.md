# Fireworks Mania Dedicated Server - PufferPanel Template

This PufferPanel template installs, configures, and manages a [Fireworks Mania](https://store.steampowered.com/app/1079260/Fireworks_Mania__An_Explosive_Simulator/) Dedicated Server on Linux.

## Details

- **Type**: **Fireworks-Mania**
- **Display**: **Fireworks-Mania-Dedicated-Server**
- **Environment**: Docker (`python:3.12-slim`)

## Prerequisites

- **Docker**: Requires host Docker environment support in PufferPanel.
- **Network**: Port **7777** (UDP) for game traffic. *(Customizable in PufferPanel settings)*
- **GitHub Access Token** *(Optional)*: A GitHub PAT with `public_repo` scope to avoid API rate limits when downloading server releases.
- **mod.io Access Token** *(Optional)*: Required if you wish to download and load custom community mods via mod.io.

## Resource Limits

- **`max-ram-mb`**: RAM limit in Megabytes (`0` = Unlimited by default).
- **`max-cpu-cores`**: Number of CPU cores allocated (`0` = All Cores by default, e.g. `4` for 4 cores).

## Installation & Maintenance

When a new server is created in PufferPanel with this template:
1. PufferPanel installs Python dependencies (`requests`, `PyGithub`) inside the container.
2. Downloads **`ServerAutoUpdate.py`**.
3. **`ServerAutoUpdate.py`** checks the target repository (**`Laumania/FireworksMania.DedicatedServer`** by default) for the specified release tag (**`latest`** by default).
4. Extracts **`FireworksManiaDedicatedLinux.x86_64`** and sets execution permissions.
5. Generates **`host.config`** and **`modio.token`** files automatically before each launch.
6. Applies process-level CPU core and RAM limits if configured.
7. Launches **`FireworksManiaDedicatedLinux.x86_64`**.
