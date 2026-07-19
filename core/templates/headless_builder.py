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

def inyectar_parche_editorial_kitsu():
    """
    Fuerza al add-on de Kitsu a usar 'Storyboarding' en lugar del 
    comportamiento por defecto al crear archivos de Edit.
    """
    try:
        import blender_kitsu.shot_builder.ops as kitsu_ops
        original_open_template = kitsu_ops.open_template_as_homefile
        
        def parche_open_template(task_type_name):
            if task_type_name.lower() in ["edit", "editorial"]:
                print("[HeadlessBuilder] 🎬 Interceptando Kitsu: Inyectando plantilla 'Storyboarding'...")
                bpy.ops.wm.read_homefile(app_template="Storyboarding")
            else:
                original_open_template(task_type_name)
                
        kitsu_ops.open_template_as_homefile = parche_open_template
        print("[HeadlessBuilder] ✓ Parche Editorial (Storyboarding) inyectado con éxito.")
        
    except ImportError:
        print("[HeadlessBuilder] ⚠️ Advertencia: No se pudo parchear. El add-on blender_kitsu no está activo o instalado.")

def forjar_edit_master():
    print("[HeadlessBuilder] Iniciando forjado del Archivo Maestro de Edición...")
    inyectar_parche_editorial_kitsu()
    
    try:
        # Se invoca al operador nativo, delegando el guardado en disco a su motor
        bpy.ops.kitsu.create_edit_file(create_kitsu_edit=True, save_file=True)
        print("[HeadlessBuilder] ✓ Archivo Maestro de Edición forjado exitosamente.")
    except Exception as e:
        print(f"[HeadlessBuilder] ❌ Fallo crítico al crear el archivo Edit: {e}")

def forjar_shot():
    print("[HeadlessBuilder] Iniciando forjado de Shot (Toma)...")
    try:
        # Aquí el ProductionManager ya habrá inyectado el contexto en las propiedades
        # de la escena (scene.kitsu) mediante otro script o variables de entorno.
        bpy.ops.kitsu.build_new_shot(save_file=True)
        print("[HeadlessBuilder] ✓ Archivo de Toma forjado exitosamente.")
    except Exception as e:
        print(f"[HeadlessBuilder] ❌ Fallo crítico al crear el Shot: {e}")

def forjar_asset():
    print("[HeadlessBuilder] Iniciando forjado de Asset (Recurso)...")
    try:
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
