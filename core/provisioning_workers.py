# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/provisioning_workers.py
# Rol Arquitectónico: Core Services / Network Downloaders & Archivers
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0
# =========================================================================================

import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from html.parser import HTMLParser
from PySide6.QtCore import Signal, QThread

from core.addon_inspector import AddonInspector

class ApacheIndexParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href':
                    self.links.append(value)

class RepoFolderFetcherWorker(QThread):
    folders_ready = Signal(list)
    status = Signal(str, str)

    def run(self):
        try:
            req = urllib.request.Request("https://download.blender.org/release/", headers={'User-Agent': 'OpenStudioHub/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            parser = ApacheIndexParser()
            parser.feed(html)
            raw_folders = [l for l in parser.links if l.endswith('/') and ('Blender' in l or l.replace('/', '').replace('.', '').isdigit())]
            raw_folders.sort(reverse=True)
            self.folders_ready.emit(raw_folders)
            self.status.emit("✓ Remote directory tree fetched.", "green")
        except Exception as e:
            self.status.emit(f"✗ Failed to reach remote repository: {str(e)}", "red")
            self.folders_ready.emit([])

class RepoFileFetcherWorker(QThread):
    files_ready = Signal(list)
    status = Signal(str, str)

    def __init__(self, folder_name: str):
        super().__init__()
        self.folder_name = folder_name

    def run(self):
        try:
            url = f"https://download.blender.org/release/{self.folder_name}"
            req = urllib.request.Request(url, headers={'User-Agent': 'OpenStudioHub/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            parser = ApacheIndexParser()
            parser.feed(html)
            valid_exts = ('.zip', '.xz', '.dmg', '.msi', '.exe', '.pkg')
            raw_files = [f for f in parser.links if f.endswith(valid_exts) and not f.startswith('?')]
            raw_files.sort()
            self.files_ready.emit(raw_files)
        except Exception as e:
            self.status.emit(f"✗ Failed to fetch binaries: {str(e)}", "red")
            self.files_ready.emit([])

class BlenderDirectDownloadWorker(QThread):
    progress = Signal(int)
    status = Signal(str, str)
    finished = Signal(bool, str)

    def __init__(self, folder_name: str, file_name: str, target_dir: Path):
        super().__init__()
        self.folder_name = folder_name
        self.file_name = file_name
        self.target_dir = target_dir

    def run(self):
        try:
            final_path = self.target_dir / self.file_name
            
            # 1. Inteligencia de Caché: Evitar descargas duplicadas
            if final_path.exists():
                self.status.emit(f"✓ Asset '{self.file_name}' already exists in Vault. Skipped download.", "green")
                self.progress.emit(100)
                self.finished.emit(True, self.file_name)
                return

            # 2. Flujo de Descarga
            url = f"https://download.blender.org/release/{self.folder_name}{self.file_name}"
            self.target_dir.mkdir(parents=True, exist_ok=True)
            archive_path = self.target_dir / f"{self.file_name}.tmp"
            
            self.status.emit(f"Downloading selected package: {self.file_name}...", "yellow")
            req = urllib.request.Request(url, headers={'User-Agent': 'OpenStudioHub/1.0'})
            
            with urllib.request.urlopen(req) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                block_size = 1024 * 64

                with open(archive_path, 'wb') as out_file:
                    while True:
                        block = response.read(block_size)
                        if not block: break
                        downloaded += len(block)
                        out_file.write(block)
                        if total_size > 0:
                            self.progress.emit(int((downloaded / total_size) * 100))

            archive_path.rename(final_path)
            self.status.emit(f"✓ Compressed asset '{self.file_name}' mirrored on NAS.", "green")
            self.finished.emit(True, self.file_name)

        except Exception as e:
            self.status.emit(f"✗ Archive transfer failed: {str(e)}", "red")
            self.finished.emit(False, "")

class StudioToolsFetchWorker(QThread):
    status = Signal(str, str)
    finished = Signal(bool, dict)

    def __init__(self, version: str, target_templates_dir: Path):
        super().__init__()
        self.version = version
        self.target_templates_dir = target_templates_dir

    def run(self):
        try:
            url = "https://projects.blender.org/studio/blender-studio-tools/archive/main.zip"
            vault_root = self.target_templates_dir.parent
            addons_dir = vault_root / "addons"
            addons_dir.mkdir(parents=True, exist_ok=True)

            herramientas_auto = {
                "templates": {
                    "Macuare_Estudio_Official": {
                        "version": "1.4.2",
                        "description": "Plantilla corporativa auto-generada",
                        "mandatory": True,
                        "requires": []
                    }
                },
                "addons": {}
            }

            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = Path(tmpdir) / "studio_tools.zip"
                req = urllib.request.Request(url, headers={'User-Agent': 'OpenStudioHub/1.0'})
                
                with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)

                self.status.emit("Extracting and compressing compatible Addons...", "yellow")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)

                extracted_root = Path(tmpdir) / "blender-studio-tools"
                
                # Encontrar todos los directorios que parezcan addons (tienen toml o init)
                addon_dirs = []
                for manifest_path in extracted_root.rglob("blender_manifest.toml"):
                    addon_dirs.append(manifest_path.parent)
                for init_path in extracted_root.rglob("__init__.py"):
                    if init_path.parent not in addon_dirs:
                        addon_dirs.append(init_path.parent)

                for addon_dir in addon_dirs:
                    meta = AddonInspector.inspect_directory(addon_dir)
                    if not meta or meta["name"] == "unknown_addon":
                        continue
                    
                    if AddonInspector.is_compatible(meta["blender_min"], self.version):
                        addon_name = meta["name"]
                        addon_ver = meta["version"]
                        desc = meta["description"]
                        
                        target_zip_name = f"{addon_name}-{addon_ver}.zip"
                        target_zip_path = addons_dir / target_zip_name
                        
                        # Inteligencia de Caché + Compresión
                        if not target_zip_path.exists():
                            shutil.make_archive(str(addons_dir / f"{addon_name}-{addon_ver}"), 'zip', root_dir=addon_dir.parent, base_dir=addon_dir.name)
                        
                        herramientas_auto["addons"][addon_name] = {
                            "version": addon_ver,
                            "description": desc[:60] + "..." if len(desc) > 60 else desc,
                            "mandatory": False,
                            "requires": []
                        }

            self.status.emit("✓ Pipeline tools packaged as ZIPs successfully.", "green")
            self.finished.emit(True, herramientas_auto)

        except Exception as e:
            self.status.emit(f"✗ Studio Tools deployment failure: {str(e)}", "red")
            self.finished.emit(False, {})
