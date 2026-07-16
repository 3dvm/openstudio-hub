# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/path_resolver.py
# Rol Arquitectónico: Motor Lógico / Kitsu Path Resolver
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.7
# =========================================================================================

"""
Traduce las entidades de la API de Kitsu (Tareas) a rutas físicas de disco local.
Implementa las convenciones de nomenclatura del estudio según el SDD, tanto
para directorios (Sparse Checkout) como para archivos finales (Deep Linking).
"""

from typing import Dict, Optional

class PathResolver:
    """
    Motor de resolución de rutas (Path Resolver).
    Calcula el path relativo necesario para orquestar el Sparse Checkout del VCS
    y la invocación de los archivos de trabajo en Blender.
    """
    
    @staticmethod
    def get_sparse_path(task_data: Dict[str, str]) -> Optional[str]:
        """
        Calcula la ruta relativa del directorio para el SparseManager.
        Retorna ej: 'pro/shots/sq01/sh010'
        """
        if not task_data:
            return None
            
        entity_type = task_data.get("entity_type", "").lower()
        entity_name = task_data.get("entity_name", "")
        
        if entity_type == "shot":
            seq_name = task_data.get("sequence_name", "")
            if not seq_name or not entity_name:
                raise ValueError("Metadatos incompletos para Shot: Falta sequence_name.")
            
            return f"pro/shots/{seq_name}/{entity_name}"
            
        elif entity_type == "asset":
            asset_type = task_data.get("asset_type_name", "")
            if not asset_type or not entity_name:
                raise ValueError("Metadatos incompletos para Asset: Falta asset_type_name.")
            
            return f"pro/assets/{asset_type}/{entity_name}"
            
        else:
            raise ValueError(f"Tipo de entidad Kitsu desconocido: {entity_type}")

    def resolve(self, task_data: Dict[str, str]) -> Optional[str]:
        """
        Calcula la ruta relativa exacta al archivo .blend de la tarea actual.
        Basado en el Diagrama 1.6 (Entity to path graph) del SDD.
        
        Retorna ej: 'shots/sq01/sh010/sh010-anim.blend'
        """
        if not task_data:
            return None
            
        entity_type = task_data.get("entity_type", "").lower()
        entity_name = task_data.get("entity_name", "")
        
        # Priorizar el short_name para archivos (ej. 'anim' en lugar de 'Animation')
        task_name = task_data.get("task_type_short_name", task_data.get("task_type_name", "")).lower()
        
        if entity_type == "shot":
            seq_name = task_data.get("sequence_name", "")
            if not seq_name or not entity_name:
                return None
                
            # Plantilla: shots/{seq}/{shot}/{shot}-{task}.blend
            return f"shots/{seq_name}/{entity_name}/{entity_name}-{task_name}.blend"
            
        elif entity_type == "asset":
            asset_type = task_data.get("asset_type_name", "")
            if not asset_type or not entity_name:
                return None
                
            # Plantilla: assets/{type}/{asset}/{type}-{asset}-{task}.blend
            return f"assets/{asset_type}/{entity_name}/{asset_type}-{entity_name}-{task_name}.blend"
            
        return None
