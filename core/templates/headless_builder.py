# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/templates/headless_builder.py
# Rol Arquitectónico: DCC Scripting / Creador Maestro de Archivos (VFS & Kitsu)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
# =========================================================================================

"""
Script ejecutado en modo Headless (background) por el ProjectBuilder o el ProductionManager.
Recibe órdenes mediante variables de entorno para ensamblar archivos .blend desde cero
utilizando los operadores nativos del add-on de Blender Kitsu.
"""

import bpy
import os
import sys

def inyectar_parche_proteccion_memoria():
    """
    Evita el crash de RNA desactivando la carga de archivos .blend 
    DENTRO de los operadores de Kitsu. Cargar archivos destruye 
    la instancia `self` del operador en modo Headless.
    """
    try:
        kitsu_module = sys.modules.get("bl_ext.user_default.blender_kitsu") or sys.modules.get("blender_kitsu")
        if not kitsu_module: return

        # Interceptamos la referencia directamente en el módulo 'ops' donde se usa
        kitsu_ops = kitsu_module.shot_builder.ops
        
        def parche_open_template(task_type_name):
            print(f"[HeadlessBuilder] 🛡️ Bypass de plantilla '{task_type_name}' ejecutado para proteger memoria RNA.")
            pass
            
        kitsu_ops.open_template_as_homefile = parche_open_template
        print("[HeadlessBuilder] ✓ Parche de protección de memoria RNA inyectado.")
        
    except Exception as e:
        print(f"[HeadlessBuilder] ⚠️ Advertencia: No se pudo inyectar protección de memoria: {e}")

def cargar_plantilla_segura(task_type_name: str = None, app_template: str = None):
    """Carga el template y restaura el contexto de Kitsu borrado por Blender."""
    import sys
    import bpy
    
    kitsu_module = sys.modules.get("bl_ext.user_default.blender_kitsu") or sys.modules.get("blender_kitsu")
    
    # 1. EXTRACCIÓN DE SALVAVIDAS (Antes de destruir la memoria de la escena)
    project_id = ""
    if kitsu_module:
        # El ProjectBuilder guardó el ID en las preferencias (que son globales y sobreviven al cambio de archivo)
        prefs = bpy.context.preferences.addons[kitsu_module.__name__].preferences
        project_id = getattr(prefs, "project_active_id", "")
        
    try:
        if app_template:
            print(f"[HeadlessBuilder] 🎬 Cargando App-Template '{app_template}' en contexto seguro...")
            bpy.ops.wm.read_homefile(app_template=app_template)
        elif task_type_name and kitsu_module:
            template_path = kitsu_module.shot_builder.template.get_template_for_task_type(task_type_name)
            if template_path and template_path.exists():
                print(f"[HeadlessBuilder] 🎬 Cargando plantilla '{task_type_name}' en contexto seguro...")
                bpy.ops.wm.open_mainfile(filepath=str(template_path), load_ui=False)
    except Exception as e:
        print(f"[HeadlessBuilder] Info: Omitiendo plantilla ({e})")
        
    # 2. REINYECCIÓN DEL CONTEXTO Y AUTENTICACIÓN
    if kitsu_module and project_id:
        print("[HeadlessBuilder] 🔑 Re-autenticando sesión (Bypass de amnesia de seguridad)...")
        # Forzamos el login nuevamente para reconstruir el token de Gazu borrado al abrir el archivo
        bpy.ops.kitsu.session_start('EXEC_DEFAULT')
        
        print(f"[HeadlessBuilder] ♻️ Restaurando contexto Kitsu en la nueva escena (Project ID: {project_id})")
        kitsu_module.cache.project_active_set_by_id(bpy.context, project_id)

def forjar_edit_master():
    print("[HeadlessBuilder] Iniciando forjado del Archivo Maestro de Edición...")
    inyectar_parche_proteccion_memoria()
    cargar_plantilla_segura(app_template="Storyboarding")
    
    try:
        bpy.ops.kitsu.create_edit_file(create_kitsu_edit=True, save_file=True)
        print("[HeadlessBuilder] ✓ Archivo Maestro de Edición forjado exitosamente.")
    except Exception as e:
        print(f"[HeadlessBuilder] ❌ Fallo crítico al crear el archivo Edit: {e}")

def forjar_shot():
    print("[HeadlessBuilder] Iniciando forjado de Shot (Toma)...")
    inyectar_parche_proteccion_memoria()
    try:
        kitsu_module = sys.modules.get("bl_ext.user_default.blender_kitsu") or sys.modules.get("blender_kitsu")
        task_type = kitsu_module.cache.task_type_active_get()
        cargar_plantilla_segura(task_type_name=task_type.name)

        bpy.ops.kitsu.build_new_shot(save_file=True)
        print("[HeadlessBuilder] ✓ Archivo de Toma forjado exitosamente.")
    except Exception as e:
        print(f"[HeadlessBuilder] ❌ Fallo crítico al crear el Shot: {e}")

def forjar_asset():
    print("[HeadlessBuilder] Iniciando forjado de Asset (Recurso)...")
    inyectar_parche_proteccion_memoria()
    try:
        cargar_plantilla_segura(task_type_name="Asset")
        bpy.ops.kitsu.build_new_asset(save_file=True)
        print("[HeadlessBuilder] ✓ Archivo de Asset forjado exitosamente.")
    except Exception as e:
        print(f"[HeadlessBuilder] ❌ Fallo crítico al crear el Asset: {e}")


def main():
    print("\n" + "="*50)
    print("[OPENSTUDIO HUB] Iniciando Constructor Headless...")
    
    # Extraemos el objetivo de construcción desde el orquestador Python
    build_target = os.environ.get("OPENSTUDIO_BUILD_TARGET", "EDIT").upper()
    
    # Validamos que el Hub haya inyectado y logueado Kitsu previamente
    # (El Hub asume que las credenciales y el ID del proyecto ya están en RAM).
    
    if build_target == "EDIT":
        forjar_edit_master()
    elif build_target == "SHOT":
        forjar_shot()
    elif build_target == "ASSET":
        forjar_asset()
    else:
        print(f"[HeadlessBuilder] ❌ Error: Objetivo de construcción desconocido -> {build_target}")

    print("[OPENSTUDIO HUB] Constructor Headless Finalizado.")
    print("="*50 + "\n")
    
    # Obligamos a Blender a cerrarse limpio tras ejecutar el trabajo en background
    sys.exit(0)

if __name__ == "__main__":
    main()
