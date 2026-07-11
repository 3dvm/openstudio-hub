import subprocess
from typing import List, Dict
from pathlib import Path
from .abstract_vcs import AbstractVCS

class SVNAdapter(AbstractVCS):
    """Adaptador concreto para operaciones Subversion (SVN) vía CLI."""

    def _build_auth_args(self, username: str, password: str) -> List[str]:
        """Construye los argumentos de autenticación sin guardarlos en disco."""
        args = ["--non-interactive", "--trust-server-cert"]
        if username and password:
            args.extend(["--username", username, "--password", password, "--no-auth-cache"])
        return args

    def _run_subprocess(self, cmd: List[str], cwd: Path = None) -> str:
        """Envoltorio seguro para ejecutar subprocesos capturando los errores."""
        try:
            cwd_path = str(cwd) if cwd else None
            result = subprocess.run(
                cmd, 
                cwd=cwd_path, 
                check=True, 
                capture_output=True, 
                text=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            # Captura el stderr real de SVN (Ej. Password incorrecto) para pasarlo a la UI
            error_msg = e.stderr.strip() if e.stderr else str(e)
            raise RuntimeError(f"Fallo de SVN: {error_msg}")

    def full_pull(self, username: str = None, password: str = None) -> bool:
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

    def sparse_pull(self, paths: List[str], username: str = None, password: str = None) -> bool:
        # 1. Checkout inicial vacío (Jailing)
        if not (self.workspace_dir / ".svn").exists():
            cmd_co = ["svn", "checkout", "--depth", "empty", self.repo_url, str(self.workspace_dir)]
            cmd_co.extend(self._build_auth_args(username, password))
            self._run_subprocess(cmd_co)
        
        # 2. Descarga solo de los directorios aprobados
        for path in paths:
            cmd_up = ["svn", "update", "--set-depth", "infinity", path]
            cmd_up.extend(self._build_auth_args(username, password))
            self._run_subprocess(cmd_up, cwd=self.workspace_dir)
            
        return True

    def commit(self, message: str, paths: List[str] = None, username: str = None, password: str = None) -> bool:
        cmd = ["svn", "commit", "-m", message]
        if paths:
            cmd.extend(paths)
        cmd.extend(self._build_auth_args(username, password))
        self._run_subprocess(cmd, cwd=self.workspace_dir)
        return True

    def lock(self, path: str, username: str = None, password: str = None) -> bool:
        cmd = ["svn", "lock", path]
        cmd.extend(self._build_auth_args(username, password))
        self._run_subprocess(cmd, cwd=self.workspace_dir)
        return True

    def unlock(self, path: str, username: str = None, password: str = None) -> bool:
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
