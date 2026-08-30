# Fireworks Mania Dedicated Server - PufferPanel Custom Template Repository

This repository provides a custom [PufferPanel](https://www.pufferpanel.com/) template to automatically install, update, configure, and host a **Fireworks Mania Dedicated Server** on Linux via Docker.

---

## 📁 Repository Structure

```
.
├── .gitignore
├── README.md
├── ServerAutoUpdate.py
├── ServerWebGUI.py
└── Fireworks-Mania-Dedicated-Server/
    ├── Fireworks-Mania-Dedicated-Server.json
    └── README.md
```

- **`ServerAutoUpdate.py`**: Python script that fetches and extracts the target dedicated server release (defaults to [Laumania/FireworksMania.DedicatedServer](https://github.com/Laumania/FireworksMania.DedicatedServer)).
- **`ServerWebGUI.py`**: Lightweight Python HTTP server & status dashboard running inside the container alongside the server process.
- **`Fireworks-Mania-Dedicated-Server/Fireworks-Mania-Dedicated-Server.json`**: PufferPanel template definition file.
- **`Fireworks-Mania-Dedicated-Server/README.md`**: Template metadata and variable documentation for PufferPanel.

---

## ⚙️ Features & Advanced Settings

- **Default Behavior**: Downloads the **latest** Linux server release from `Laumania/FireworksMania.DedicatedServer`.
- **Integrated Web GUI**: Live status monitoring dashboard served on a separate port (`8888` by default).
- **Custom Repository & Versions**: Under **Advanced Settings** in PufferPanel, you can specify:
  - **`github-repo`**: Change the source repository (e.g. `CustomOwner/CustomRepo`). Defaults to `Laumania/FireworksMania.DedicatedServer`.
  - **`server-version`**: Target a specific version or release tag (e.g. `latest` or `v1.2.0`).

---

## 📥 Adding the Template to PufferPanel

### Import via Custom Template Repository URL 
1. In PufferPanel, navigate to **Templates** -> **Repositories**.
2. Set the repository name to `Fireworks Mania Dedicated Server` for exemple.
3. Add this GitHub repository URL:
   `https://github.com/guanaco0403/fireworks-mania-dedicated-server-pufferpanel`
4. Set the `main` branch
5. Click on the **Import Repository Reference** button.

---

## ⚙️ Game & Server Settings

When creating a server with this template in PufferPanel, you can configure:

- **Server Info**: Name, Description, Author.
- **Network**: Server IP (`0.0.0.0`), Server Port (`7777` UDP), and Web GUI Port (`8080` HTTP).
- **Gameplay**: Max Players, Max Fireworks per player, Max Props, Auto-despawn, Physics forces, Destructions.
- **Mods**: Provide mod.io IDs as a JSON array (`[12345, 67890]`) and **REQUIRED** `mod.io token` to download mods from mod io, (its optional if you dont want to use any mods from modio).
- **GitHub Token**: Optional PAT to prevent GitHub API rate limits when downloading server releases.

---

## 📄 License

Distributed under the MIT License.
