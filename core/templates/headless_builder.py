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


        # =======================================================
        # 3. REINYECCIÓN DEL MONKEY PATCH (Supervivencia a read_homefile)
        # =======================================================
        import importlib
        from pathlib import Path
        vfs_svn = os.environ.get("OPENSTUDIO_VFS_SVN", "svn")
        kitsu_prefs_mod = importlib.import_module(f"{kitsu_module.__name__}.prefs")
        
        def custom_root_dir_get(context):
            pref_instance = kitsu_prefs_mod.addon_prefs_get(context)
            return Path(pref_instance.project_root_dir) / vfs_svn
            
        kitsu_prefs_mod.project_root_dir_get = custom_root_dir_get
        print(f"[HeadlessBuilder] 🛡️ Monkey patch VFS ({vfs_svn}) reinyectado tras cargar plantilla.")
        # =======================================================

        # =======================================================
        # 4. NUEVO: Parche de Guardado Síncrono (Anti-Timer)
        # =======================================================
        #kitsu_file_save = kitsu_module.shot_builder.file_save
        
        #def save_shot_sync(file_path: str) -> bool:
        #    from pathlib import Path
        #    if Path(file_path).exists(): return False
        #    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        #    
        #    # Guardado instantáneo, bloqueando el hilo principal hasta terminar
        #    bpy.ops.wm.save_mainfile(filepath=file_path, relative_remap=True)
        #    print(f"[HeadlessBuilder] 💾 Archivo físico escrito exitosamente en el disco.")
        #    return True
        #    
        #kitsu_file_save.save_shot_builder_file = save_shot_sync
        #print("[HeadlessBuilder] ✓ Parche de guardado síncrono (Anti-Timer) inyectado.")
        # =======================================================


# =======================================================
# FUNCIÓN MAESTRA (Template Method)
# =======================================================
def _guardar_entidad_forjada(filepath_str: str, debug_label: str = "ENTIDAD"):
    """
    Centraliza la I/O de disco: crea los directorios padres si no existen
    y ejecuta el guardado síncrono del archivo .blend maestro.
    """
    import bpy
    from pathlib import Path
    
    out_path = Path(filepath_str)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Guardado manual forzado (Síncrono y bloqueante)
    bpy.ops.wm.save_mainfile(filepath=str(out_path), relative_remap=True)
    print(f"[HeadlessBuilder DEBUG] 💾 GUARDADO DE {debug_label} EXITOSO EN: {out_path}")
    return out_path

# =======================================================
# CONSTRUCTORES ESPECÍFICOS (Strategias)
# =======================================================
def forjar_storyboard():
    print("[HeadlessBuilder] Iniciando forjado del Archivo Maestro de Storyboard...")
    inyectar_parche_proteccion_memoria()
    
# 1. Cargamos la plantilla nativa de Blender para Storyboard (2D Animation)
    try:
        print("[HeadlessBuilder] 🎬 Cargando plantilla nativa 'Storyboarding'...")
        #bpy.ops.wm.read_homefile(app_template="2D_Animation")
        cargar_plantilla_segura(app_template="Storyboarding")
    except Exception as e:
        print(f"[HeadlessBuilder] ⚠️ Plantilla Storyboarding no encontrada, usando default. Error: {e}")
        bpy.ops.wm.read_homefile()
        
    try:
        from pathlib import Path
        
        # 2. Extraer contexto inyectado por el Hub
        project_root = Path(os.environ.get("OPENSTUDIO_PROJECT_ROOT", ""))
        vfs_svn = os.environ.get("OPENSTUDIO_PRODUCTION_FOLDER", "svn")
        seq_name = os.environ.get("OPENSTUDIO_TARGET_SEQUENCE", "SQ000").lower()
        
        # 3. Construir la ruta (En la carpeta de edición, tal como lo definimos)
        # Formato esperado: pro/edit/{seq_name}-storyboard.blend
        out_path = project_root / vfs_svn / "edit" / "storyboards" / f"{seq_name}-storyboard.blend"
        
        # 4. Guardado manual forzado (Síncrono y bloqueante)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_mainfile(filepath=str(out_path), relative_remap=True)
        
        print(f"[HeadlessBuilder DEBUG] 💾 GUARDADO FORZADO EXITOSO EN: {out_path}")
        
    except Exception as e:
        print(f"[HeadlessBuilder] ❌ Fallo crítico al crear el archivo de Storyboard: {e}")

