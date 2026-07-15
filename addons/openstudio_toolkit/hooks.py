# =========================================================================================
# OPENSTUDIOHUB
# Módulo: addons/openstudio_toolkit/hooks.py
# Rol Arquitectónico: API Integration / Kitsu Synergy
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.0
# =========================================================================================

"""
Módulo de ganchos (Hooks) de integración de terceros.
Delega procesos complejos a add-ons preexistentes (como Blender Kitsu)
una vez que el Gatekeeper ha dado luz verde a la sanidad del archivo.
"""

import bpy

def disparar_playblast_kitsu():
    """
    Invoca el operador nativo de Blender Kitsu para renderizar el Playblast
    y subirlo a la API, cambiando el estado de la tarea en el servidor.
    """
    try:
        # Verificamos si el add-on de Kitsu está habilitado y expone su operador
        if hasattr(bpy.ops.kitsu, "push_playblast"):
            # Usamos 'INVOKE_DEFAULT' para levantar la ventana modal de Kitsu,
            # permitiendo al artista escribir su comentario de entrega.
            bpy.ops.kitsu.push_playblast('INVOKE_DEFAULT')
            print("[SYNERGY HOOK] Operador 'push_playblast' de Blender Kitsu invocado exitosamente.")
            return True
            
        # Fallback genérico por si la API de Blender Studio cambia el nombre del operador
        elif hasattr(bpy.ops.kitsu, "push"):
            bpy.ops.kitsu.push('INVOKE_DEFAULT')
            print("[SYNERGY HOOK] Operador 'push' de Blender Kitsu invocado (Fallback).")
            return True
            
        else:
            print("[SYNERGY HOOK ERROR] No se encontró un operador compatible en el add-on de Kitsu.")
            return False
            
    except Exception as e:
        print(f"[SYNERGY HOOK FATAL ERROR] Excepción al delegar el evento a Kitsu: {e}")
        return False

def register():
    # Este módulo expone funciones puras, no requiere registrar clases en bpy
    pass

def unregister():
    pass
