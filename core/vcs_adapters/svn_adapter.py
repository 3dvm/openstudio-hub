# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/vcs_adapters/svn_adapter.py
# Rol Arquitectónico: Adaptador VCS / Capa de Abstracción
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.4.0
# =========================================================================================

"""
Adaptador concreto para operaciones Subversion (SVN) vía CLI.
Implementa el mecanismo de Sparse Checkout para orquestar el Jailing de Vendors.
"""

import subprocess
from typing import List, Dict, Optional
from pathlib import Path
from .abstract_vcs import AbstractVCS

class SVNAdapter(AbstractVCS):
    """Adaptador concreto para operaciones Subversion (SVN) vía CLI."""

    def _build_auth_args(self, username: Optional[str], password: Optional[str]) -> List[str]:
        """Construye los argumentos de autenticación sin guardarlos en disco."""
        args = ["--non-interactive", "--trust-server-cert"]
        if username and password:
            args.extend(["--username", username, "--password", password, "--no-auth-cache"])
        return args

    def _run_subprocess(self, cmd: List[str], cwd: Optional[Path] = None) -> str:
        """Envoltorio seguro para ejecutar subprocesos capturando los errores."""
        cwd_path = str(cwd) if cwd else None
        
        # === MODO DEBUG: Máscara de seguridad para no imprimir la clave en consola ===
        safe_cmd = []
        skip_next = False
        for token in cmd:
            if skip_next:
                safe_cmd.append("********")
                skip_next = False
            elif token == "--password":
                safe_cmd.append(token)
                skip_next = True
            else:
                safe_cmd.append(token)
                
        print(f"\n[SVN DEBUG] Ejecutando (CWD: {cwd_path or 'Actual'}):")
        print(f" -> {' '.join(safe_cmd)}")
        # ==============================================================================

        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd_path, 
                check=True, 
                capture_output=True, 
                text=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            # Captura el stderr real de SVN (Ej. Password incorrecto) para pasarlo a la UI y a Consola
            error_msg = e.stderr.strip() if e.stderr else str(e)
            print(f"[SVN ERROR FATAL] Código {e.returncode}: {error_msg}\n")
            raise RuntimeError(f"Fallo de SVN: {error_msg}")

    def full_pull(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        # Si la carpeta ya existe y es un repo SVN, hacemos update
        if (self.workspace_dir / ".svn").exists():
            cmd = ["svn", "update"]
            cmd.extend(self._build_auth_args(username, password))
            self._run_subprocess(cmd, cwd=self.workspace_dir)
        else:
            # Si no, hacemos checkout completo
            cmd = ["svn", "checkout", self.repo_url, str(self.workspace_dir)]
            cmd.extend(self._build_auth_args(username, password))
            self._run_subprocess(cmd)
        return True

    def sparse_pull(self, paths: List[str], username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Descarga restrictiva (Jailing) para Vendors."""
        # 1. Checkout inicial vacío (Trae solo la estructura, sin archivos)
        if not (self.workspace_dir / ".svn").exists():
            cmd_co = ["svn", "checkout", "--depth", "empty", self.repo_url, str(self.workspace_dir)]
            cmd_co.extend(self._build_auth_args(username, password))
            self._run_subprocess(cmd_co)
        
        # 2. Descarga solo de los directorios aprobados en la lista de rutas
        for path in paths:
            # FIX: Añadida la bandera --parents para construir la jerarquía vacía obligatoria
            cmd_up = ["svn", "update", "--set-depth", "infinity", "--parents", path]
            cmd_up.extend(self._build_auth_args(username, password))
            self._run_subprocess(cmd_up, cwd=self.workspace_dir)
            
        return True

    def commit(self, message: str, paths: Optional[List[str]] = None, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        cmd = ["svn", "commit", "-m", message]
        if paths:
            cmd.extend(paths)
        cmd.extend(self._build_auth_args(username, password))
        self._run_subprocess(cmd, cwd=self.workspace_dir)
        return True

    def lock(self, path: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        cmd = ["svn", "lock", path]
        cmd.extend(self._build_auth_args(username, password))
        self._run_subprocess(cmd, cwd=self.workspace_dir)
        return True

    def unlock(self, path: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        cmd = ["svn", "unlock", path]
        cmd.extend(self._build_auth_args(username, password))
        self._run_subprocess(cmd, cwd=self.workspace_dir)
        return True

    def revert(self, path: str) -> bool:
        cmd = ["svn", "revert", "-R", path]
        self._run_subprocess(cmd, cwd=self.workspace_dir)
        return True

    def get_status(self) -> Dict[str, str]:
        cmd = ["svn", "status"]
        output = self._run_subprocess(cmd, cwd=self.workspace_dir)
        # Parseo crudo para devolver dict: {'A': 'ruta/archivo.blend', 'M': 'ruta/otro.blend'}
        status_dict = {}
        for line in output.splitlines():
            if len(line) > 8:
                state = line[0]
                file_path = line[8:].strip()
                status_dict[file_path] = state
        return status_dict