def forjar_edit_master():
    print("[HeadlessBuilder] Iniciando forjado del Archivo Maestro de Edición...")
    inyectar_parche_proteccion_memoria()
    cargar_plantilla_segura(app_template="Video Editing")
    
    try:
        bpy.ops.kitsu.create_edit_file(create_kitsu_edit=True, save_file=False)
        print("[HeadlessBuilder] ✓ Archivo Maestro de Edición configurado en memoria por Kitsu.")

        import sys
        kitsu_module = sys.modules.get("bl_ext.user_default.blender_kitsu") or sys.modules.get("blender_kitsu")
        edit_entity = kitsu_module.cache.edit_default_get(episode_id=bpy.context.scene.kitsu.episode_active_id)
        filepath_str = edit_entity.get_filepath(bpy.context)
        
        _guardar_entidad_forjada(filepath_str, "EDIT MASTER")
    except Exception as e:
        print(f"[HeadlessBuilder] ❌ Fallo crítico al crear el archivo Edit: {e}")

def forjar_shot():
    print("[HeadlessBuilder] Iniciando forjado de Shot (Toma)...")
    inyectar_parche_proteccion_memoria()
    
    try:
        import sys
        kitsu_module = sys.modules.get("bl_ext.user_default.blender_kitsu") or sys.modules.get("blender_kitsu")
        task_type = kitsu_module.cache.task_type_active_get()
        cargar_plantilla_segura(task_type_name=task_type.name)

        bpy.ops.kitsu.build_new_shot(save_file=False)
        
        shot = kitsu_module.cache.shot_active_get()
        filepath_str = shot.get_filepath(bpy.context, task_type.get_short_name())
        
        _guardar_entidad_forjada(filepath_str, "SHOT")
    except Exception as e:
        print(f"[HeadlessBuilder] ❌ Fallo crítico al crear el Shot: {e}")

def forjar_asset():
    print("[HeadlessBuilder] Iniciando forjado de Asset (Recurso)...")
    inyectar_parche_proteccion_memoria()
    
    try:
        cargar_plantilla_segura(task_type_name="Asset")
        bpy.ops.kitsu.build_new_asset(save_file=False)
        
        import sys
        kitsu_module = sys.modules.get("bl_ext.user_default.blender_kitsu") or sys.modules.get("blender_kitsu")
        asset = kitsu_module.cache.asset_active_get()
        filepath_str = asset.get_filepath(bpy.context)
        
        _guardar_entidad_forjada(filepath_str, "ASSET")
    except Exception as e:
        print(f"[HeadlessBuilder] ❌ Fallo crítico al crear el Asset: {e}")

# =======================================================
# MAIN ORCHESTRATOR
# =======================================================
def main():
    print("\n" + "="*50)
    print("[OPENSTUDIO HUB] Iniciando Constructor Headless...")
    
    build_target = os.environ.get("OPENSTUDIO_BUILD_TARGET", "STORYBOARD").upper()
    
    if build_target == "STORYBOARD":
        forjar_storyboard()
    elif build_target == "EDIT":
        forjar_edit_master()
    elif build_target == "SHOT":
        forjar_shot()
    elif build_target == "ASSET":
        forjar_asset()
    else:
        print(f"[HeadlessBuilder] ❌ Error: Objetivo de construcción desconocido -> {build_target}")

    print("[OPENSTUDIO HUB] Constructor Headless Finalizado.")
    print("="*50 + "\n")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
