# =========================================================================================
# OPENSTUDIOHUB
# Módulo: addons/openstudio_toolkit/utils_logger.py
# Rol Arquitectónico: QA Pasivo / Wrapper de Telemetría (blender_log)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.0
# =========================================================================================

"""
Envoltorio (Wrapper) seguro para el add-on de terceros 'blender_log'.
Permite inyectar alertas visuales (QA Pasivo) en la interfaz de Blender sin generar
dependencias fatales. Si 'blender_log' no está disponible, realiza un fallback seguro.
"""

import bpy
import addon_utils

def _is_blender_log_enabled() -> bool:
    """Verifica de forma segura si el add-on blender_log está instalado y activo."""
    # addon_utils.check() devuelve una tupla: (cargado_por_defecto, estado_cargado)
    try:
        estado = addon_utils.check("blender_log")
        return estado[1]
    except Exception:
        return False

def clear_log_category(context: bpy.types.Context, category: str):
    """
    Limpia una categoría entera de problemas en el panel visual.
    Útil para evitar duplicados al re-evaluar la escena.
    """
    if _is_blender_log_enabled():
        try:
            context.scene.blender_log.clear_category(category)
        except AttributeError:
            pass # Fallback silencioso si la API de blender_log cambió

def report_issue(
    context: bpy.types.Context,
    name: str,
    description: str = "",
    icon: str = "INFO",
    category: str = "OpenStudio Hub",
    operator: str = "",
    op_kwargs: dict = None,
    op_text: str = "",
    op_icon: str = ""
):
    """
    Añade una tarjeta de advertencia/error a la lista persistente en la UI.
    Si blender_log no está activo, imprime el error en la terminal del Hub como Fallback.
    """
    if op_kwargs is None:
        op_kwargs = {}

    if _is_blender_log_enabled():
        try:
            context.scene.blender_log.add(
                name=name,
                description=description,
                icon=icon,
                category=category,
                operator=operator,
                op_kwargs=op_kwargs,
                op_text=op_text,
                op_icon=op_icon
            )
            return
        except AttributeError:
            pass # Si falla el context, caemos al fallback

    # FALLBACK SECUNDARIO (Si el add-on no existe)
    print(f"\n[QA PASIVO] {category} | {name}")
    if description:
        print(f" -> {description}")
    if operator:
        print(f" -> Solución sugerida: Ejecutar operador '{operator}'")

# ---------------------------------------------------------
# REGISTRO
# ---------------------------------------------------------

def register():
    # Solo son utilidades puras de Python, no requieren registro en bpy
    pass

def unregister():
    pass
