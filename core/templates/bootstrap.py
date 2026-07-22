# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/templates/bootstrap.py
# Rol Arquitectónico: DCC Scripting / Pre-Flight Config & Jailing
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.9
# =========================================================================================

"""
Script de inyección ejecutado asíncronamente al iniciar Blender.
Aplica la Matriz RBAC, activa extensiones contextualmente, establece credenciales RAM,
abre el archivo de la tarea (si existe), e invoca la autodetección nativa del contexto Kitsu.
"""

import bpy
import os
import importlib
import addon_utils
from pathlib import Path

def _setup_openstudio_environment():
    print("\n" + "="*50)
    print("[OPENSTUDIO HUB] Iniciando Bootstrap en Blender (Post-RestrictBlend)...")
    
    # 1. Extraer contexto inyectado
    user_role = os.environ.get("OPENSTUDIO_USER_ROLE", "artist").lower()
    task_type = os.environ.get("OPENSTUDIO_TASK_TYPE", "generic").lower()
    project_root = os.environ.get("OPENSTUDIO_PROJECT_ROOT", "")
    prod_folder = os.environ.get("OPENSTUDIO_PRODUCTION_FOLDER", "02_archivos_de_produccion")
    project_id = os.environ.get("OPENSTUDIO_KITSU_PROJECT_ID", "")
    target_file = os.environ.get("OPENSTUDIO_TARGET_FILE", "")
    entity_type = os.environ.get("OPENSTUDIO_KITSU_ENTITY_TYPE", "").upper()
    
    kitsu_user = os.environ.get("OPENSTUDIO_KITSU_USER", "")
    kitsu_pwd = os.environ.get("OPENSTUDIO_KITSU_PWD", "")
    kitsu_host = os.environ.get("OPENSTUDIO_KITSU_HOST", "")
    
    print(f"[OPENSTUDIO HUB] Contexto -> Rol: {user_role.upper()} | Tarea: {task_type.upper()}")
    
    # 2. Activar herramientas y add-ons
    kitsu_module = _activar_herramientas_contextuales(task_type)
    
    _inyectar_splash_screen()
    
    # 3. Preferencias Globales Físicas y Autenticación
    if kitsu_module:
        _configurar_preferencias_estudio(kitsu_module, project_root, prod_folder)
        if kitsu_user and kitsu_pwd and kitsu_host:
            _autenticar_kitsu_silencioso(kitsu_host, kitsu_user, kitsu_pwd, kitsu_module, project_id)
            
    _blindar_asset_pipeline(project_root)
    
    # 4. Carga de Archivo y Contexto Kitsu (Strict Mode)
    if target_file and os.path.exists(target_file):
        print(f"[OPENSTUDIO HUB] Cargando archivo de producción: {target_file}")
        try:
            bpy.ops.wm.open_mainfile(filepath=target_file)
            
            # Autodetección nativa de Kitsu tras abrir el archivo
            if kitsu_module and hasattr(bpy.ops.kitsu, "con_detect_context"):
                print("[OPENSTUDIO HUB] Invocando autodetector nativo de Kitsu...")
                bpy.ops.kitsu.con_detect_context('EXEC_DEFAULT')
                print("[OPENSTUDIO HUB] Auto-navegación completada con éxito.")
                
        except Exception as e:
            print(f"[OPENSTUDIO HUB] Advertencia: No se pudo abrir el archivo {e}")
    else:
        # El archivo NO existe. Aplicamos la regla estricta: Los artistas NO construyen.
        print(f"[OPENSTUDIO HUB] ADVERTENCIA: El archivo base no existe en la ruta esperada: {target_file}")
        if user_role in ["lead", "supervisor", "td", "manager"]:
            print("[OPENSTUDIO HUB] Modo Administrador: Puedes utilizar el Shot Builder manualmente si lo deseas.")
            _inyectar_cache_basica(kitsu_module, entity_type)
        else:
            print("[OPENSTUDIO HUB] BLOQUEO RBAC: Los Artistas/Vendors no están autorizados a inicializar archivos.")
            _inyectar_cache_basica(kitsu_module, entity_type)

    # 5. Aplicar Guardrails (Jailing UI)
    if user_role not in ["lead", "supervisor", "td"]:
        _aplicar_guardrails_rbac()
        
    print("="*50 + "\n")
    return None

