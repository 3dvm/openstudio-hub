from pathlib import Path
from .vcs_adapters.abstract_vcs import AbstractVCS
from .vcs_adapters.svn_adapter import SVNAdapter
from .vcs_adapters.git_lfs_adapter import GitLFSAdapter

class VCSRouter:
    """
    Enrutador principal para la capa VCS. Instancia y devuelve el adaptador correcto 
    en función de la configuración extraída del ConfigFactory.
    """
    def __init__(self, vcs_type: str, repo_url: str, workspace_dir: Path):
        self.vcs_type = vcs_type.lower()
        self.repo_url = repo_url
        self.workspace_dir = workspace_dir
        self._ensure_workspace()

    def _ensure_workspace(self):
        """Garantiza que la carpeta de destino exista antes de operar."""
        if not self.workspace_dir.exists():
            self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def get_adapter(self) -> AbstractVCS:
        """
        Retorna la instancia del adaptador concreto a usar.
        """
        if self.vcs_type == "svn":
            return SVNAdapter(self.repo_url, self.workspace_dir)
        elif self.vcs_type == "git-lfs":
            return GitLFSAdapter(self.repo_url, self.workspace_dir)
        else:
            raise ValueError(f"Motor VCS no soportado o desconocido: '{self.vcs_type}'")
