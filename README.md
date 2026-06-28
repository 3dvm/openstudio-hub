# Macuare Studio Hub: Pipeline Management System

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Blender](https://img.shields.io/badge/Blender-4.2%2B-orange?logo=blender&logoColor=white)
![Kitsu](https://img.shields.io/badge/Kitsu_SSO-Gazu-success?logo=cgwire&logoColor=white)
![Architecture](https://img.shields.io/badge/Architecture-MVC-purple)

**Macuare Hub** is a desktop application designed to orchestrate the production pipeline for a 3D animation studio. It acts as a seamless bridge between artists, the version control system (SVN/Git LFS), and the production tracker (Kitsu).

## The Problem it Solves
In large-scale productions, updating software versions or add-ons often breaks backward compatibility. Artists might accidentally open files with the wrong Blender version, corrupting production data.

**The Solution:** Macuare Hub reads the "DNA" (`project_config.json`) of each project and **builds dynamic software containers at runtime**. It injects environment variables (`BLENDER_USER_SCRIPTS`) to isolate extensions and forces the exact Blender binary required by the project to launch. This allows a studio to work on Blender 5.0 and 5.1 simultaneously without cross-contamination.

## Key Features
* **Single Sign-On (SSO) with Kitsu:** Uses the Gazu API as the *Source of Truth* to validate user roles (TD vs. Artist) and grant secure access.
* **In-Memory SVN Vault:** Stores the Subversion password in RAM only during the active session, eliminating the vulnerability of saving network credentials on local disks.
* **Dynamic Environment Injection:** Configures the execution environment by isolating extensions, wheels, and scripts per project before Blender even starts.
* **"Artist-Proof" UI:** Built with `CustomTkinter`, it offers a modern and fluid interface that completely hides the terminal and infrastructure complexity from the end user.

## Software Architecture (MVC)
The codebase is designed following the **Separation of Concerns** principle, making it highly maintainable and ideal for Enterprise-level scaling:

```text
macuare-hub/
├── core/                   # Business Logic (Backend)
│   ├── auth_manager.py     # Gazu/Kitsu API Connection
│   ├── env_launcher.py     # Environment injection and subprocess
│   └── vault_manager.py    # In-memory credential management
├── tests/                  # Automated Testing (Pytest)
│   └── test_kitsu.py       # Roles and SSO validation
├── macuare_hub.py          # UI Controller (CustomTkinter)
└── requirements.txt        # Dependencies (Gazu, CTk)

```

## 💻 Installation and Usage (Development Mode)

1. Clone the repository:
```bash
git clone [https://github.com/your-username/macuare-hub.git](https://github.com/your-username/macuare-hub.git)
cd macuare-hub

```


2. Create and activate the virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate.fish  # Or activate for bash/zsh

```


3. Install dependencies:
```bash
pip install -r requirements.txt

```


4. Run the Hub:
```bash
python macuare_hub.py

```



## 🛠️ Packaging for Production

To distribute the tool to studio artists without requiring them to install Python, the application is "frozen" into a standalone executable using PyInstaller:

```bash
pyinstaller --noconsole --onefile --name "Macuare Hub" macuare_hub.py

```

---

*Developed by [Ernesto / Del Valle M.] - Technical Director & Pipeline Engineer.*