def _activar_herramientas_contextuales(task_type: str) -> str:
    base_addons = ["blender_kitsu"]
    kitsu_real_module = "blender_kitsu"
    
    if task_type in ["modeling", "rigging", "surfacing", "texturing", "lookdev"]:
        base_addons.append("asset_pipeline")
        
    if task_type in ["animation", "anim"]:
        base_addons.extend(["pose_library", "rigify"])
    elif task_type in ["lookdev", "lighting"]:
        base_addons.extend(["node_wrangler"])
        
    modulos_instalados = [mod.__name__ for mod in addon_utils.modules()]
    
    for base_name in base_addons:
        real_module = next((mod for mod in modulos_instalados if mod.endswith(base_name)), base_name)
        if base_name == "blender_kitsu":
            kitsu_real_module = real_module
            
        try:
            bpy.ops.preferences.addon_enable(module=real_module)
        except Exception as e:
            print(f"[OPENSTUDIO HUB] Fallo al habilitar {real_module}: {e}")
            
    return kitsu_real_module

def _configurar_preferencias_estudio(kitsu_module: str, project_root: str, prod_folder: str):
    prefs = bpy.context.preferences.addons.get(kitsu_module)
    if not prefs: return
    
    addon_prefs = prefs.preferences
    try:
        if project_root and hasattr(addon_prefs, "project_root_dir"):
            addon_prefs.project_root_dir = project_root
            
        if hasattr(addon_prefs, "version_control"):
            addon_prefs.version_control = True
            
        # =================================================================
        # INYECCIÓN DE DIRECTORIOS (VFS ALIGNMENT)
        # =================================================================
        # Kitsu ya encadena internamente "pro/" o "pre/", por lo tanto
        # inyectamos los nombres de los directorios en su estado puro.
        if hasattr(addon_prefs, "shot_dir_name"):
            addon_prefs.shot_dir_name = "shots"
        if hasattr(addon_prefs, "asset_dir_name"):
            addon_prefs.asset_dir_name = "assets"
        if hasattr(addon_prefs, "seq_dir_name"):
            addon_prefs.seq_dir_name = "strips"
        if hasattr(addon_prefs, "edit_dir_name"):
            addon_prefs.edit_dir_name = "edit"
            
        # =================================================================
        # MONKEY-PATCHING: Sobrescribir función hardcodeada de Kitsu
        # =================================================================
        kitsu_prefs_mod = importlib.import_module(f"{kitsu_module}.prefs")
        
        def custom_project_root_dir_get(context):
            pref_instance = kitsu_prefs_mod.addon_prefs_get(context)
            # Reemplazamos el hardcoded 'project_files' por el nombre del directorio
            # dinámico definido en la configuración maestro del estudio.
            return Path(pref_instance.project_root_dir) / prod_folder
            
        kitsu_prefs_mod.project_root_dir_get = custom_project_root_dir_get
        print(f"[OPENSTUDIO HUB] Monkey-Patch Exitoso: Rutas de Kitsu enrutadas hacia {prod_folder}.")
            
    except Exception as e:
        print(f"[OPENSTUDIO HUB] Advertencia al configurar preferencias Kitsu: {e}")

def _blindar_asset_pipeline(project_root: str):
    if not project_root: return
    modulos_instalados = [mod.__name__ for mod in addon_utils.modules()]
    ap_module = next((mod for mod in modulos_instalados if mod.endswith("asset_pipeline")), None)
    
    if ap_module:
        prefs_ap = bpy.context.preferences.addons.get(ap_module)
        if prefs_ap:
            try:
                if hasattr(prefs_ap.preferences, "project_directory"):
                    prefs_ap.preferences.project_directory = project_root
                elif hasattr(prefs_ap.preferences, "project_dir"):
                    prefs_ap.preferences.project_dir = project_root
            except Exception:
                pass

