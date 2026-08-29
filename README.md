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

## 🚀 Setup & Publishing to GitHub

Follow these steps to host your custom PufferPanel template repository on GitHub:

### 1. Push to GitHub
Create a new GitHub repository (e.g. `fireworks-mania-pufferpanel-template`) and push this project:

```bash
git init
git add .
git commit -m "Initial commit for PufferPanel Fireworks Mania template"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

### 2. Update the `ServerAutoUpdate.py` URL in the Template JSON
Before importing into PufferPanel, edit `Fireworks-Mania-Dedicated-Server/Fireworks-Mania-Dedicated-Server.json`:

Line ~186 currently contains:
```json
"sh -c \"... curl -sSL -o ServerAutoUpdate.py https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPOSITORY/main/ServerAutoUpdate.py && python3 ServerAutoUpdate.py ${github-token} || true\""
```

Replace `YOUR_USERNAME` and `YOUR_REPOSITORY` with your actual GitHub username and repository name!

---

## 📥 Adding the Template to PufferPanel

You can import this template into your PufferPanel instance in two ways:

### Option A: Import JSON File directly
1. Go to your **PufferPanel Admin Panel** -> **Templates**.
2. Click **Import Template** or **Add Template**.
3. Copy and paste the contents of `Fireworks-Mania-Dedicated-Server/Fireworks-Mania-Dedicated-Server.json` (or upload the file).
4. Save the template.

### Option B: Import via Custom Template Repository URL
1. In PufferPanel, navigate to **Templates** -> **Repositories**.
2. Add your GitHub repository raw URL:
   `https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPOSITORY/main`

---

## ⚙️ Game & Server Settings

When creating a server with this template in PufferPanel, you can configure:

- **Server Info**: Name, Description, Author.
- **Network**: Server IP (`0.0.0.0`) & Port (`7777` UDP).
- **Gameplay**: Max Players, Max Fireworks per player, Max Props, Auto-despawn, Physics forces, Destructions.
- **Mods**: Provide mod.io IDs as a JSON array (`[12345, 67890]`) and optional `mod.io PAT`.
- **GitHub Token**: Optional PAT to prevent GitHub API rate limits when downloading server releases.

---

## 📄 License

Distributed under the MIT License.
