import bpy
import os
import addon_utils

def _setup_openstudio_environment():
    """Inicializa el entorno dinámico basado en las variables inyectadas por el Hub."""
    print("\n" + "="*50)
    print("[OPENSTUDIO HUB] Iniciando Bootstrap en Blender (Post-RestrictBlend)...")
    
    # 1. Extraer contexto inyectado
    user_role = os.environ.get("OPENSTUDIO_USER_ROLE", "artist").lower()
    task_type = os.environ.get("OPENSTUDIO_TASK_TYPE", "generic").lower()
    project_root = os.environ.get("OPENSTUDIO_PROJECT_ROOT", "")
    
    kitsu_user = os.environ.get("OPENSTUDIO_KITSU_USER", "")
    kitsu_pwd = os.environ.get("OPENSTUDIO_KITSU_PWD", "")
    kitsu_host = os.environ.get("OPENSTUDIO_KITSU_HOST", "")
    
    print(f"[OPENSTUDIO HUB] Contexto -> Rol: {user_role.upper()} | Tarea: {task_type.upper()}")
    
    # 2. Activar herramientas y add-ons (Resolución dinámica de namespaces)
    kitsu_module = _activar_herramientas_contextuales(task_type)
    
    # 3. Autenticación Asíncrona con Inyección en UI (Zero-Disk Passwords)
    if kitsu_user and kitsu_pwd and kitsu_host and kitsu_module:
        _autenticar_kitsu_silencioso(kitsu_host, kitsu_user, kitsu_pwd, kitsu_module)
    
    # 4. Aplicar Guardrails (Jailing UI)
    if user_role not in ["lead", "supervisor", "td"]:
        _aplicar_guardrails_rbac()
        
    print("="*50 + "\n")
    return None # Limpia el timer (run once)

def _activar_herramientas_contextuales(task_type: str) -> str:
    """Activa extensiones resolviendo su namespace real (API 4.2+) y retorna el módulo de Kitsu."""
    base_addons = ["blender_kitsu"]
    kitsu_real_module = "blender_kitsu"
    
    # Lógica de Context-Aware Tooling
    if task_type in ["modeling", "rigging", "surfacing", "texturing", "lookdev"]:
        base_addons.append("asset_pipeline")
        
    if task_type in ["animation", "anim"]:
        base_addons.extend(["pose_library", "rigify"])
    elif task_type in ["lookdev", "lighting"]:
        base_addons.extend(["node_wrangler"])
        
    # Obtener todos los nombres de módulos instalados (incluyendo bl_ext.user_default...)
    modulos_instalados = [mod.__name__ for mod in addon_utils.modules()]
    
    for base_name in base_addons:
        # Busca si existe una extensión cuyo nombre termine en el nombre base que buscamos
        real_module = next((mod for mod in modulos_instalados if mod.endswith(base_name)), base_name)
        
        if base_name == "blender_kitsu":
            kitsu_real_module = real_module
            
        try:
            # Carga usando el nombre absoluto
            bpy.ops.preferences.addon_enable(module=real_module)
            print(f"[OPENSTUDIO HUB] Extensión habilitada: {real_module}")
        except Exception as e:
            print(f"[OPENSTUDIO HUB] Fallo al habilitar {real_module}: {e}")
            
    return kitsu_real_module

def _autenticar_kitsu_silencioso(kitsu_host: str, kitsu_user: str, kitsu_pwd: str, kitsu_module: str):
    """Inyecta las credenciales JIT en las preferencias del Add-on antes de pulsar Login."""
    print(f"[OPENSTUDIO HUB] Inyectando credenciales JIT en preferencias de: {kitsu_module}...")
    try:
        # Obtenemos el acceso a la estructura usando el namespace absoluto
        prefs = bpy.context.preferences.addons.get(kitsu_module)
        
        if not prefs:
            print(f"[OPENSTUDIO HUB] ERROR: No se pudieron cargar las preferencias de {kitsu_module}.")
            return
            
        addon_prefs = prefs.preferences
        
        addon_prefs.host = kitsu_host
        addon_prefs.email = kitsu_user
        addon_prefs.passwd = kitsu_pwd
        
        if hasattr(bpy.ops.kitsu, "session_start"):
            bpy.ops.kitsu.session_start('EXEC_DEFAULT')
            
            if addon_prefs.session.is_auth():
                print("[OPENSTUDIO HUB] Login exitoso. Token establecido en RAM.")
            else:
                print("[OPENSTUDIO HUB] Fallo lógico: Kitsu rechazó las credenciales.")
            
    except Exception as e:
        print(f"[OPENSTUDIO HUB] Fallo critico al inyectar credenciales en Kitsu: {e}")

def _aplicar_guardrails_rbac():
    """Secuestra botones destructivos usando Runtime Polling Override."""
    print("[OPENSTUDIO HUB] Aplicando seguridad estricta RBAC (Jailing UI)...")
    
    if hasattr(bpy.types, "ASSETPIPE_OT_force_push"):
        @classmethod
        def poll_restringido(cls, context):
            return False # Deshabilita el botón visualmente
            
        bpy.types.ASSETPIPE_OT_force_push.poll = poll_restringido
        print("[OPENSTUDIO HUB] OVERRIDE: ASSETPIPE_OT_force_push bloqueado.")

# Timer para asegurar que Blender cargue la GUI antes de ejecutar operadores interactivos
if __name__ == "__main__":
    print("[OPENSTUDIO HUB] Registrando Bootstrap en Main Loop...")
    bpy.app.timers.register(_setup_openstudio_environment, first_interval=1.0)
