# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/config_factory.py
# Rol Arquitectónico: Configuration Manager / Factory
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.9
# =========================================================================================

import json
import platform
from pathlib import Path

class ConfigFactory:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config = {}
        self._load_config()

    def _load_config(self):
        """Lee y parsea el archivo maestro B2B."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Archivo de configuracion maestro no encontrado: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config = json.load(f)

    def get_raw_config(self) -> dict:
        """Devuelve el diccionario completo en caso de necesitar consultas sin mapear."""
        return self._config

    def _get_current_os(self) -> str:
        """Interroga al sistema host para resolver el Agnosticismo OS."""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "darwin"
        else:
            # Tratamos a Linux y derivados bajo la misma llave para NAS Unix.
            return "linux"

    def get_workspace_root(self) -> Path:
        """Extrae y resuelve la ruta física del NAS/Workspace según el OS de la máquina."""
        os_key = self._get_current_os()
        vcs_config = self._config.get("vcs_engine", {})
        roots = vcs_config.get("local_workspace_root", {})
        
        root_str = roots.get(os_key)
        if not root_str:
            raise ValueError(f"No se ha definido 'local_workspace_root' en settings.json para el OS: {os_key}")
            
        return Path(root_str)

    def get_vcs_adapter_type(self) -> str:
        """Devuelve 'svn' o 'git-lfs'."""
        return self._config.get("vcs_engine", {}).get("active_adapter", "svn")

    def get_vcs_repository_url(self) -> str:
        return self._config.get("vcs_engine", {}).get("repository_url", "")

    def is_vendor_sparse_enabled(self) -> bool:
        """Determina si la protección Jailing/Sparse está activada en la red."""
        return self._config.get("vcs_engine", {}).get("enable_vendor_sparse_checkout", True)

    def get_production_folder_name(self) -> str:
        """Devuelve el nombre del directorio principal de producción (Dynamic Routing)."""
        return self._config.get("vcs_engine", {}).get("production_folder_name", "02_archivos_de_produccion")

    def get_kitsu_api_url(self) -> str:
        return self._config.get("kitsu_production", {}).get("api_url", "")

    def get_blender_executable(self) -> Path | None:
        """
        Devuelve la ruta absoluta al ejecutable de Blender según el OS.
        Si es None, el sistema asume que Blender está instalado en el PATH global (Ej: Linux).
        """
        os_key = self._get_current_os()
        dcc_config = self._config.get("dcc_environment", {})
        execs = dcc_config.get("blender_executable", {})
        
        exe_str = execs.get(os_key)
        return Path(exe_str) if exe_str else None
