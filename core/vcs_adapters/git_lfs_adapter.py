from typing import List, Dict
from pathlib import Path
from .abstract_vcs import AbstractVCS

class GitLFSAdapter(AbstractVCS):
    """
    Adaptador concreto para operaciones Git LFS.
    (Actualmente en estado 'NotImplemented' preparando soporte futuro).
    """

    def full_pull(self, username: str = None, password: str = None) -> bool:
        raise NotImplementedError("Git LFS support is currently under development.")

    def sparse_pull(self, paths: List[str], username: str = None, password: str = None) -> bool:
        # Según SDD 3.3: git clone --filter=blob:none --sparse
        raise NotImplementedError("Git LFS support is currently under development.")

    def commit(self, message: str, paths: List[str] = None, username: str = None, password: str = None) -> bool:
        raise NotImplementedError("Git LFS support is currently under development.")

    def lock(self, path: str, username: str = None, password: str = None) -> bool:
        raise NotImplementedError("Git LFS support is currently under development.")

    def unlock(self, path: str, username: str = None, password: str = None) -> bool:
        raise NotImplementedError("Git LFS support is currently under development.")

    def revert(self, path: str) -> bool:
        raise NotImplementedError("Git LFS support is currently under development.")

    def get_status(self) -> Dict[str, str]:
        raise NotImplementedError("Git LFS support is currently under development.")
