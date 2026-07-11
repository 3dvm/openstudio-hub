# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/path_resolver.py
# Rol Arquitectónico: Motor Lógico / Kitsu Path Resolver
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.4.0
# =========================================================================================

"""
Traduce las entidades de la API de Kitsu (Tareas) a rutas físicas de disco local.
Implementa las convenciones de nomenclatura del estudio según el SDD.
"""

from typing import Dict, Optional

class PathResolver:
    """
    Motor de resolución de rutas (Path Resolver).
    Calcula el path relativo necesario para orquestar el Sparse Checkout del VCS.
    """
    
    @staticmethod
    def get_sparse_path(task_data: Dict[str, str]) -> Optional[str]:
        """
        Recibe un diccionario con los metadatos de la Tarea parseada desde Kitsu
        y devuelve la ruta relativa del directorio de trabajo exacto.
        
        Estructura esperada en task_data:
        - 'entity_type': 'Shot' o 'Asset'
        - 'entity_name': ej. 'sh010' o 'Prota'
        - 'sequence_name': ej. 'sq01' (Solo exigido para Shots)
        - 'asset_type_name': ej. 'Character' (Solo exigido para Assets)
        """
        if not task_data:
            return None
            
        entity_type = task_data.get("entity_type", "").lower()
        entity_name = task_data.get("entity_name", "")
        
        if entity_type == "shot":
            seq_name = task_data.get("sequence_name", "")
            if not seq_name or not entity_name:
                raise ValueError("Metadatos de Kitsu incompletos para Shot: Falta sequence_name o entity_name.")
            
            # Convención Shot: pro/shots/{seq}/{shot}
            return f"pro/shots/{seq_name}/{entity_name}"
            
        elif entity_type == "asset":
            asset_type = task_data.get("asset_type_name", "")
            if not asset_type or not entity_name:
                raise ValueError("Metadatos de Kitsu incompletos para Asset: Falta asset_type_name o entity_name.")
            
            # Convención Asset: pro/assets/{type}/{asset}
            return f"pro/assets/{asset_type}/{entity_name}"
            
        else:
            raise ValueError(f"Tipo de entidad Kitsu desconocido o no soportado: {entity_type}")
