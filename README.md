# OpenStudio Hub: Pipeline Management System

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Blender](https://img.shields.io/badge/Blender-3.6_|_4.2_|_5.1-orange?logo=blender&logoColor=white)
![Kitsu](https://img.shields.io/badge/Kitsu_SSO-Gazu-success?logo=cgwire&logoColor=white)
![Architecture](https://img.shields.io/badge/Architecture-MVC-purple)
![AI](https://img.shields.io/badge/AI_Powered-Proxy_VERITAS-magic)

**OpenStudio Hub** (formerly Macuare Hub) is a standalone desktop application designed to orchestrate the production pipeline for a 3D animation studio. It acts as a seamless, deterministic bridge between artists, the version control system (SVN/Git), cloud storage (Nextcloud), and the production tracker (Kitsu).

> **[Watch the Demo Video Showcase Here](https://estudiomacuare.com/wp-content/uploads/macuare-hub-demo.mp4)**

*(Note: While the public and commercial name is OpenStudio Hub, the internal namespace and codebase may retain the legacy `MACUARE_` / `macuare_` prefix for structural stability)*.

## The Problem: Dependency Hell
In large-scale productions, updating software versions or add-ons mid-show often breaks backward compatibility. Artists waste hours dealing with Python tracebacks, missing add-ons, and manual path configurations just to open a legacy file without corrupting modern production data.

## The Solution: A "rez-like" Ephemeral Sandbox
OpenStudio Hub solves this by reading the "DNA" (`project_config.json`) of each project and **building dynamic software containers at runtime**. It bypasses global OS installations completely by injecting environment variables (`OPENSTUDIO_PROJECT_ROOT`, `OPENSTUDIO_USER_ROLE`) to isolate extensions, scripts, and preferences per project. 

This guarantees **100% backward compatibility** and allows artists to run conflicting legacy tools and modern pipelines simultaneously with zero cross-contamination[cite: 8].

---

## Core Pipeline Features

*   **Dual Sync & VFS Mapping (Symlinks):** Fuses Cloud (Nextcloud) and VCS (SVN) at the OS level. Heavy caches and renders go to the NAS, while `.blend` files go to SVN, appearing as a single continuous drive to the artist.
*   **Context-Aware Tooling & RBAC:** Automatically injects task-specific add-ons based on the Kitsu `TaskType` (e.g., Animation vs. Rigging) and restricts destructive actions (like Force Push) via Runtime Polling Override based on user roles.
*   **The Gatekeeper:** Enforces a strict Scene Sanity Check before publishing, automating scale fixes, orphan purging, and Out-of-Bounds reference resolution.
*   **AI Telemetry & Daily Digest:** A background tracker monitors artist activity and the Undo Stack, sending raw data to the VERITAS Proxy. This generates automated commit messages and an LLM-powered Daily Stand-up Digest for Supervisors.
*   **Vendor Jailing:** External freelancers are isolated via a Sparse Checkout engine, restricting their local workspace to strictly the task assigned to them.

---

## High-Level Studio Architecture

```mermaid
flowchart TD
    subgraph Cloud [Studio Cloud Infrastructure]
        K[Kitsu API<br>SSO & Roles]
        N[Nextcloud / NAS<br>Heavy Caches & Manifests]
        S[SVN / Git Server<br>Production Assets]
        P[VERITAS Proxy<br>LLM Telemetry & Digests]
    end

    subgraph Workstation [Artist Local Machine]
        direction TB
        MH{OpenStudio Hub<br>Standalone GUI}
        RAM[(In-Memory Vault<br>Volatile Credentials)]
        VFS[VFS / Symlinks<br>Dual Sync Engine]
        DCC[Blender Subprocess<br>Context-Aware Sandbox]
    end

    K <-->|Auth & Metadata| MH
    N -->|Manifests & Caches| VFS
    S <-->|Commits & Updates| VFS
    MH -->|Creates Symlink Schema| VFS
    MH -->|Stores Passwords| RAM
    
    RAM -.->|Injects ENVs| DCC
    VFS -.->|Mounts Workspace| DCC
    DCC -->|Sends Undo/Telemetry Logs| P

    classDef cloud fill:#2c3e50,stroke:#fff,stroke-width:2px,color:#fff;
    classDef local fill:#34495e,stroke:#fff,stroke-width:2px,color:#fff;
    classDef hub fill:#e67e22,stroke:#fff,stroke-width:3px,color:#fff;
    classDef security fill:#e74c3c,stroke:#fff,stroke-width:2px,color:#fff;

    class K,N,S,P cloud;
    class VFS,DCC local;
    class MH hub;
    class RAM security;

```

---

## Security: Just-In-Time (JIT) Credential Interception

Traditional pipelines often rely on saving plain-text network credentials on local disks, creating significant security vulnerabilities. OpenStudio Hub utilizes an **In-Memory Vault**. SVN and Kitsu passwords are asked once via a CustomTkinter modal, kept strictly in volatile RAM, injected into the DCC as OS environment variables during the subprocess launch, and wiped entirely upon logout.

```mermaid
sequenceDiagram
    autonumber
    actor Artist
    participant UI as OpenStudio Hub GUI
    participant Vault as RAM Vault (Volatile)
    participant Core as Env Launcher
    participant DCC as Blender Subprocess

    Artist->>UI: Clicks "Launch Project"
    UI->>Vault: Check SVN/Kitsu Credentials
    
    alt Vault is Empty
        Vault-->>UI: Missing Credentials
        UI->>Artist: Prompt JIT Login Modal
        Artist->>UI: Enters Passwords
        UI->>Vault: Store in RAM (No Disk IO)
    end
    
    UI->>Core: Trigger Thread (Background Process)
    Core->>Vault: Retrieve Credentials
    Core->>Core: Inject OPENSTUDIO_USER_ROLE / GAZU_AUTH_TOKEN
    Core->>DCC: subprocess.Popen()
    
    Note over DCC: DCC boots 100% isolated.<br/>Init scripts read ENVs<br/>and auto-authenticate.

```

---

## 💻 Development & Installation

The codebase is designed following the **Separation of Concerns (MVC)** principle and a strict **Concurrency Model**, ensuring the CustomTkinter GUI never blocks during heavy I/O or networking tasks (delegated to Worker Threads).

1. Clone the repository:

```bash
git clone [https://github.com/tu-usuario/openstudio-hub.git](https://github.com/tu-usuario/openstudio-hub.git)
cd openstudio-hub

```

2. Create and activate the virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

```

3. Install dependencies:

```bash
pip install -r requirements.txt

```

4. Run the Hub:

```bash
python openstudio_hub.py

```

## Packaging for Production

To distribute the tool to studio artists without requiring them to install Python, the application is "frozen" into a standalone executable using PyInstaller.

```bash
pyinstaller --noconsole --onefile --name "OpenStudio Hub" openstudio_hub.py

```

*(Note: The compiled executable is not tracked in this repository. Please visit the **Releases** tab to download the latest production build)*.

---

*Developed by [Ernesto Del Valle M.] - Pipeline TD & Technical Artist.*
