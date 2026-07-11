from abc import ABC, abstractmethod
from typing import List, Dict
from pathlib import Path

class AbstractVCS(ABC):
    """
    Interfaz base para todos los adaptadores de Control de Versiones.
    Garantiza que cualquier motor (SVN, Git) exponga los mismos métodos al Hub.
    """
    def __init__(self, repo_url: str, workspace_dir: Path):
        self.repo_url = repo_url
        self.workspace_dir = workspace_dir

    @abstractmethod
    def full_pull(self, username: str = None, password: str = None) -> bool:
        """Descarga o actualiza el repositorio completo."""
        pass

    @abstractmethod
    def sparse_pull(self, paths: List[str], username: str = None, password: str = None) -> bool:
        """Descarga estrictamente las rutas especificadas ignorando el resto (Jailing)."""
        pass

    @abstractmethod
    def commit(self, message: str, paths: List[str] = None, username: str = None, password: str = None) -> bool:
        """Sube los cambios locales al servidor."""
        pass

    @abstractmethod
    def lock(self, path: str, username: str = None, password: str = None) -> bool:
        """Bloquea un archivo en el servidor para evitar conflictos."""
        pass

    @abstractmethod
    def unlock(self, path: str, username: str = None, password: str = None) -> bool:
        """Libera un archivo bloqueado en el servidor."""
        pass

    @abstractmethod
    def revert(self, path: str) -> bool:
        """Revierte los cambios locales a la última versión del servidor."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, str]:
        """Devuelve el estado de los archivos locales (modificados, añadidos, etc)."""
        pass