def _autenticar_kitsu_silencioso(kitsu_host: str, kitsu_user: str, kitsu_pwd: str, kitsu_module: str, project_id: str):
    try:
        prefs = bpy.context.preferences.addons.get(kitsu_module)
        if not prefs: return
            
        addon_prefs = prefs.preferences
        addon_prefs.host = kitsu_host
        addon_prefs.email = kitsu_user
        addon_prefs.passwd = kitsu_pwd
        
        if hasattr(bpy.ops.kitsu, "session_start"):
            bpy.ops.kitsu.session_start('EXEC_DEFAULT')
            
            if hasattr(bpy.ops.kitsu, "con_productions_load"):
                bpy.ops.kitsu.con_productions_load('EXEC_DEFAULT')
                
            if project_id:
                try:
                    kitsu_cache = importlib.import_module(f"{kitsu_module}.cache")
                    kitsu_cache.project_active_set_by_id(bpy.context, project_id)
                    addon_prefs.project_active_id = project_id 
                except Exception as cache_err:
                    print(f"[OPENSTUDIO HUB] Error inyectando caché de proyecto: {cache_err}")
                
    except Exception as e:
        print(f"[OPENSTUDIO HUB] Fallo al inyectar credenciales: {e}")

def _inyectar_cache_basica(kitsu_module: str, entity_type: str):
    """Inyecta el contexto visualmente en Kitsu si el archivo físico aún no existe."""
    try:
        kitsu_cache = importlib.import_module(f"{kitsu_module}.cache")
        entity_id = os.environ.get("OPENSTUDIO_KITSU_ENTITY_ID", "")
        task_type_id = os.environ.get("OPENSTUDIO_KITSU_TASK_TYPE_ID", "")

        if entity_type == "SHOT" and entity_id:
            seq_id = os.environ.get("OPENSTUDIO_KITSU_SEQUENCE_ID", "")
            if seq_id: kitsu_cache.sequence_active_set_by_id(bpy.context, seq_id)
            kitsu_cache.shot_active_set_by_id(bpy.context, entity_id)
            
        elif entity_type == "ASSET" and entity_id:
            asset_type_id = os.environ.get("OPENSTUDIO_KITSU_ASSET_TYPE_ID", "")
            if asset_type_id: kitsu_cache.asset_type_active_set_by_id(bpy.context, asset_type_id)
            kitsu_cache.asset_active_set_by_id(bpy.context, entity_id)

        if task_type_id:
            kitsu_cache.task_type_active_set_by_id(bpy.context, task_type_id)

    except Exception:
        pass

def _inyectar_splash_screen():
    """Sobrescribe la UI de Blender para cargar el Splash Screen corporativo del proyecto."""
    splash_path = os.environ.get("OPENSTUDIO_SPLASH_PATH", "")
    
    if not splash_path or not os.path.exists(splash_path):
        return
        
    def custom_splash_handler(dummy=None):
        import bpy
        from pathlib import Path
        img_name = Path(splash_path).name
        
        # Cargar a memoria solo si no existe
        if img_name not in bpy.data.images:
            bpy.data.images.load(splash_path)
            
        try:
            bpy.context.preferences.view.splash_image = img_name
        except Exception as e:
            print(f"[OPENSTUDIO HUB] Fallo al aplicar imagen splash: {e}")
            
    # Añadimos el handler para que Blender lo dibuje al terminar de inicializar
    import bpy
    bpy.app.handlers.load_post.append(custom_splash_handler)
    print(f"[OPENSTUDIO HUB] Splash Screen programado: {splash_path}")

def _aplicar_guardrails_rbac():
    @classmethod
    def poll_restringido(cls, context):
        return False 
        
    if hasattr(bpy.types, "ASSETPIPE_OT_force_push"):
        bpy.types.ASSETPIPE_OT_force_push.poll = poll_restringido
        
    if hasattr(bpy.types, "OPENSTUDIO_OT_override_sanity"):
        bpy.types.OPENSTUDIO_OT_override_sanity.poll = poll_restringido

if __name__ == "__main__":
    bpy.app.timers.register(_setup_openstudio_environment, first_interval=1.0)
