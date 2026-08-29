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

- **`ServerAutoUpdate.py`**: Python script that fetches and extracts the latest dedicated server release from [Laumania/FireworksMania.DedicatedServer](https://github.com/Laumania/FireworksMania.DedicatedServer).
- **`Fireworks-Mania-Dedicated-Server/Fireworks-Mania-Dedicated-Server.json`**: PufferPanel template definition file.
- **`Fireworks-Mania-Dedicated-Server/README.md`**: Template metadata and variable documentation for PufferPanel.

---

## 📥 Adding the Template to PufferPanel

### Import via Custom Template Repository URL 
1. In PufferPanel, navigate to **Templates** -> **Repositories**.
2. Set the repository name to `"Fireworks Mania Dedicated Server"` for exemple.
3. Add this GitHub repository URL:
   `https://github.com/guanaco0403/fireworks-mania-dedicated-server-pufferpanel`
4. Set the `"main"` branch
5. Click on the **Import Repository Reference** button.

---

## ⚙️ Game & Server Settings

When creating a server with this template in PufferPanel, you can configure:

- **Server Info**: Name, Description, Author.
- **Network**: Server IP (`0.0.0.0`) & Port (`7777` UDP).
- **Gameplay**: Max Players, Max Fireworks per player, Max Props, Auto-despawn, Physics forces, Destructions.
- **Mods**: Provide mod.io IDs as a JSON array (`[12345, 67890]`) and **REQUIRED** `mod.io token` to download mods from mod io, (its optional if you dont want to use any mods from modio).
- **GitHub Token**: Optional PAT to prevent GitHub API rate limits when downloading server releases.

---

## 📄 License

Distributed under the MIT License.
