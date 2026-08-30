# Fireworks Mania Dedicated Server - PufferPanel Custom Template Repository

This repository provides a custom [PufferPanel](https://www.pufferpanel.com/) template to automatically install, update, configure, and host a **Fireworks Mania Dedicated Server** on Linux via Docker.

---

## 📁 Repository Structure

```
.
├── .gitignore
├── README.md
├── ServerAutoUpdate.py
└── Fireworks-Mania-Dedicated-Server/
    ├── Fireworks-Mania-Dedicated-Server.json
    └── README.md
```

- **`ServerAutoUpdate.py`**: Python script that fetches and extracts the target dedicated server release (defaults to [Laumania/FireworksMania.DedicatedServer](https://github.com/Laumania/FireworksMania.DedicatedServer)).
- **`Fireworks-Mania-Dedicated-Server/Fireworks-Mania-Dedicated-Server.json`**: PufferPanel template definition file.
- **`Fireworks-Mania-Dedicated-Server/README.md`**: Template metadata and documentation for PufferPanel.

---

## ⚙️ Features & Advanced Settings

- **Automatic Downloads & Updates**: Downloads the target Linux server release from `Laumania/FireworksMania.DedicatedServer` (or a custom repository).
- **Auto-Update On Start**: Option (`auto-update-on-start`, enabled by default) to automatically check for and apply new server updates every time the server starts.
- **Custom Repository & Versions**: Under **Advanced Settings** in PufferPanel:
  - **`auto-update-on-start`**: Toggle automatic update check on server startup (`true`/`false`).
  - **`github-repo`**: Change the source repository (e.g. `CustomOwner/CustomRepo`). Defaults to `Laumania/FireworksMania.DedicatedServer`.
  - **`server-version`**: Target a specific version or release tag (e.g. `latest` or `v1.2.0`).

---

## 📥 Adding the Template to PufferPanel

### Import via Custom Template Repository URL 
1. In PufferPanel, navigate to **Templates** -> **Repositories**.
2. Set the repository name (e.g., `Fireworks Mania Dedicated Server`).
3. Add this GitHub repository URL:
   `https://github.com/guanaco0403/fireworks-mania-dedicated-server-pufferpanel`
4. Select the `main` branch.
5. Click **Import Repository Reference**.

---

## ⚙️ Game & Server Settings

When creating a server with this template in PufferPanel, you can configure:

- **Server Info**: Name, Description, Author.
- **Network**: Server IP (`0.0.0.0`), Server Port (`7777` UDP).
- **Gameplay**: Max Players, Max Fireworks per player, Max Props, Auto-despawn, Physics forces, Map Destructions, Fly Mode, Spawn Delay, Locked Items.
- **Mods**: Provide mod.io IDs as a JSON array (`[12345, 67890]`) and an optional `mod.io token` that is only required to download custom mods from mod.io.
- **GitHub Token**: Optional PAT to prevent GitHub API rate limits when downloading server releases.

---

## 📄 License

Distributed under the MIT License.
