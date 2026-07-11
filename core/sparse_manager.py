# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/sparse_manager.py
# Rol Arquitectónico: Backend Orchestrator / Jailing Manager
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.4.0
# =========================================================================================

"""
Orquestador del Sparse Checkout (Jailing).
Recibe metadatos de Tareas, resuelve rutas y delega la descarga restrictiva 
a la capa de abstracción VCS para aislar a los trabajadores remotos (Vendors).
"""

from typing import Dict, Callable
from core.path_resolver import PathResolver
from core.vcs_router import VCSRouter

class SparseManager:
    """
    Gestiona el aislamiento de directorios (Jailing) para usuarios con rol 'vendor'.
    """
    
    def __init__(self, vcs_router: VCSRouter, status_callback: Callable[[str, str], None]):
        self.router = vcs_router
        self.status_callback = status_callback

    def setup_vendor_workspace(self, task_metadata: Dict[str, str], username: str, password: str) -> bool:
        """
        Orquesta el descubrimiento de ruta y la clonación restrictiva.
        """
        self.status_callback("Calculando ruta estricta de Jailing...", "yellow")
        
        try:
            # 1. Resolución de Ruta (Traducción Kitsu -> LocalFS)
            sparse_path = PathResolver.get_sparse_path(task_metadata)
            
            if not sparse_path:
                self.status_callback("Error: Metadatos de tarea inválidos o vacíos.", "red")
                return False
            
            self.status_callback(f"Jailing activo. Descargando exclusivamente: {sparse_path}", "yellow")
            
            # 2. Delegación a la Capa de Abstracción VCS
            adapter = self.router.get_adapter()
            
            # El adaptador ejecutará el checkout vacío y el update enfocado
            adapter.sparse_pull(paths=[sparse_path], username=username, password=password)
            
            self.status_callback("Jailing completado: Workspace restrictivo preparado.", "green")
            return True
            
        except ValueError as ve:
            self.status_callback(f"Error de Resolución Kitsu: {str(ve)}", "red")
            return False
        except RuntimeError as re:
            # Atrapamos errores provenientes de CLI (SVNAdapter / GitAdapter)
            self.status_callback("Fallo de conexión en Sparse Checkout. Revisa credenciales.", "red")
            print(f"[MACUARE HUB] Error en SparseManager (Red/Auth): {re}")
            return False
        except Exception as e:
            self.status_callback(f"Error crítico durante el Jailing: {str(e)}", "red")
            return False
