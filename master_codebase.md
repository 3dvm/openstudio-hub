# Estructura y Código del Proyecto: openstudio-hub

A continuación se presenta el código fuente concatenado del proyecto.

================================================================================

### Archivo: `_version.py`

```python
## =========================================================================================
# OPENSTUDIOHUB
# Módulo: _version.py
# Rol Arquitectónico: Main App Root / Orquestador Inicial (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.6.3
# =========================================================================================

# Tupla para comparaciones lógicas internas
VERSION_INFO = (0, 6, 5)

# String en formato Semantic Versioning (SemVer)
__version__ = ".".join(map(str, VERSION_INFO))

```

--------------------------------------------------------------------------------

### Archivo: `addons/openstudio_toolkit/__init__.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: addons/openstudio_toolkit/__init__.py
# Rol Arquitectónico: DCC Add-on Entry Point
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.0
# =========================================================================================

"""
Punto de entrada oficial para la extensión OpenStudio Toolkit en Blender 5.x.
Gestiona el registro de clases, módulos (como Gatekeeper) y operadores nativos.
"""

import bpy
from . import gatekeeper
from . import ui_modals
from . import hooks
from . import utils_logger

# Importaremos los módulos a medida que los vayamos construyendo en esta Fase
# from . import gatekeeper

modules = [
    gatekeeper,
    ui_modals,
    hooks,
    utils_logger,
]

def register():
    """Registra dinámicamente todos los submódulos del Toolkit."""
    for mod in modules:
        if hasattr(mod, "register"):
            mod.register()
    print("[OPENSTUDIO TOOLKIT] Extensión inicializada correctamente.")

def unregister():
    """Desregistra los submódulos en orden inverso para evitar dependencias colgadas."""
    for mod in reversed(modules):
        if hasattr(mod, "unregister"):
            mod.unregister()
    print("[OPENSTUDIO TOOLKIT] Extensión deshabilitada.")

if __name__ == "__main__":
    register()

```

--------------------------------------------------------------------------------

### Archivo: `addons/openstudio_toolkit/gatekeeper.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: addons/openstudio_toolkit/gatekeeper.py
# Rol Arquitectónico: DCC Scripting / Quality Assurance (QA)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.7
# =========================================================================================

"""
Módulo principal de The Gatekeeper.
Implementa el Scene Sanity Check, la purga de datos huérfanos, validación de dependencias,
auditoría matemática de la geometría y detona los hooks de publicación.
"""

import bpy
import os
import shutil
import math
from . import hooks

PRIMITIVAS_PROHIBIDAS = {
    "Cube", "Sphere", "Cylinder", "Cone", "Torus", "Plane", "Monkey", "Suzanne", "Circle",
    "BézierCurve", "BezierCurve", "GPencil", "Grid", "Icosphere", "Mball", "NurbsCurve", "NurbsPath",
    "Armature"
}

# Constante para auditar todos los objetos transformables en el pipeline
TIPOS_AUDITABLES = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'ARMATURE', 'GPENCIL', 'GREASEPENCIL'}

# ---------------------------------------------------------
# FUNCIONES DE LA FASE 1: LIMPIEZA
# ---------------------------------------------------------

def purgar_huerfanos_recursivo() -> int:
    total_purgados = 0
    purgados_en_pasada = 1
    
    while purgados_en_pasada > 0:
        purgados_en_pasada = bpy.data.orphans_purge(
            do_local_ids=True, 
            do_linked_ids=True, 
            do_recursive=True
        )
        total_purgados += purgados_en_pasada
        
    return total_purgados

def aislar_coleccion_temp() -> bool:
    temp_col = bpy.data.collections.get("__TEMP__")
    if not temp_col:
        return False
        
    for layer_collection in bpy.context.view_layer.layer_collection.children:
        if layer_collection.collection.name == "__TEMP__":
            layer_collection.exclude = True
            return True
            
    return False

# ---------------------------------------------------------
# FUNCIONES DE LA FASE 2: AUDITORÍA DE DEPENDENCIAS
# ---------------------------------------------------------

def escanear_out_of_bounds() -> list:
    project_root = os.environ.get("OPENSTUDIO_PROJECT_ROOT")
    
    if not project_root:
        if not bpy.data.filepath:
            return []
        project_root = os.path.dirname(bpy.data.filepath)
        
    project_root = os.path.normpath(project_root)
    infractores = []

    for img in bpy.data.images:
        if not img.filepath or img.packed_file or img.source in ('GENERATED', 'VIEWER'):
            continue
            
        abs_path = os.path.normpath(bpy.path.abspath(img.filepath))
        if not abs_path.startswith(project_root):
            infractores.append({
                "tipo": "IMAGE",
                "nombre": img.name,
                "ruta_actual": abs_path,
                "datablock": img
            })
                
    return infractores

def auto_fix_dependencias(infractores: list, clasificaciones: dict) -> int:
    blend_dir = os.path.dirname(bpy.data.filepath)
    siendo_fijados = 0
    
    for item in infractores:
        nombre = item["nombre"]
        ruta_origen = item["ruta_actual"]
        datablock = item["datablock"]
        
        categoria = clasificaciones.get(nombre, "textures")
        ruta_destino_dir = os.path.join(blend_dir, categoria)
        
        if not os.path.exists(ruta_destino_dir):
            os.makedirs(ruta_destino_dir)
            
        nombre_archivo = os.path.basename(ruta_origen)
        ruta_destino_archivo = os.path.join(ruta_destino_dir, nombre_archivo)
        
        try:
            shutil.copy2(ruta_origen, ruta_destino_archivo)
            datablock.filepath = ruta_destino_archivo
            siendo_fijados += 1
        except Exception as e:
            print(f"[CONSERJE ERROR] No se pudo copiar {nombre}: {e}")

    bpy.ops.file.make_paths_relative()
    return siendo_fijados

# ---------------------------------------------------------
# FUNCIONES DE LA FASE 2.5: SANIDAD MATEMÁTICA Y GEOMETRÍA
# ---------------------------------------------------------

def escanear_geometria_sucia() -> list:
    infractores = []
    for obj in bpy.context.view_layer.objects:
        if obj.type in TIPOS_AUDITABLES:
            loc_sucia = not (math.isclose(obj.location.x, 0.0, abs_tol=1e-4) and 
                             math.isclose(obj.location.y, 0.0, abs_tol=1e-4) and 
                             math.isclose(obj.location.z, 0.0, abs_tol=1e-4))
                             
            rot_sucia = not (math.isclose(obj.rotation_euler.x, 0.0, abs_tol=1e-4) and 
                             math.isclose(obj.rotation_euler.y, 0.0, abs_tol=1e-4) and 
                             math.isclose(obj.rotation_euler.z, 0.0, abs_tol=1e-4))
                             
            esc_sucia = not (math.isclose(obj.scale.x, 1.0, abs_tol=1e-4) and 
                             math.isclose(obj.scale.y, 1.0, abs_tol=1e-4) and 
                             math.isclose(obj.scale.z, 1.0, abs_tol=1e-4))
            
            if loc_sucia or rot_sucia or esc_sucia:
                infractores.append(obj.name)
                
    return infractores

def aplicar_transformaciones(nombres_infractores: list) -> int:
    if not nombres_infractores: return 0
    fijados = 0
    modo_original = bpy.context.object.mode if bpy.context.object else 'OBJECT'
    if modo_original != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    for nombre in nombres_infractores:
        obj = bpy.context.scene.objects.get(nombre)
        if obj and obj.name in bpy.context.view_layer.objects:
            estado_oculto = obj.hide_get()
            estado_seleccion = obj.hide_select
            
            obj.hide_set(False)
            obj.hide_select = False
            
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            obj.select_set(False)
            
            obj.hide_set(estado_oculto)
            obj.hide_select = estado_seleccion
            fijados += 1
            
    if modo_original != 'OBJECT': bpy.ops.object.mode_set(mode=modo_original)
    return fijados

def limpiar_transformaciones(nombres_infractores: list) -> int:
    if not nombres_infractores: return 0
    fijados = 0

    for nombre in nombres_infractores:
        obj = bpy.context.scene.objects.get(nombre)
        if obj:
            obj.location = (0.0, 0.0, 0.0)
            obj.rotation_euler = (0.0, 0.0, 0.0)
            obj.scale = (1.0, 1.0, 1.0)
            fijados += 1
            
    return fijados

# ---------------------------------------------------------
# FUNCIONES DE LA FASE 2.6: NOMENCLATURA
# ---------------------------------------------------------

def _obtener_asset_name() -> str:
    nombre_archivo = bpy.path.basename(bpy.context.blend_data.filepath) or "Asset"
    if "-" in nombre_archivo:
        return "-".join(nombre_archivo.split("-")[:-1])
    return "Asset"

def escanear_nombres_sucios() -> list:
    infractores = []
    asset_name = _obtener_asset_name()
    
    for obj in bpy.context.view_layer.objects:
        if obj.type in TIPOS_AUDITABLES:
            nombre_base = obj.name.split('.')[0]
            if nombre_base in PRIMITIVAS_PROHIBIDAS:
                infractores.append(obj.name)
            elif not obj.name.startswith(f"{asset_name}-"):
                infractores.append(obj.name)
                
    return infractores

def auto_fix_nombres(nombres_infractores: list) -> int:
    if not nombres_infractores: return 0
    asset_name = _obtener_asset_name()
    fijados = 0

    for nombre in nombres_infractores:
        obj = bpy.context.scene.objects.get(nombre)
        if obj:
            nombre_limpio = obj.name.split('.')[0]
            if not nombre_limpio.startswith(f"{asset_name}-"):
                nuevo_nombre = f"{asset_name}-{nombre_limpio}"
                obj.name = nuevo_nombre
                if obj.data:
                    obj.data.name = nuevo_nombre
                fijados += 1
    return fijados

# ---------------------------------------------------------
# OPERADOR PRINCIPAL: PUSH / PUBLISH
# ---------------------------------------------------------

class OPENSTUDIO_OT_publish_task(bpy.types.Operator):
    bl_idname = "openstudio.publish_task"
    bl_label = "Push / Publish"
    bl_description = "Purga el archivo, evalúa las reglas y recolecta errores antes de publicar"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        print("\n==================================================")
        print("[GATEKEEPER] Iniciando Secuencia de Publicación...")
        
        if aislar_coleccion_temp():
            print(" -> Colección '__TEMP__' excluida.")
        items_eliminados = purgar_huerfanos_recursivo()
        print(f" -> {items_eliminados} huérfanos purgados.")

        infractores_ext = escanear_out_of_bounds()
        infractores_geo = escanear_geometria_sucia()
        infractores_nom = escanear_nombres_sucios()
        
        hay_errores = bool(infractores_ext or infractores_geo or infractores_nom)
        
        if hay_errores:
            print("[GATEKEEPER ALERTA] Se detectaron errores. Invocando Modal Maestro QA...")
            context.scene.os_geo_infractores = ",".join(infractores_geo)
            context.scene.os_nom_infractores = ",".join(infractores_nom)
            
            try:
                bpy.ops.openstudio.master_qa_ui('INVOKE_DEFAULT')
            except AttributeError:
                self.report({'ERROR'}, "Errores detectados pero módulo UI Maestro no está cargado.")
            return {'CANCELLED'}

        print(" -> Todos los chequeos superados con éxito.")
        self.report({'INFO'}, "Gatekeeper superado. Preparando Push.")
        
        # FASE 3: THE SYNERGY HOOK (Kitsu)
        print("[GATEKEEPER] Fase 3: The Synergy Hook (Kitsu)...")
        hooks.disparar_playblast_kitsu()
        
        return {'FINISHED'}

def register():
    bpy.types.Scene.os_geo_infractores = bpy.props.StringProperty()
    bpy.types.Scene.os_nom_infractores = bpy.props.StringProperty()
    bpy.utils.register_class(OPENSTUDIO_OT_publish_task)

def unregister():
    del bpy.types.Scene.os_nom_infractores
    del bpy.types.Scene.os_geo_infractores
    bpy.utils.unregister_class(OPENSTUDIO_OT_publish_task)

if __name__ == "__main__":
    register()

```

--------------------------------------------------------------------------------

### Archivo: `addons/openstudio_toolkit/hooks.py`

```python
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
import os
from pathlib import Path

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

def inyectar_splash_corporativo(dummy=None):
    """Atrapa el inicio de Blender y sobrescribe el logo default con la portada del Hub."""
    splash_path = os.environ.get("OPENSTUDIO_SPLASH_PATH", "")
    
    if not splash_path or not os.path.exists(splash_path):
        return
        
    img_name = Path(splash_path).name
    if img_name not in bpy.data.images:
        bpy.data.images.load(splash_path)
        
    try:
        bpy.context.preferences.view.splash_image = img_name
    except Exception:
        

def register():
    # Este módulo expone funciones puras, no requiere registrar clases en bpy
    bpy.app.handlers.load_post.append(inyectar_splash_corporativo)
    pass

def unregister():
    if inyectar_splash_corporativo in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(inyectar_splash_corporativo)
    pass

```

--------------------------------------------------------------------------------

### Archivo: `addons/openstudio_toolkit/ui_modals.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: addons/openstudio_toolkit/ui_modals.py
# Rol Arquitectónico: DCC UI / Interceptores Modales
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.2
# =========================================================================================

"""
Módulo de interfaces modales interactivas para el Gatekeeper.
Provee el Master QA UI, una ventana emergente unificada que obliga al usuario a resolver
inconsistencias en la escena antes de continuar con la publicación.
"""

import bpy
from . import gatekeeper

# ---------------------------------------------------------
# ESTRUCTURAS DE DATOS TEMPORALES (UI)
# ---------------------------------------------------------

class OpenStudioInfractorItem(bpy.types.PropertyGroup):
    """Estructura para listar archivos Out-of-Bounds."""
    nombre: bpy.props.StringProperty()
    ruta_actual: bpy.props.StringProperty()
    categoria: bpy.props.EnumProperty(
        name="Destino",
        items=[
            ('textures', "Textura (Base, Normal)", ""),
            ('hdri', "Entorno HDRI", ""),
            ('caches', "Caché o Simulación", "")
        ],
        default='textures'
    )

class OpenStudioGeoItem(bpy.types.PropertyGroup):
    """Estructura para listar mallas con errores matemáticos."""
    nombre: bpy.props.StringProperty()
    accion: bpy.props.EnumProperty(
        name="Resolución",
        description="Elige cómo resolver las transformaciones sucias",
        items=[
            ('apply', "Aplicar (Ctrl+A)", "Congela la escala/rotación actual"),
            ('clear', "Limpiar (Alt+G/R/S)", "Devuelve el objeto a posición cero"),
            ('ignore', "Ignorar por ahora", "No altera la malla")
        ],
        default='apply'
    )

# ---------------------------------------------------------
# INTERFAZ UNIFICADA: MASTER QA
# ---------------------------------------------------------

class OPENSTUDIO_OT_master_qa_ui(bpy.types.Operator):
    """
    Despliega el Pop-up interactivo unificado del Gatekeeper.
    Muestra dependencias externas, geometría sucia y errores de nomenclatura en un solo panel.
    """
    bl_idname = "openstudio.master_qa_ui"
    bl_label = "Master QA: Resolución de Conflictos"
    bl_description = "Resuelve todos los problemas de la escena en un solo lugar"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        """Inicializa las listas leyendo los datos del Gatekeeper."""
        context.scene.os_infractores.clear()
        context.scene.os_geo_items.clear()
        
        # 1. Poblamos la lista de Dependencias
        infractores_ext = gatekeeper.escanear_out_of_bounds()
        for item in infractores_ext:
            new_item = context.scene.os_infractores.add()
            new_item.nombre = item["nombre"]
            new_item.ruta_actual = item["ruta_actual"]
            
        # 2. Poblamos la lista de Geometría
        geo_str = context.scene.os_geo_infractores
        if geo_str:
            nombres_geo = geo_str.split(",")
            for nom in nombres_geo:
                new_item = context.scene.os_geo_items.add()
                new_item.nombre = nom
                
        return context.window_manager.invoke_props_dialog(self, width=600)

    def draw(self, context):
        layout = self.layout
        
        # Panel 1: Out-of-Bounds
        if len(context.scene.os_infractores) > 0:
            box = layout.box()
            box.label(text="Dependencias Externas (Out-of-Bounds)", icon='URL')
            for item in context.scene.os_infractores:
                row = box.row()
                row.label(text=item.nombre, icon='FILE_IMAGE')
                row.prop(item, "categoria", text="")
                
            layout.separator()
            
        # Panel 2: Geometría
        if len(context.scene.os_geo_items) > 0:
            box = layout.box()
            box.label(text="Sanidad Matemática (Escalas/Rotaciones/Posición)", icon='MESH_DATA')
            for item in context.scene.os_geo_items:
                row = box.row()
                row.label(text=item.nombre, icon='OBJECT_DATA')
                row.prop(item, "accion", text="")
                
            layout.separator()
            
        # Panel 3: Nomenclatura
        nom_str = context.scene.os_nom_infractores
        if nom_str:
            box = layout.box()
            box.label(text="Nomenclatura (Se aplicará convención automáticamente)", icon='SORTALPHA')
            nombres_nom = nom_str.split(",")
            for nom in nombres_nom:
                box.label(text=f"• {nom}", icon='BLANK1')

    def execute(self, context):
        """Ejecuta las reparaciones delegando al Gatekeeper."""
        
        # 1. Reparar Dependencias
        clasificaciones = {item.nombre: item.categoria for item in context.scene.os_infractores}
        if clasificaciones:
            infractores_crudos = gatekeeper.escanear_out_of_bounds()
            gatekeeper.auto_fix_dependencias(infractores_crudos, clasificaciones)
            
        # 2. Reparar Geometría (Filtrado por acción elegida)
        apply_list = [item.nombre for item in context.scene.os_geo_items if item.accion == 'apply']
        clear_list = [item.nombre for item in context.scene.os_geo_items if item.accion == 'clear']
        
        gatekeeper.aplicar_transformaciones(apply_list)
        gatekeeper.limpiar_transformaciones(clear_list)
        
        # 3. Reparar Nomenclatura
        nom_str = context.scene.os_nom_infractores
        if nom_str:
            gatekeeper.auto_fix_nombres(nom_str.split(","))

        # Limpieza de memoria
        context.scene.os_infractores.clear()
        context.scene.os_geo_items.clear()
        context.scene.os_geo_infractores = ""
        context.scene.os_nom_infractores = ""
        
        self.report({'INFO'}, "Master QA: Todas las reparaciones ejecutadas. Vuelve a intentar el Push.")
        return {'FINISHED'}

# ---------------------------------------------------------
# REGISTRO
# ---------------------------------------------------------

def register():
    bpy.utils.register_class(OpenStudioInfractorItem)
    bpy.utils.register_class(OpenStudioGeoItem)
    
    bpy.types.Scene.os_infractores = bpy.props.CollectionProperty(type=OpenStudioInfractorItem)
    bpy.types.Scene.os_geo_items = bpy.props.CollectionProperty(type=OpenStudioGeoItem)
    
    bpy.utils.register_class(OPENSTUDIO_OT_master_qa_ui)

def unregister():
    bpy.utils.unregister_class(OPENSTUDIO_OT_master_qa_ui)
    
    del bpy.types.Scene.os_geo_items
    del bpy.types.Scene.os_infractores
    
    bpy.utils.unregister_class(OpenStudioGeoItem)
    bpy.utils.unregister_class(OpenStudioInfractorItem)

```

--------------------------------------------------------------------------------

### Archivo: `addons/openstudio_toolkit/utils_logger.py`

```python
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

```

--------------------------------------------------------------------------------

### Archivo: `core/__init__.py`

```python

```

--------------------------------------------------------------------------------

### Archivo: `core/addon_inspector.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/addon_inspector.py
# Rol Arquitectónico: Core Utility / Semantic Metadata Parser
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0
# =========================================================================================

import re
import zipfile
from pathlib import Path

class AddonInspector:
    """Utilidad estática para leer y extraer propiedades de Addons desde archivos ZIP o directorios crudos."""
    
    @staticmethod
    def parse_manifest_content(content: str, is_toml: bool) -> dict:
        """Aplica expresiones regulares sobre el texto crudo para aislar las propiedades semánticas."""
        resultado = {
            "name": "unknown_addon",
            "version": "1.0.0",
            "description": "Custom loaded addon",
            "blender_min": (0, 0, 0)
        }

        if is_toml:
            id_m = re.search(r'id\s*=\s*"([^"]+)"', content)
            ver_m = re.search(r'version\s*=\s*"([^"]+)"', content)
            desc_m = re.search(r'description\s*=\s*"([^"]+)"', content)
            min_v_m = re.search(r'blender_version_min\s*=\s*"([^"]+)"', content)

            if id_m: resultado["name"] = id_m.group(1)
            if ver_m: resultado["version"] = ver_m.group(1)
            if desc_m: resultado["description"] = desc_m.group(1)
            if min_v_m:
                resultado["blender_min"] = tuple(int(x) for x in min_v_m.group(1).split('.') if x.isdigit())
        else:
            # Parseo Legacy (bl_info)
            v_match = re.search(r'"version"\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d+))?\s*\)', content)
            b_match = re.search(r'"blender"\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d+))?\s*\)', content)
            desc_m = re.search(r'"description"\s*:\s*"([^"]+)"', content)

            # Para legacy, sacamos el nombre de un campo alternativo o se debe inferir por carpeta fuera de este método
            name_m = re.search(r'"name"\s*:\s*"([^"]+)"', content)
            if name_m: resultado["name"] = name_m.group(1).lower().replace(" ", "_")

            if v_match: resultado["version"] = f"{v_match.group(1)}.{v_match.group(2)}.{v_match.group(3) or '0'}"
            if desc_m: resultado["description"] = desc_m.group(1)
            if b_match:
                resultado["blender_min"] = (int(b_match.group(1)), int(b_match.group(2)), int(b_match.group(3) or 0))

        return resultado

    @staticmethod
    def inspect_zip(zip_path: Path) -> dict:
        """Abre un archivo ZIP en memoria y busca su manifiesto."""
        if not zipfile.is_zipfile(zip_path):
            return {}

        with zipfile.ZipFile(zip_path, 'r') as z:
            # 1. Buscar extensiones modernas
            for item in z.namelist():
                if item.endswith("blender_manifest.toml"):
                    content = z.read(item).decode('utf-8', errors='ignore')
                    return AddonInspector.parse_manifest_content(content, is_toml=True)
            
            # 2. Buscar legacy
            for item in z.namelist():
                if item.endswith("__init__.py"):
                    content = z.read(item).decode('utf-8', errors='ignore')
                    if "bl_info" in content:
                        parsed = AddonInspector.parse_manifest_content(content, is_toml=False)
                        # Inferir nombre base de la carpeta si el regex no lo capturó bien
                        if parsed["name"] == "unknown_addon":
                            parsed["name"] = Path(item).parent.name
                        return parsed
        return {}

    @staticmethod
    def inspect_directory(dir_path: Path) -> dict:
        """Analiza un directorio extraído en disco (Útil para el FetchWorker)."""
        toml_path = dir_path / "blender_manifest.toml"
        if toml_path.exists():
            return AddonInspector.parse_manifest_content(toml_path.read_text(encoding='utf-8', errors='ignore'), is_toml=True)
            
        init_path = dir_path / "__init__.py"
        if init_path.exists():
            content = init_path.read_text(encoding='utf-8', errors='ignore')
            if "bl_info" in content:
                parsed = AddonInspector.parse_manifest_content(content, is_toml=False)
                if parsed["name"] == "unknown_addon":
                    parsed["name"] = dir_path.name
                return parsed
        return {}

    @staticmethod
    def is_compatible(min_version_tuple: tuple, target_v_str: str) -> bool:
        """Contrasta la versión mínima exigida contra la versión objetivo de Blender."""
        try:
            t_parts = [int(x) for x in target_v_str.split('.') if x.isdigit()]
            while len(t_parts) < 3: t_parts.append(0)
            r_parts = list(min_version_tuple)
            while len(r_parts) < 3: r_parts.append(0)

            for t, r in zip(t_parts, r_parts):
                if t > r: return True
                if t < r: return False
            return True 
        except:
            return True

```

--------------------------------------------------------------------------------

### Archivo: `core/addon_parser.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/addon_parser.py
# Rol Arquitectónico: Add-on Metadata Extractor (Manifest & Legacy Scanner)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0
# =========================================================================================

"""
Scans and parses Blender add-on archives (.zip).
Extracts compatibility metadata by analyzing either the modern 'blender_manifest.toml' 
(Blender 4.2+ extensions) or the legacy 'bl_info' dictionary in '__init__.py'.
Performs safe parsing via Regex without executing external code.
"""

import zipfile
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

class AddonParser:
    @staticmethod
    def parse_zip(zip_path: Path) -> Dict[str, Any]:
        """
        Inspects a zip file in memory to extract Blender add-on metadata.
        Returns a dictionary with standard keys: 'is_valid', 'name', 'version', 'min_blender_version'.
        """
        default_response = {
            "is_valid": False,
            "name": "Unknown Add-on",
            "version": "0.0.0",
            "min_blender_version": "0.0.0",
            "type": "unknown"
        }

        if not zip_path.exists() or not zipfile.is_zipfile(zip_path):
            return default_response

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                file_list = zf.namelist()
                
                # 1. Search for modern Extension Manifest (Blender 4.2+)
                manifest_files = [f for f in file_list if f.endswith('blender_manifest.toml')]
                if manifest_files:
                    # Sort to get the shallowest file (root level preferred)
                    manifest_files.sort(key=lambda x: x.count('/'))
                    content = zf.read(manifest_files[0]).decode('utf-8', errors='ignore')
                    return AddonParser._parse_toml_manifest(content)

                # 2. Search for Legacy bl_info (Pre 4.2)
                init_files = [f for f in file_list if f.endswith('__init__.py')]
                if init_files:
                    # Sort to get the shallowest __init__.py
                    init_files.sort(key=lambda x: x.count('/'))
                    content = zf.read(init_files[0]).decode('utf-8', errors='ignore')
                    return AddonParser._parse_legacy_bl_info(content)

        except Exception as e:
            print(f"[ADDON PARSER] Error inspecting zip '{zip_path.name}': {e}")
            
        return default_response

    @staticmethod
    def _parse_toml_manifest(content: str) -> Dict[str, Any]:
        """Extracts metadata from a blender_manifest.toml using regex."""
        name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
        version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
        blender_min_match = re.search(r'blender_version_min\s*=\s*"([^"]+)"', content)

        name = name_match.group(1) if name_match else "Unknown Extension"
        version = version_match.group(1) if version_match else "1.0.0"
        min_blender = blender_min_match.group(1) if blender_min_match else "4.2.0"

        return {
            "is_valid": bool(name_match and version_match),
            "name": name,
            "version": version,
            "min_blender_version": min_blender,
            "type": "manifest"
        }

    @staticmethod
    def _parse_legacy_bl_info(content: str) -> Dict[str, Any]:
        """
        Safely extracts bl_info metadata from an __init__.py file using regex
        to prevent execution of untrusted code via eval() or ast.literal_eval().
        """
        # Find the bl_info block (rudimentary but effective for standardized files)
        bl_info_match = re.search(r'bl_info\s*=\s*\{([^}]+)\}', content, re.DOTALL)
        
        if not bl_info_match:
            return {
                "is_valid": False,
                "name": "Unknown Legacy Add-on",
                "version": "0.0.0",
                "min_blender_version": "0.0.0",
                "type": "legacy"
            }

        bl_info_text = bl_info_match.group(1)

        # Regex for values
        name_match = re.search(r'"name"\s*:\s*["\']([^"\']+)["\']', bl_info_text)
        
        # Versions in legacy are tuples: (3, 0, 0)
        version_match = re.search(r'"version"\s*:\s*\(\s*([0-9]+)\s*,\s*([0-9]+)\s*(?:,\s*([0-9]+)\s*)?\)', bl_info_text)
        blender_match = re.search(r'"blender"\s*:\s*\(\s*([0-9]+)\s*,\s*([0-9]+)\s*(?:,\s*([0-9]+)\s*)?\)', bl_info_text)

        name = name_match.group(1) if name_match else "Unknown Add-on"
        
        version = "1.0.0"
        if version_match:
            v_parts = [p for p in version_match.groups() if p is not None]
            version = ".".join(v_parts)

        min_blender = "2.80.0"
        if blender_match:
            b_parts = [p for p in blender_match.groups() if p is not None]
            min_blender = ".".join(b_parts)

        return {
            "is_valid": True,
            "name": name,
            "version": version,
            "min_blender_version": min_blender,
            "type": "legacy"
        }

    @staticmethod
    def is_compatible(addon_min_version: str, target_blender_version: str) -> bool:
        """
        Compares version strings (e.g., '4.2.0' vs '4.5') to determine compatibility.
        Returns True if the target Blender version is >= the add-on's minimum requirement.
        """
        try:
            def parse_version(v: str) -> Tuple[int, ...]:
                # Extract only numeric parts, ignore alphas like 'b', 'alpha'
                clean_v = re.sub(r'[^0-9.]', '', v)
                return tuple(int(x) for x in clean_v.split('.') if x.isdigit())

            addon_tuple = parse_version(addon_min_version)
            target_tuple = parse_version(target_blender_version)

            # Pad tuples to identical length for safe comparison
            max_len = max(len(addon_tuple), len(target_tuple))
            addon_tuple = addon_tuple + (0,) * (max_len - len(addon_tuple))
            target_tuple = target_tuple + (0,) * (max_len - len(target_tuple))

            return target_tuple >= addon_tuple
        except Exception:
            # Fallback for parsing errors: Leave it to TD judgment
            return True

```

--------------------------------------------------------------------------------

### Archivo: `core/auth_manager.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/auth_manager.py
# Rol Arquitectónico: Adapter / API Gateway (Gazu/Kitsu)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.7.0
# =========================================================================================

"""
Main adapter for the Kitsu API (via the Gazu library).
Manages authentication, role resolution (RBAC), and the extraction
of studio and user metadata. Anchored to English standard.
"""

import json
import gazu
from pathlib import Path
from typing import Tuple, Dict, List, Optional

OPENSTUDIO_CONFIG_DIR = Path.home() / ".openstudio"
SESSION_FILE = OPENSTUDIO_CONFIG_DIR / "session.json"

class AuthManager:
    def __init__(self):
        self.kitsu_host = None
        self.user_data = None
        
        if not OPENSTUDIO_CONFIG_DIR.exists():
            OPENSTUDIO_CONFIG_DIR.mkdir(parents=True)

    def set_host(self, host_url: str) -> None:
        if not host_url.endswith("/api"):
            host_url = f"{host_url.rstrip('/')}/api"
        self.kitsu_host = host_url
        gazu.client.set_host(self.kitsu_host)

    def login_with_credentials(self, email: str, password: str, host_url: str) -> Tuple[bool, str]:
        try:
            self.set_host(host_url)
            tokens = gazu.log_in(email, password)
            self.user_data = gazu.client.get_current_user()
            self._save_session(tokens)
            return True, "Login successful."
        except gazu.exception.AuthFailedException:
            return False, "Invalid credentials."
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def login_with_saved_session(self) -> bool:
        if not SESSION_FILE.exists():
            return False
        try:
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)
            self.set_host(data["host"])
            gazu.client.set_tokens(data["tokens"])
            self.user_data = gazu.client.get_current_user()
            return True
        except Exception:
            if SESSION_FILE.exists():
                SESSION_FILE.unlink()
            return False

    def logout(self) -> None:
        gazu.log_out()
        self.user_data = None
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()

    def get_user_role(self) -> str:
        if not self.user_data:
            return "guest"
        kitsu_role = self.user_data.get("role", "").lower()
        kitsu_position = self.user_data.get("position", "").lower()
        
        if kitsu_role == "admin": return "td"
        elif kitsu_role == "supervisor": return "supervisor"
        elif kitsu_role == "manager": return "manager"
        elif kitsu_role == "vendor": return "vendor"
        elif kitsu_role == "client": return "client"
        elif kitsu_role == "user":
            if kitsu_position == "lead": return "lead"
            return "artist"
        return "artist"

    def get_user_position(self) -> str:
        if not self.user_data: return ""
        return self.user_data.get("position", "").lower()

    def get_current_token(self) -> str:
        if hasattr(gazu.client, "tokens") and isinstance(gazu.client.tokens, dict):
            return gazu.client.tokens.get("access_token", "")
            
        if SESSION_FILE.exists():
            try:
                with open(SESSION_FILE, 'r') as f:
                    data = json.load(f)
                return data.get("tokens", {}).get("access_token", "")
            except Exception:
                pass
        return ""

    def _save_session(self, tokens) -> None:
        data = {"host": self.kitsu_host, "tokens": tokens}
        with open(SESSION_FILE, 'w') as f:
            json.dump(data, f)

    # =========================================================================
    # KITSU API ENDPOINTS (SSoT)
    # =========================================================================

    def sync_studio_identity(self) -> dict:
        """
        Dynamically downloads the main studio identity from Kitsu.
        Designed to be explicitly triggered by the TD via the Settings Panel.
        """
        identity = {}
        try:
            org = gazu.person.get_organisation()
            if isinstance(org, dict) and "name" in org:
                identity["name"] = org["name"]
        except Exception as e:
            print(f"[AuthManager] Info: Failed to fetch Organisation from server ({e})")
            
        return identity

    def obtener_proyectos_activos(self) -> Dict[str, str]:
        proyectos = {}
        try:
            for p in gazu.project.all_open_projects():
                proyectos[p["name"].lower()] = p["id"]
        except Exception as e:
            print(f"[AuthManager] Error fetching active projects: {e}")
        return proyectos

    def get_task_metadata(self, task_id: str) -> Optional[Dict[str, str]]:
        try:
            return gazu.task.get_task(task_id)
        except Exception:
            return None

    def get_assigned_tasks(self) -> List[dict]:
        try:
            return gazu.user.all_tasks_to_do()
        except Exception as e:
            print(f"[AuthManager] Error fetching assigned tasks: {e}")
            return []

    def get_recent_activity(self, limit: int=15) -> List[dict]:
        return []

    def acknowledge_activity(self, task_id: str, comment_id: str) -> bool:
        return True

```

--------------------------------------------------------------------------------

### Archivo: `core/config_factory.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/config_factory.py
# Rol Arquitectónico: Configuration Manager & Crypto Engine (Bidirectional CRUD)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.9.0 (Encapsulation & Default Fallbacks)
# =========================================================================================

"""
Bidirectional parser and persistent CRUD engine for the settings.json file.
Manages atomic injection of NAS paths, API endpoints, and Semantic Topography.
Implements the B2B Provisioning Engine (Seed Generator/Importer) via zlib and base64.
Strictly encapsulates Fallback logic (Defaults) to keep UI components decoupled.
"""

import json
import platform
import base64
import zlib
from pathlib import Path

class ConfigFactory:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config = {}
        self._volatile_identity = {}  # Volatile RAM cache for Kitsu identity
        self._load_config()

    def _load_config(self):
        """Reads and parses the master B2B file if it exists."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"[CONFIG FACTORY ERROR] Corrupted or unreadable file: {e}")
                self._config = {}
        else:
            self._config = {}

    def get_raw_config(self) -> dict:
        """Returns the full dictionary for unmapped queries."""
        return self._config

    # ---------------------------------------------------------
    # PROVISIONING ENGINE (STUDIO SEED)
    # ---------------------------------------------------------

    def exportar_semilla(self, payload: dict, destino_dir: Path) -> tuple[bool, str]:
        """
        Packages, compresses, and obfuscates global configuration into a .seed file.
        Dynamically generates filename based on studio identity.
        """
        try:
            # 1. Dynamic Naming and Sanitization
            studio_name = payload.get("studio_profile", {}).get("name", "").strip()
            if not studio_name:
                studio_name = "openstudio"
            
            safe_name = "".join(c if c.isalnum() else "_" for c in studio_name).lower()
            
            import re
            safe_name = re.sub(r'_+', '_', safe_name).strip('_')
            
            seed_filename = f"{safe_name}.seed"
            seed_path = destino_dir / seed_filename

            # 2. Serialize and Obfuscate (JSON -> ZLIB -> BASE64)
            json_str = json.dumps(payload)
            compressed_bytes = zlib.compress(json_str.encode('utf-8'))
            encoded_str = base64.b64encode(compressed_bytes).decode('utf-8')

            # 3. Isolated Atomic Write
            with open(seed_path, 'w', encoding='utf-8') as f:
                f.write(encoded_str)

            return True, str(seed_path)
            
        except Exception as e:
            error_msg = f"Failed to export seed: {e}"
            print(f"[SEED ENGINE ERROR] {error_msg}")
            return False, error_msg

    def importar_semilla(self, seed_path: Path) -> bool:
        """
        Reads, decodes, and decompresses a .seed file, injecting it into local environment.
        This is the dispatcher called by the Login view on Day 0.
        """
        try:
            if not seed_path.exists():
                return False
            
            with open(seed_path, 'r', encoding='utf-8') as f:
                encoded_str = f.read()

            # Reverse Flow: BASE64 -> ZLIB -> JSON
            compressed_bytes = base64.b64decode(encoded_str)
            json_str = zlib.decompress(compressed_bytes).decode('utf-8')
            payload = json.loads(json_str)

            # Persist automatically using native CRUD
            return self.guardar_configuracion(payload, from_seed=True)
            
        except Exception as e:
            print(f"[SEED ENGINE ERROR] Integrity failure during seed import: {e}")
            return False

    def purgar_configuracion_local(self) -> bool:
        """Destroys local settings.json returning the Hub to Day 0 state."""
        try:
            if self.config_path.exists():
                self.config_path.unlink()
            self._config = {}
            return True
        except Exception as e:
            print(f"[CONFIG FACTORY ERROR] Failed to purge configuration: {e}")
            return False

    # ---------------------------------------------------------
    # ATOMIC PERSISTENCE (CRUD ENGINE)
    # ---------------------------------------------------------

    def guardar_configuracion(self, datos_dict: dict, from_seed: bool = False) -> bool:
        """
        Public API: Receives a structured payload, injects semantic validations,
        and atomically writes data to disk.
        """
        if not datos_dict:
            return False

        try:
            # 1. Extraction and Normalization
            kitsu_url = datos_dict.get("kitsu_production", {}).get("api_url", "").strip()
            
            vcs_data = datos_dict.get("vcs_engine", {})
            vcs_sys = vcs_data.get("active_adapter", "svn").strip()
            vendor_sparse = bool(vcs_data.get("enable_vendor_sparse_checkout", True))
            repo_url = vcs_data.get("repository_url", "").strip()
            
            topo_data = datos_dict.get("project_topography", {})
            infra_data = datos_dict.get("infrastructure_topology", {})
            
            # 2. B2B Schema Scaffolding
            if "studio_profile" not in self._config: self._config["studio_profile"] = {}
            if "vcs_engine" not in self._config: self._config["vcs_engine"] = {}
            if "kitsu_production" not in self._config: self._config["kitsu_production"] = {}
            if "macuare_services" not in self._config: self._config["macuare_services"] = {}
            if "project_topography" not in self._config: self._config["project_topography"] = {}
            if "infrastructure_topology" not in self._config: self._config["infrastructure_topology"] = {}

            # 3. Semantic Validations & Injection
            if "local_workspace_root" not in self._config["vcs_engine"]:
                self._config["vcs_engine"]["local_workspace_root"] = {}
            
            # Multi-OS Mapping
            if "local_workspace_root" in vcs_data:
                self._config["vcs_engine"]["local_workspace_root"] = vcs_data["local_workspace_root"]

            if kitsu_url:
                self._config["kitsu_production"]["api_url"] = kitsu_url
                
            studio_name = datos_dict.get("studio_profile", {}).get("name", "").strip()
            if studio_name:
                self._config["studio_profile"]["name"] = studio_name

            # Topography Mapping
            if topo_data:
                self._config["project_topography"]["vfs_svn"] = topo_data.get("vfs_svn", "svn")
                self._config["project_topography"]["vfs_shared"] = topo_data.get("vfs_shared", "shared")
                self._config["project_topography"]["vfs_local"] = topo_data.get("vfs_local", "local")
                self._config["project_topography"]["vfs_pipeline"] = topo_data.get("vfs_pipeline", "pipeline")
                self._config["project_topography"]["custom_dirs"] = topo_data.get("custom_dirs", [])
                
            # Infrastructure & Vault Mapping
            if infra_data:
                self._config["infrastructure_topology"]["vault_path"] = infra_data.get("vault_path", "")

            # Parametric Adapter Selection
            vcs_clean = vcs_sys.lower()
            if "svn" in vcs_clean and "git" in vcs_clean:
                self._config["vcs_engine"]["active_adapter"] = "git-svn"
            elif "git" in vcs_clean:
                self._config["vcs_engine"]["active_adapter"] = "git-lfs"
            else:
                self._config["vcs_engine"]["active_adapter"] = "svn"

            self._config["vcs_engine"]["enable_vendor_sparse_checkout"] = vendor_sparse
            self._config["vcs_engine"]["repository_url"] = repo_url

            # 4. Atomic Disk Write
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)

            self._load_config()
            return True

        except Exception as e:
            print(f"[CONFIG FACTORY ERROR] Critical error during atomic write: {e}")
            return False

    # ---------------------------------------------------------
    # VOLATILE IDENTITY (SSO & B2B Branding)
    # ---------------------------------------------------------

    def set_volatile_studio_identity(self, identity_data: dict):
        self._volatile_identity = identity_data

    def get_studio_name(self) -> str:
        name = self._volatile_identity.get("name") or self._volatile_identity.get("studio_name")
        if name: return name
        return self._config.get("studio_profile", {}).get("name", "OPENSTUDIO HUB")

    def get_user_avatar_path(self) -> str | None:
        return self._volatile_identity.get("avatar_path")

    # ---------------------------------------------------------
    # SYSTEM ROUTING & TOPOGRAPHY GETTERS
    # ---------------------------------------------------------

    def _get_current_os(self) -> str:
        system = platform.system().lower()
        if system == "windows": return "windows"
        elif system == "darwin": return "darwin"
        else: return "linux"

    def get_workspace_root(self) -> Path:
        """Returns the base projects directory. Implements Day-0 Fallbacks."""
        os_key = self._get_current_os()
        vcs_config = self._config.get("vcs_engine", {})
        roots = vcs_config.get("local_workspace_root", {})
        
        root_str = roots.get(os_key)
        if not root_str:
            # Fallback seguro en lugar de romper la app con ValueError
            return Path.home() / "openstudio_projects"
            
        return Path(root_str)
        
    def get_vault_path(self) -> Path:
        """
        Returns the absolute path to the Vault.
        Calculates dynamic fallback based on workspace_root if unconfigured.
        """
        vault_str = self._config.get("infrastructure_topology", {}).get("vault_path", "")
        if vault_str:
            return Path(vault_str)
            
        # Fallback dinámico
        return self.get_workspace_root() / "openstudio_vault"

    def get_vcs_adapter_type(self) -> str:
        return self._config.get("vcs_engine", {}).get("active_adapter", "svn")

    def get_vcs_repository_url(self) -> str:
        return self._config.get("vcs_engine", {}).get("repository_url", "")

    def is_vendor_sparse_enabled(self) -> bool:
        return self._config.get("vcs_engine", {}).get("enable_vendor_sparse_checkout", True)

    def get_kitsu_api_url(self) -> str:
        return self._config.get("kitsu_production", {}).get("api_url", "")

    # --- TOPOGRAPHY ENGINE ---

    def get_vfs_svn_name(self) -> str:
        return self._config.get("project_topography", {}).get("vfs_svn", "svn")

    def get_vfs_shared_name(self) -> str:
        return self._config.get("project_topography", {}).get("vfs_shared", "shared")

    def get_vfs_local_name(self) -> str:
        return self._config.get("project_topography", {}).get("vfs_local", "local")

    def get_vfs_pipeline_name(self) -> str:
        return self._config.get("project_topography", {}).get("vfs_pipeline", "pipeline")

    def get_custom_dirs(self) -> list:
        return self._config.get("project_topography", {}).get("custom_dirs", [])

    def get_production_folder_name(self) -> str:
        """DEPRECATED ALIAS: Routes to get_vfs_svn_name() to prevent breaking legacy components."""
        return self.get_vfs_svn_name()

```

--------------------------------------------------------------------------------

### Archivo: `core/env_launcher.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/env_launcher.py
# Rol Arquitectónico: Subprocess Orchestrator / Sandboxing
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.1.0 (Dynamic VFS & PathResolver Integration)
# =========================================================================================

"""
Orquestador de subprocesos para el ecosistema OpenStudio.
Se encarga de ubicar el binario de Blender de forma dinámica mediante el ConfigFactory, 
construir el entorno aislado (Sandboxing VFS), e inyectar las variables de entorno 
para el Context-Aware Tooling y la navegación RNA.
"""

import os
import json
import subprocess
import shutil
import platform
from pathlib import Path
from typing import Optional

from core.path_resolver import PathResolver

def _get_os_info() -> str:
    system = platform.system().lower()
    if system == "linux": return "linux"
    elif system == "windows": return "windows"
    else: return "macos"

def lanzar_blender(project_root: Path, config_path: Path, svn_user: str, svn_pwd: str, 
                   kitsu_user: str, kitsu_pwd: str, kitsu_host: str, user_role: str, 
                   task_data: dict, target_file: Optional[Path], status_callback,
                   production_folder: str = "", config_factory = None):
    try:
        if not config_factory:
            raise RuntimeError("ConfigFactory no fue inyectado en el EnvLauncher.")

        # Extracción de Topología Dinámica B2B
        vfs_local = config_factory.get_vfs_local_name()
        vfs_svn = config_factory.get_vfs_svn_name()
        vault_path = config_factory.get_vault_path()

        if not production_folder:
            production_folder = vfs_svn

        with open(config_path, 'r', encoding='utf-8') as f:
            adn = json.load(f)

        template_name = adn.get("template", "Macuare_Estudio")
        version = adn.get("version_locking", {}).get("blender_version", adn.get("blender_version", "5.1.2"))

        #status_callback(f"Buscando Blender {version}...", "yellow")

        status_callback(f"Buscando Blender {version} en Sandbox Local...", "yellow")

        # 1. Búsqueda Estricta de Binario (Exclusivo en Sandbox VFS)
        os_name = _get_os_info()
        archive_folder = f"blender-{version}-{os_name}-x64"
        
        base_blender_dir = project_root / vfs_local / "blender-build" / archive_folder
        
        if os_name == "windows":
            blender_bin = base_blender_dir / "blender.exe"
        elif os_name == "macos":
            # En macOS, el ejecutable real vive dentro del paquete .app
            blender_bin = base_blender_dir / "Blender.app" / "Contents" / "MacOS" / "Blender"
            if not blender_bin.exists():
                blender_bin = base_blender_dir / "Blender" # Fallback de seguridad
        else:
            blender_bin = base_blender_dir / "blender"

        if not blender_bin.exists():
            raise FileNotFoundError(f"Fallo de Sandboxing: No se encontró el ejecutable en {blender_bin}")

        status_callback(f"Ejecutable aislado encontrado en: {archive_folder}", "green")
        status_callback("Preparando Sandboxing y Variables de Entorno...", "yellow")

        # 2. Configurar Sandbox Dirs (Aislamiento absoluto VFS)
        sandbox_dir = project_root / vfs_local / "blender_data"
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        
        extensions_dir = sandbox_dir / "extensions" / "user_default"
        extensions_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["OPENSTUDIO_PROJECT_CONFIG"] = str(config_path)

        task_type = task_data.get("task_type_name", "generic")
        project_name = task_data.get("project_name", project_root.name)

        # Inyección VFS & Sandboxing Env Vars
        env["BLENDER_USER_RESOURCES"] = str(sandbox_dir)
        env["BLENDER_USER_CONFIG"] = str(sandbox_dir / "config")
        env["BLENDER_USER_SCRIPTS"] = str(sandbox_dir / "scripts")
        env["OPENSTUDIO_EXTENSIONS_DIR"] = str(extensions_dir) 

        env["OPENSTUDIO_PROJECT_ROOT"] = str(project_root)
        env["OPENSTUDIO_PRODUCTION_FOLDER"] = production_folder
        env["OPENSTUDIO_USER_ROLE"] = user_role
        env["OPENSTUDIO_TASK_TYPE"] = task_type
        
        # Inyección de Credenciales 
        env["OPENSTUDIO_KITSU_USER"] = kitsu_user
        env["OPENSTUDIO_KITSU_PWD"] = kitsu_pwd
        env["OPENSTUDIO_KITSU_HOST"] = kitsu_host

        # NUEVO: Calcular ruta del Splash Screen usando el ConfigFactory
        vfs_pipe = config_factory.get_vfs_pipeline_name()
        splash_path = project_root / vfs_pipe / "splash.png"
        env["OPENSTUDIO_SPLASH_PATH"] = str(splash_path) if splash_path.exists() else ""


        # ---------------------------------------------------------
        # PATH RESOLVER: INYECCIÓN DINÁMICA DE CONTEXTO
        # ---------------------------------------------------------
        if not target_file:
            resolver = PathResolver()
            resolved_rel_path = resolver.resolve(task_data)
            if resolved_rel_path:
                import glob
                # Quitamos el ".blend" para buscar variaciones con -v001, -v002, etc.
                base_target_str = str(project_root / production_folder / resolved_rel_path).replace(".blend", "")
                
                versioned_files = glob.glob(f"{base_target_str}-v*.blend")
                if versioned_files:
                    # Ordenamos y tomamos el archivo con la versión más reciente
                    target_file = Path(sorted(versioned_files)[-1])
                else:
                    # Fallback estándar
                    target_file = Path(f"{base_target_str}.blend")

        env["OPENSTUDIO_TARGET_FILE"] = str(target_file) if target_file else ""
        
        env["OPENSTUDIO_KITSU_PROJECT_ID"] = task_data.get("project_id", "")
        env["OPENSTUDIO_PROJECT_NAME"] = project_name
        env["OPENSTUDIO_KITSU_ENTITY_TYPE"] = task_data.get("entity_type", "SHOT").upper()
        env["OPENSTUDIO_KITSU_TASK_TYPE_ID"] = task_data.get("task_type_id", "")
        env["OPENSTUDIO_KITSU_TASK_TYPE_NAME"] = task_type
        env["OPENSTUDIO_KITSU_ENTITY_ID"] = task_data.get("entity_id", "")
        env["OPENSTUDIO_KITSU_ENTITY_NAME"] = task_data.get("entity_name", "")
        env["OPENSTUDIO_KITSU_SEQUENCE_ID"] = task_data.get("sequence_id", "")
        env["OPENSTUDIO_KITSU_SEQUENCE_NAME"] = task_data.get("sequence_name", "")
        # env["OPENSTUDIO_KITSU_ASSET_TYPE_ID"] = task_data.get("asset_type_id", "")
        # env["OPENSTUDIO_KITSU_ASSET_TYPE_NAME"] = task_data.get("asset_type_name", "")

        # Kitsu usa 'entity_type_id' para referirse al tipo de Asset dentro de un diccionario de Asset crudo
        env["OPENSTUDIO_KITSU_ASSET_TYPE_ID"] = task_data.get("asset_type_id", task_data.get("entity_type_id", ""))
        env["OPENSTUDIO_KITSU_ASSET_TYPE_NAME"] = task_data.get("asset_type_name", "")

        env["OPENSTUDIO_SVN_USER"] = svn_user
        env["OPENSTUDIO_SVN_PASSWORD"] = svn_pwd

        #breakpoint()
        # 3. Preparar el script bootstrap
        bootstrap_src = Path(__file__).parent / "templates" / "bootstrap.py"
        bootstrap_dst = project_root / vfs_local / "bootstrap.py"

        bootstrap_dst.parent.mkdir(parents=True, exist_ok=True)
        if bootstrap_src.exists():
            shutil.copy2(bootstrap_src, bootstrap_dst)
        else:
            raise FileNotFoundError("No se encontro core/templates/bootstrap.py")

        status_callback(f"Arrancando {project_name} (Contexto: {task_type.upper()})...", "green")

        # =========================================================
        # SANEAMIENTO DE ENTORNO: Evitar TypeError por Kitsu 'null'
        # =========================================================
        clean_env = {}
        for k, v in env.items():
            clean_env[k] = str(v) if v is not None else ""
        # =========================================================

        # 4. Lanzar el subproceso con Sandboxing Inyectado
        cmd = [str(blender_bin), "--app-template", template_name, "--python", str(bootstrap_dst)]
        # --- DEBUG VOLCADO DE ENTORNO ---
        print("\n" + "="*40)
        print("🔍 AUDITORÍA DE ENV_LAUNCHER ANTES DEL POPEN")
        print("="*40)
        for key in ["OPENSTUDIO_KITSU_ASSET_TYPE_ID", "OPENSTUDIO_KITSU_ASSET_TYPE_NAME", "OPENSTUDIO_KITSU_ENTITY_NAME"]:
            print(f"[{key}]: '{clean_env.get(key, 'NO EXISTE')}'")
        print("="*40 + "\n")
        # --------------------------------
        proceso = subprocess.Popen(cmd, env=clean_env)

        status_callback(f"Blender en ejecucion ({project_name})...", "#00aaff")
        proceso.wait()
        status_callback(f"Sesion de {project_name} terminada.", "green")
        
    except Exception as e:
        status_callback(f"Error Crítico Launcher: {str(e)}", "red")
        import traceback
        print(f"Error detallado Launcher:\n{traceback.format_exc()}")

```

--------------------------------------------------------------------------------

### Archivo: `core/file_downloader.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/file_downloader.py
# Rol Arquitectónico: Utility / Asynchronous Network Engine
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0
# =========================================================================================

"""
Motor de transferencia asíncrono para descargas masivas (Chunked Streaming).
Desacoplado del hilo principal de la GUI (QThread). Escribe de forma atómica
en el disco destino e implementa limpieza de residuos (Rollback) ante caídas de red.
"""

import requests
from pathlib import Path
from PySide6.QtCore import QThread, Signal

class FileDownloaderWorker(QThread):
    """
    Worker Thread para descargas HTTP.
    Emite el progreso porcentual y garantiza la integridad estructural del archivo.
    """
    progress_updated = Signal(int)
    status_update = Signal(str, str)
    download_completed = Signal(Path)
    error_occurred = Signal(str)

    def __init__(self, url: str, dest_path: Path, chunk_size: int = 8192):
        super().__init__()
        self.url = url
        self.dest_path = dest_path
        self.chunk_size = chunk_size

    def run(self):
        try:
            self.status_update.emit(f"Iniciando descarga: {self.dest_path.name}...", "yellow")
            
            # Garantizar la existencia estructural del árbol de directorios destino
            self.dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Iniciar conexión de flujo continuo (Evita desbordamiento de RAM)
            with requests.get(self.url, stream=True, timeout=15) as response:
                response.raise_for_status()
                
                total_length = response.headers.get('content-length')
                
                if total_length is None:
                    # El servidor no reporta tamaño (Descarga ciega)
                    with open(self.dest_path, 'wb') as f:
                        f.write(response.content)
                    self.progress_updated.emit(100)
                else:
                    # Descarga fraccionada con cálculo aritmético de progreso
                    dl_bytes = 0
                    total_length = int(total_length)
                    
                    with open(self.dest_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=self.chunk_size):
                            if chunk:
                                dl_bytes += len(chunk)
                                f.write(chunk)
                                done_percent = int(100 * dl_bytes / total_length)
                                self.progress_updated.emit(done_percent)
                                
            self.status_update.emit(f"Descarga completada y verificada: {self.dest_path.name}", "green")
            self.download_completed.emit(self.dest_path)
            
        except requests.exceptions.RequestException as e:
            self._rollback_cleanup()
            self.error_occurred.emit(f"Fallo de integridad de red: {e}")
            
        except Exception as e:
            self._rollback_cleanup()
            self.error_occurred.emit(f"Fallo de E/S local: {e}")

    def _rollback_cleanup(self):
        """Purga el archivo parcialmente descargado para evitar empaquetados corruptos en la bóveda."""
        try:
            if self.dest_path.exists():
                self.dest_path.unlink()
        except Exception:
            pass

```

--------------------------------------------------------------------------------

### Archivo: `core/git_packager.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/git_packager.py
# Rol Arquitectónico: Backend Worker / Git LFS Provisioning
# =========================================================================================

import os
import shutil
import zipfile
import tempfile
import subprocess
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from core.manifest_manager import ManifestManager
from core.addon_parser import AddonParser

class StudioToolsPackagerWorker(QThread):
    """Clones the repo (resolving Git LFS), repacks internal addons individually, and registers valid ones."""
    progress_updated = Signal(int)
    status_update = Signal(str, str)
    finished_packing = Signal()
    error_occurred = Signal(str)

    def __init__(self, manifest_manager: ManifestManager, current_version: str):
        super().__init__()
        self.manifest_manager = manifest_manager
        self.current_version = current_version

    def _verificar_dependencias_sistema(self):
        """Valida que Git y Git LFS estén instalados en la máquina del TD."""
        if not shutil.which("git"):
            raise RuntimeError("Git no está instalado o no está en el PATH del sistema. Instala Git para continuar.")
        
        # Verificar soporte LFS
        resultado = subprocess.run(["git", "lfs", "version"], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("Git LFS no está instalado. Ejecuta 'git lfs install' en tu terminal antes de continuar.")

    def run(self):
        try:
            # 1. Pre-Flight Check
            self.status_update.emit("Verificando dependencias del sistema (Git LFS)...", "yellow")
            self._verificar_dependencias_sistema()

            self.status_update.emit("Clonando repositorio Studio Tools (Resolviendo LFS)...", "yellow")
            temp_dir = Path(tempfile.mkdtemp())
            repo_dir = temp_dir / "blender-studio-tools"
            
            # 2. Clonación directa por Git para forzar la descarga de los binarios LFS
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "https://projects.blender.org/studio/blender-studio-tools.git", str(repo_dir)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"Fallo crítico durante git clone: {result.stderr}")

            self.status_update.emit("Empaquetando add-ons internos...", "yellow")
            
            # 3. Identificar las carpetas de add-ons en el repositorio clonado
            addons_src_dir = repo_dir / "scripts-blender" / "addons"
            if not addons_src_dir.exists():
                raise ValueError("El directorio de add-ons no se encontró en el repositorio clonado.")

            addon_dirs = [d for d in addons_src_dir.iterdir() if d.is_dir()]
            total = len(addon_dirs)
            registered_count = 0
            
            # 4. Empaquetar y validar dinámicamente
            for i, addon_dir in enumerate(addon_dirs):
                addon_name = addon_dir.name
                self.status_update.emit(f"Empaquetando herramienta interna: {addon_name}...", "yellow")
                
                addon_zip_path = temp_dir / f"{addon_name}.zip"
                
                # Escribimos un nuevo ZIP limpio desde el sistema de archivos
                with zipfile.ZipFile(addon_zip_path, 'w', zipfile.ZIP_DEFLATED) as out_zf:
                    for root, _, files in os.walk(addon_dir):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(addons_src_dir)
                            out_zf.write(file_path, arcname)
                
                # Validación vía AddonParser
                parsed = AddonParser.parse_zip(addon_zip_path)
                if parsed["is_valid"]:
                    if AddonParser.is_compatible(parsed["min_blender_version"], self.current_version):
                        exito, msg = self.manifest_manager.register_addon(
                            blender_version=self.current_version,
                            addon_name=parsed["name"],
                            addon_version=parsed["version"],
                            source_zip=addon_zip_path
                        )
                        if exito:
                            registered_count += 1
                
                self.progress_updated.emit(int(((i + 1) / total) * 100))
            
            # 5. Atomic Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            self.status_update.emit(f"✓ Studio Tools Auto-Fetch completado. {registered_count} add-ons registrados.", "green")
            self.finished_packing.emit()
            
        except Exception as e:
            import traceback
            print(f"[StudioToolsPackager] ERROR: {traceback.format_exc()}")
            self.error_occurred.emit(str(e))
            # Fallback cleanup en caso de error
            if 'temp_dir' in locals() and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

```

--------------------------------------------------------------------------------

### Archivo: `core/kitsu_manager.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/kitsu_manager.py
# Rol Arquitectónico: API Wrapper / Integración Gazu
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.5.0 (Database Seeder)
# =========================================================================================

"""
Capa de abstracción y seguridad para las transacciones con la API de Kitsu (Gazu).
Encapsula la creación, consulta, borrado y validación de entidades para evitar
que la lógica de red contamine el orquestador de archivos locales y los componentes de UI.
Incluye rutinas de aprovisionamiento de datos (Seeding) para entornos locales.
"""

import gazu
import requests
from pathlib import Path
from typing import Optional, Tuple

class KitsuManager:
    def __init__(self):
        """
        El AuthManager asume la responsabilidad de establecer el host 
        y los tokens globales de Gazu en RAM antes de instanciar esto.
        """
        pass

    def check_project_exists(self, project_name: str) -> bool:
        """
        Consulta a Kitsu si ya existe un proyecto con ese nombre exacto.
        Útil para prevenir conflictos antes de inicializar la topografía física.
        """
        try:
            proyecto = gazu.project.get_project_by_name(project_name)
            return proyecto is not None
        except Exception:
            # Gazu lanza una excepción si no encuentra el proyecto, o si hay un fallo de red.
            # Asumimos False (no existe) para permitir que el flujo superior decida.
            return False

    def create_project(self, project_name: str) -> Tuple[bool, str, dict]:
        """
        Construye la entidad raíz del Proyecto en la base de datos de Kitsu.
        Valida pre-existencias y captura el ID resultante para enlazado (Binding).
        """
        try:
            # 1. Validación de colisión
            if self.check_project_exists(project_name):
                return False, f"El proyecto '{project_name}' ya existe en la base de datos de Kitsu.", {}

            # 2. Generación en Base de Datos
            nuevo_proyecto = gazu.project.new_project(project_name)
            
            if not nuevo_proyecto:
                return False, "Kitsu rechazó la creación del proyecto (respuesta vacía).", {}

            return True, "Proyecto creado exitosamente en Kitsu.", nuevo_proyecto

        except Exception as e:
            return False, f"Error crítico al comunicarse con Kitsu: {str(e)}", {}

    def create_initial_edit(self, project_id: str, edit_name: str = "Main Edit") -> Tuple[bool, str, dict]:
        """
        Crea un Edit (entidad de montaje) inicial en el proyecto.
        Fundamental para que el departamento de Editorial tenga un contenedor en la base de datos.
        """
        if not project_id:
            return False, "ID de proyecto inválido.", {}

        try:
            # 1. Verificar si ya existe para evitar duplicados
            existing_edit = gazu.edit.get_edit_by_name(project_id, edit_name)
            if existing_edit:
                return True, f"El Edit '{edit_name}' ya existe en Kitsu.", existing_edit

            # 2. Crear la nueva entidad Edit
            nuevo_edit = gazu.edit.new_edit(project_id, name=edit_name)
            return True, f"Edit '{edit_name}' creado exitosamente.", nuevo_edit

        except Exception as e:
            trace = traceback.format_exc()
            print(f"[KitsuManager] DEBUG CRÍTICO (create_initial_edit):\n{trace}")
            return False, f"Fallo al crear el Edit inicial: {str(e)}", {}

    def upload_project_splash(self, project_id: str, image_path: str) -> bool:
        """
        Inyecta el Splash Screen (Thumbnail) oficial del proyecto.
        Captura silenciosamente los errores porque esto no debe bloquear la creación.
        """
        if not image_path:
            return False
            
        img_path = Path(image_path)
        if not img_path.exists() or not img_path.is_file():
            return False

        try:
            project = gazu.project.get_project(project_id)
            if project:
                endpoint = f"/pictures/thumbnails/projects/{project_id}"
                gazu.client.upload(endpoint, str(img_path))
                return True
        except Exception as e:
            print(f"[KitsuManager] Advertencia: Fallo al subir el Splash Screen a Kitsu: {e}")
            
        return False

    def delete_project(self, project_id: str) -> Tuple[bool, str]:
        """
        Ejecuta la eliminación permanente del proyecto en la base de datos.
        Utiliza el método nativo remove_project con force=True para saltar 
        la restricción de estado 'Closed', garantizando una limpieza limpia.
        """
        if not project_id:
            return False, "ID de proyecto inválido o nulo."

        try:
            # Reemplazo de Two-Step Destruction por Force Remove nativo de Gazu.

            try:
                gazu.project.close_project(project_id)
                print(f"[KitsuManager] Proyecto '{project_id}' cambiado a estado 'Closed'.")
            except Exception as close_err:
                print(f"[KitsuManager] Advertencia al intentar cerrar el proyecto: {close_err}")

            gazu.project.remove_project(project_id, force=True)
            return True, "Proyecto destruido exitosamente en Kitsu."
            
        except Exception as e:
            error_msg = str(e)
            print(f"[KitsuManager] Error crítico al borrar el proyecto '{project_id}': {error_msg}")
            return False, f"Fallo al eliminar en Kitsu: {error_msg}"

    def build_web_url(self, host_url: str, project_id: str, sub_path: str) -> str:
        """
        Construye una URL segura para enrutar al usuario a la interfaz web de Kitsu.
        Sanea automáticamente la URL base removiendo '/api' si está presente.
        Ejemplo sub_path: '/shots', '/team', '/production-settings'
        """
        if not host_url or not project_id:
            return ""
            
        clean_host = host_url[:-4] if host_url.endswith('/api') else host_url
        
        if sub_path and not sub_path.startswith('/'):
            sub_path = '/' + sub_path
            
        return f"{clean_host}/productions/{project_id}{sub_path}"

    def download_project_thumbnail(self, project_id: str, token: str, host_url: str) -> Optional[bytes]:
        """
        Descarga asíncronamente la miniatura del proyecto usando la API HTTP cruda.
        Retorna los bytes de la imagen listos para el QImage o None si falla.
        """
        if not project_id or not token or not host_url:
            return None

        try:
            img_url = f"{host_url}/pictures/thumbnails/projects/{project_id}.png"
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.get(img_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.content
        except Exception as e:
            print(f"[KitsuManager] Fallo de red al descargar miniatura del proyecto '{project_id}': {e}")
            
        return None

    def seed_test_database(self, admin_email: str = "admin@example.com", admin_pwd: str = "mysecretpassword") -> Tuple[bool, str]:
        """
        Se conecta temporalmente como administrador global para inyectar 
        los usuarios dummy necesarios para las pruebas locales del Hub.
        """
        try:
            # 1. Autenticación efímera de administración
            gazu.log_in(admin_email, admin_pwd)
            print("[KitsuManager] Autenticado como Admin. Iniciando sembrado de cuentas de prueba...")

            # 2. Definición de la matriz de usuarios dummy requerida
            dummy_users = [
                {"first": "Production", "last": "Manager", "email": "pm@estudiomacuare.com", "role": "manager"},
                {"first": "Vendor", "last": "Artist", "email": "vendor@estudiomacuare.com", "role": "vendor"},
                {"first": "3D", "last": "Artist", "email": "artist@estudiomacuare.com", "role": "user"}
            ]

            creados = 0
            for user in dummy_users:
                # Verificar si el usuario ya fue inyectado previamente para evitar duplicados
                existing = gazu.person.get_person_by_email(user["email"])
                if not existing:
                    gazu.person.new_person(
                        first_name=user["first"],
                        last_name=user["last"],
                        email=user["email"],
                        role=user["role"],
                        password="entrar123"
                    )
                    print(f"[KitsuManager] -> Usuario creado: {user['email']}")
                    creados += 1
                else:
                    print(f"[KitsuManager] -> Usuario ya existía: {user['email']}")

            return True, f"Base de datos sembrada. {creados} nuevos usuarios creados con éxito."

        except Exception as e:
            return False, f"Fallo crítico durante el Seeding de Kitsu: {str(e)}"

    def get_all_templates(self) -> list:
        """
        Consulta la base de datos de Kitsu y devuelve una lista con 
        todos los esquemas de producción (Project Templates) disponibles.
        """
        try:
            return gazu.project_template.all_project_templates()
        except Exception as e:
            print(f"[KitsuManager] Error al consultar plantillas: {e}")
            return []

    def create_project_from_template(self, project_name: str, template_name: str = "OpenStudioHub Default") -> Tuple[bool, str, dict]:
        """
        Construye el proyecto inyectando la estructura de una plantilla de Kitsu.
        """
        try:
            if self.check_project_exists(project_name):
                return False, f"El proyecto '{project_name}' ya existe.", {}
            
            # 1. Buscar la plantilla por su nombre real
            template = gazu.project_template.get_project_template_by_name(template_name)
            
            # 2. Forjar el proyecto
            if template:
                print(f"[KitsuManager] Utilizando plantilla de Kitsu: {template_name}")
                nuevo_proyecto = gazu.project.new_project(name=project_name, project_template=template)
            else:
                print(f"[KitsuManager] WARNING: Plantilla '{template_name}' no encontrada. Creando proyecto en blanco.")
                nuevo_proyecto = gazu.project.new_project(project_name)

            if not nuevo_proyecto:
                return False, "Kitsu rechazó la creación del proyecto.", {}

            return True, "Project created successfully.", nuevo_proyecto
            
        except Exception as e:
            return False, f"Error crítico: {str(e)}", {}

    def check_edit_preview_exists(self, project_id: str) -> bool:
        """
        Verifica si existe al menos un archivo de previsualización (preview-file) 
        para la tarea de Edición en Kitsu. Retorna True si hay video, False si no.
        """
        try:
            edits = gazu.client.get(f"data/edits/with-tasks?project_id={project_id}")
            if not edits:
                return False
                
            for e in edits:
                if e.get('canceled'):
                    continue
                
                # Buscar el Task Type de 'Edit'
                r_task_types = gazu.client.get(f"data/edits/{e['id']}/task-types")
                edit_task_id = None
                for tt in r_task_types:
                    if tt['name'] == 'Edit':
                        edit_task_id = tt['id']
                        break
                
                if not edit_task_id:
                    continue
                
                # Buscar previews
                r_previews = gazu.client.get(f"data/edits/{e['id']}/preview-files")
                if not r_previews:
                    continue
                    
                preview_list = r_previews.get(edit_task_id, [])
                if preview_list and len(preview_list) > 0 and preview_list[0] is not None:
                    return True
                    
            return False
            
        except Exception as e:
            print(f"[KitsuManager] Error verificando la existencia de previews de edición: {e}")
            return False


```

--------------------------------------------------------------------------------

### Archivo: `core/local_installer.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/local_installer.py
# Rol Arquitectónico: Deployment Engine / Jailing Router
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.9.0 (Dynamic Addon Resolution)
# =========================================================================================

"""
Local deployment and orchestration engine.
Reads the topography signature from the NAS-synced pipeline folder, executes VCS 
cloning (Full vs Sparse Jailing), extracts tools into the isolated sandbox (vfs_local), 
and maps VFS Symlinks (vfs_shared). Anchored to English I/O standard.
"""

import json
import shutil
import zipfile
import tarfile
import platform
import os
from pathlib import Path
from typing import Tuple, Dict, Optional, Any

from core.vcs_router import VCSRouter
from core.sparse_manager import SparseManager

class LocalInstaller:
    def __init__(self, projects_dir: Path, config_factory):
        self.projects_dir = projects_dir
        self.config_factory = config_factory 
        
        # Dynamic Vault Resolution (B2B Standard)
        try:
            self.vault_root = self.config_factory.get_workspace_root() / "openstudio_vault"
        except Exception:
            self.vault_root = self.projects_dir.parent / "openstudio_vault"

        # Direct paths, strictly bypassing legacy intermediate folders
        self.boveda_addons = self.vault_root / "addons"
        self.boveda_blender = self.vault_root / "blender_versions"
        self.boveda_templates = self.vault_root / "project_templates"

    def verificar_instalacion(self, project_root: Path) -> bool:
        vfs_local = self.config_factory.get_vfs_local_name()
        vfs_svn = self.config_factory.get_vfs_svn_name()
        
        config_local = project_root / vfs_local / "project_config.json"
        vcs_dir = project_root / vfs_svn
        return config_local.exists() and vcs_dir.exists()

    def _get_os_info(self) -> Tuple[str, str]:
        system = platform.system().lower()
        if system == "linux":
            return "linux", "tar.xz"
        elif system == "windows":
            return "windows", "zip"
        else:
            return "macos", "dmg"

    def _instalar_blender(self, project_root: Path, vfs_local: str, version: str, status_callback):
        os_name, ext = self._get_os_info()
        archive_name = f"blender-{version}-{os_name}-x64.{ext}"
        archive_path = self.boveda_blender / archive_name

        dest_dir = project_root / vfs_local / "blender-build"
        folder_name_extracted = f"blender-{version}-{os_name}-x64"
        final_exec_dir = dest_dir / folder_name_extracted

        if final_exec_dir.exists():
            status_callback(f"Blender {version} is already cached locally.", "white")
            return

        if not archive_path.exists():
            raise FileNotFoundError(f"Binary archive not found in Vault: {archive_path}")

        status_callback(f"Extracting Blender {version} (This will take a couple of minutes)...", "yellow")
        dest_dir.mkdir(parents=True, exist_ok=True)

        if ext == "tar.xz":
            with tarfile.open(archive_path, "r:xz") as tar:
                tar.extractall(path=dest_dir)
        elif ext == "zip":
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)

        status_callback(f"Blender {version} extracted successfully.", "green")

    def _gestionar_vcs(self, project_root: Path, vfs_svn: str, vcs_user: str, vcs_pwd: str, 
                       status_callback, user_role: str, task_metadata: Optional[Dict[str, str]]) -> bool:
        vcs_root = project_root / vfs_svn
        vcs_type = self.config_factory.get_vcs_adapter_type()
        
        base_repo_url = self.config_factory.get_vcs_repository_url()
        final_repo_url = f"{base_repo_url}/{project_root.name}/{vfs_svn}"

        router = VCSRouter(vcs_type=vcs_type, repo_url=final_repo_url, workspace_dir=vcs_root)
        is_sparse_enabled = getattr(self.config_factory, 'is_vendor_sparse_enabled', lambda: True)()
        
        if user_role == "vendor" and is_sparse_enabled:
            status_callback("Initializing Sparse Checkout (Jailing Mode)...", "yellow")
            sparse_manager = SparseManager(vcs_router=router, status_callback=status_callback)
            success = sparse_manager.setup_vendor_workspace(task_metadata, vcs_user, vcs_pwd)
            return success
        
        adapter = router.get_adapter()
        status_callback(f"Synchronizing Full Workspace with {vcs_type.upper()}...", "yellow")
        
        try:
            adapter.full_pull(username=vcs_user, password=vcs_pwd)
            status_callback(f"{vcs_type.upper()}: Synchronization completed successfully.", "green")
            return True
        except RuntimeError as e:
            status_callback("Repository connection failed: Check credentials or network.", "red")
            print(f"[MACUARE HUB] VCS Driver Error: {e}")
            return False

    def instalar_entorno(self, project_root: Path, vcs_user: str, vcs_pwd: str, status_callback,
                         user_role: str = "artist", task_metadata: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
        vfs_svn = self.config_factory.get_vfs_svn_name()
        vfs_local = self.config_factory.get_vfs_local_name()
        vfs_pipe = self.config_factory.get_vfs_pipeline_name()
        vfs_shared = self.config_factory.get_vfs_shared_name()

        vcs_root = project_root / vfs_svn
        init_json_path = project_root / vfs_pipe / "project_init.json"

        try:
            if not init_json_path.exists():
                return False, f"Critical: project_init.json not found in {vfs_pipe}/. Make sure the NAS is fully synced."

            status_callback("Reading structural topography and manifest...", "yellow")
            with open(init_json_path, 'r', encoding='utf-8') as f:
                init_data = json.load(f)

            project_name = init_data.get("project_name", project_root.name)
            blender_version = init_data.get("blender_version", "4.2.0")
            dependencies = init_data.get("dependencies", {})
            template_name = init_data.get("template", "")

            checkout_ok = self._gestionar_vcs(
                project_root, vfs_svn, vcs_user, vcs_pwd, status_callback, user_role, task_metadata
            )
            if not checkout_ok:
                return False, "VCS Synchronization aborted."

            self._instalar_blender(project_root, vfs_local, blender_version, status_callback)

            if template_name:
                self._instalar_template(project_root, vfs_local, template_name, blender_version, status_callback)

            status_callback("Deploying project extensions...", "yellow")
            self._sincronizar_addons(project_root, vfs_local, dependencies, status_callback)
            
            status_callback("Configuring production VFS symlinks...", "yellow")
            self._crear_symlinks(project_path=project_root, vfs_svn=vfs_svn, vfs_shared=vfs_shared)

            status_callback("Generating local workspace configuration...", "yellow")
            config_local_dir = project_root / vfs_local
            config_local_dir.mkdir(exist_ok=True)

            local_config_data = {
                "project_name": project_name,
                "blender_version": blender_version,
                "kitsu_host": self.config_factory.get_kitsu_api_url(),
                "dependencies": dependencies,
                "paths": {
                    "root": str(project_root),
                    "svn_root": str(vcs_root),
                    "assets": str(vcs_root / "pro" / "assets"),
                    "shots": str(vcs_root / "pro" / "shots"),
                    "render_output": str(project_root / vfs_shared / "editorial" / "footage"),
                    "deliverables": str(project_root / vfs_shared / "editorial" / "deliver")
                }
            }

            config_local_file = config_local_dir / "project_config.json"
            with open(config_local_file, 'w', encoding='utf-8') as f:
                json.dump(local_config_data, f, indent=4)
            
            return True, "Local workspace installed and verified successfully."

        except Exception as e:
            return False, f"Critical error during local installation: {str(e)}"

    def _sincronizar_addons(self, project_root: Path, vfs_local: str, dependencies: dict, status_callback):
        """
        Extrae add-ons parseando el contrato de dependencias inyectado por ProjectBuilder.
        Resuelve las rutas de los .zip dinámicamente escaneando la bóveda local del usuario.
        """
        extensions_dir = project_root / vfs_local / "blender_data" / "extensions" / "user_default"
        extensions_dir.mkdir(parents=True, exist_ok=True)

        # Blindaje por si las dependencias fueron serializadas como string
        if isinstance(dependencies, str):
            try:
                dependencies = json.loads(dependencies)
            except Exception:
                dependencies = {}

        addons_dict = dependencies.get("addons", {})
        
        for addon_name, addon_version in addons_dict.items():
            status_callback(f"Buscando extensión: {addon_name} (v{addon_version})...", "yellow")
            
            # Búsqueda dinámica en la bóveda local de esta computadora
            origen_addon_zip = None
            if self.boveda_addons.exists():
                for archivo in self.boveda_addons.rglob("*.zip"):
                    if addon_name.lower() in archivo.name.lower():
                        origen_addon_zip = archivo
                        break

            if origen_addon_zip and origen_addon_zip.exists():
                safe_folder_name = addon_name.replace(" ", "_").lower()
                destino_addon = extensions_dir / safe_folder_name

                if not destino_addon.exists():
                    status_callback(f"Desplegando extensión: {addon_name}...", "yellow")
                    destino_addon.mkdir(parents=True, exist_ok=True)
                    try:
                        with zipfile.ZipFile(origen_addon_zip, 'r') as zip_ref:
                            zip_ref.extractall(destino_addon)
                    except zipfile.BadZipFile:
                        status_callback(f"Error: Archive {origen_addon_zip.name} is corrupted.", "red")
            else:
                status_callback(f"Warning: Extension '{addon_name}' not found in Vault.", "red")

    def _crear_symlinks(self, project_path: Path, vfs_svn: str, vfs_shared: str):
        shared_edit_dir = project_path / vfs_shared / "editorial"
        svn_edit_dir = project_path / vfs_svn / "edit"
        svn_edit_dir.mkdir(parents=True, exist_ok=True)
        
        folders_to_link = ["footage", "deliver", "export"]

        for folder in folders_to_link:
            target_path = shared_edit_dir / folder  
            target_path.mkdir(parents=True, exist_ok=True)
            
            link_path = svn_edit_dir / folder       
            if not link_path.exists() and not link_path.is_symlink():
                try:
                    link_path.symlink_to(target_path, target_is_directory=True)
                except OSError as e:
                    print(f"[VFS WARNING] Symlink creation failed (Privilege issue?): {e}")

    def _instalar_template(self, project_root: Path, vfs_local: str, template_name: str, blender_version: str, status_callback):
        source_path = self.boveda_templates / template_name
        if not source_path.exists():
            status_callback(f"Warning: Project template '{template_name}' not found in Vault.", "red")
            return

        os_name, _ = self._get_os_info()
        ver_major = ".".join(blender_version.split(".")[:2])
        blender_folder = f"blender-{blender_version}-{os_name}-x64"
        dest_path = (
            project_root / vfs_local / "blender-build" / blender_folder / 
            ver_major / "scripts" / "startup" / "bl_app_templates_system" / template_name
        )

        status_callback(f"Injecting template '{template_name}' into isolated container...", "yellow")
        if dest_path.exists():
            shutil.rmtree(dest_path)
            
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_path, dest_path, ignore=shutil.ignore_patterns('*.pyc', '__pycache__'))

```

--------------------------------------------------------------------------------

### Archivo: `core/manifest_manager.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/manifest_manager.py
# Rol Arquitectónico: Vault Manifest Controller (JSON CRUD)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0
# =========================================================================================

"""
Manages the vault_manifest.json file located in the NAS Vault.
Provides a strict CRUD interface to register, link, and query software dependencies 
(Add-ons, Templates) mapped specifically to Blender versions.
"""

import json
import shutil
from pathlib import Path
from typing import List, Dict

class ManifestManager:
    def __init__(self, vault_root: Path):
        self.vault_root = vault_root
        self.software_dir = self.vault_root / "blender_versions"
        self.manifest_path = self.software_dir / "vault_manifest.json"
        
        # Ensure directories exist
        self.software_dir.mkdir(parents=True, exist_ok=True)
        (self.software_dir / "blender_versions").mkdir(parents=True, exist_ok=True)
        (self.software_dir / "addons").mkdir(parents=True, exist_ok=True)
        
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict:
        """Reads the JSON manifest. Creates a default scaffold if missing."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[MANIFEST MANAGER] Failed to parse vault_manifest.json: {e}")
                
        # Default Scaffold
        return {
            "blender_versions": {}
        }

    def _save_manifest(self) -> bool:
        """Atomically writes the manifest state to the NAS."""
        try:
            with open(self.manifest_path, 'w', encoding='utf-8') as f:
                json.dump(self._manifest, f, indent=4)
            return True
        except Exception as e:
            print(f"[MANIFEST MANAGER] Critical write failure: {e}")
            return False

    def get_registered_blender_versions(self) -> List[str]:
        """Returns a list of Blender versions currently tracked in the manifest."""
        return list(self._manifest.get("blender_versions", {}).keys())

    def scan_local_blender_binaries(self) -> List[str]:
        """Scans the physical vault for downloaded Blender binaries and syncs the manifest."""
        blender_dir = self.software_dir / "blender_versions"
        found_versions = set()
        
        if blender_dir.exists():
            for file_path in blender_dir.iterdir():
                if file_path.is_file() and ("blender-" in file_path.name.lower()):
                    import re
                    match = re.search(r'blender-([0-9]+\.[0-9]+\.[0-9a-zA-Z.-]+)-', file_path.name.lower())
                    if match:
                        found_versions.add(match.group(1))
                        
        # Register any new versions found physically that aren't in the JSON
        changed = False
        for version in found_versions:
            if version not in self._manifest["blender_versions"]:
                self._manifest["blender_versions"][version] = {"addons": [], "templates": []}
                changed = True
                
        if changed:
            self._save_manifest()
            
        return sorted(list(found_versions), reverse=True)

    def get_addons_for_version(self, blender_version: str) -> List[Dict[str, str]]:
        """Retrieves mapped add-ons for a specific Blender version."""
        version_node = self._manifest.get("blender_versions", {}).get(blender_version, {})
        return version_node.get("addons", [])

    def register_addon(self, blender_version: str, addon_name: str, addon_version: str, source_zip: Path) -> tuple[bool, str]:
        """Copies an Add-on to the vault and links it to the specified Blender version."""
        if not source_zip.exists() or not source_zip.name.endswith('.zip'):
            return False, "Invalid source file. Must be a .zip archive."
            
        if blender_version not in self._manifest["blender_versions"]:
            self._manifest["blender_versions"][blender_version] = {"addons": [], "templates": []}

        # Format and copy file
        safe_name = addon_name.replace(" ", "_").lower()
        dest_filename = f"{safe_name}_v{addon_version}.zip"
        dest_path = self.software_dir / "addons" / dest_filename
        
        try:
            shutil.copy2(source_zip, dest_path)
        except Exception as e:
            return False, f"File copy failed: {e}"

        # Update JSON mapping
        relative_path = f"addons/{dest_filename}"
        new_entry = {
            "name": addon_name,
            "version": addon_version,
            "path": relative_path
        }
        
        # Prevent duplicates
        addons_list = self._manifest["blender_versions"][blender_version]["addons"]
        addons_list = [a for a in addons_list if a["name"] != addon_name]
        addons_list.append(new_entry)
        
        self._manifest["blender_versions"][blender_version]["addons"] = addons_list
        
        if self._save_manifest():
            return True, "Add-on registered and copied successfully."
        else:
            return False, "Add-on copied but manifest update failed."

```

--------------------------------------------------------------------------------

### Archivo: `core/nas_manager.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/nas_manager.py
# Rol Arquitectónico: File System Manager / NAS Orchestrator
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0 (Genesis)
# =========================================================================================

"""
Gestor centralizado para las operaciones de lectura y escritura en el servidor NAS (Local/Red).
Aísla a la UI de las comprobaciones de disco, búsquedas de directorios,
lectura de manifiestos (Blueprints) y operaciones destructivas.
"""

import json
import shutil
from pathlib import Path
from typing import Optional, Dict

class NasManager:
    def __init__(self, base_dir: Path):
        """
        Inicializa el gestor con la ruta raíz del almacenamiento local o de red (NAS).
        """
        self.base_dir = Path(base_dir) if base_dir else None

    def is_connected(self) -> bool:
        """Verifica si la ruta raíz está configurada y accesible."""
        return self.base_dir is not None and self.base_dir.exists()

    def resolve_project_dir(self, project_name: str, project_code: str = "") -> Optional[Path]:
        """
        Intenta resolver la ruta física del proyecto usando su nombre o su código.
        """
        if not self.is_connected():
            return None

        # 1. Buscar coincidencia exacta (Nombre crudo)
        target_dir = self.base_dir / project_name
        if target_dir.exists():
            return target_dir

        # 2. Buscar versión normalizada (Guiones en vez de espacios, minúsculas)
        clean_name = project_name.strip().lower().replace(" ", "-") if project_name else "unknown"
        target_dir_clean = self.base_dir / clean_name
        if target_dir_clean.exists():
            return target_dir_clean

        # 3. Fallback al código corto de Kitsu
        if project_code:
            target_dir_code = self.base_dir / project_code
            if target_dir_code.exists():
                return target_dir_code

        return None

    def get_project_blueprint(self, project_dir: Path) -> Dict:
        """
        Busca dinámicamente el archivo project_init.json dentro de la carpeta
        del proyecto (independientemente del nombre del VFS interno) y retorna sus metadatos.
        """
        if not project_dir or not project_dir.exists():
            return {}

        try:
            # Busca un nivel adentro usando glob
            meta_files = list(project_dir.glob("*/project_init.json"))
            if meta_files:
                with open(meta_files[0], "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[NasManager] Error leyendo blueprint en {project_dir}: {e}")
            
        return {}

    def delete_project_folder(self, project_dir: Path) -> bool:
        """
        Destruye recursivamente el directorio del proyecto en el disco local/NAS.
        """
        if not project_dir or not project_dir.exists():
            return False

        try:
            shutil.rmtree(project_dir, ignore_errors=True)
            print(f"[NasManager] Directorio local destruido exitosamente: {project_dir}")
            return True
        except Exception as e:
            print(f"[NasManager] Error al destruir directorio {project_dir}: {e}")
            return False

```

--------------------------------------------------------------------------------

### Archivo: `core/path_resolver.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/path_resolver.py
# Rol Arquitectónico: Motor Lógico / Kitsu Path Resolver
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.1
# =========================================================================================

"""
Traduce las entidades de la API de Kitsu (Tareas) a rutas físicas de disco local.
Implementa las convenciones de nomenclatura del estudio según el SDD, adaptado
estrictamente a payloads de datos que mapean el tipo bajo 'entity_type_name'.
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
            
        # Kitsu mapping: Extraer tipo desde entity_type_name o fallback a entity_type
        entity_type = task_data.get("entity_type_name", task_data.get("entity_type", "")).lower()
        entity_name = task_data.get("entity_name", "")
        
        if entity_type == "shot":
            seq_name = task_data.get("sequence_name", "")
            if not seq_name or not entity_name:
                raise ValueError("Metadatos incompletos para Shot: Falta sequence_name.")
            
            return f"pro/shots/{seq_name}/{entity_name}"
            
        elif entity_type == "asset":
            # Normalización Jailing para Assets: Si no hay categoría asignada cae en props
            asset_type = task_data.get("asset_type_name", "props").lower()
            if not entity_name:
                raise ValueError("Metadatos incompletos para Asset: Falta entity_name.")
            
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
            
        # Corrección de Mapeo API: Captura 'entity_type_name' mapeado por Kitsu
        entity_type = task_data.get("entity_type_name", task_data.get("entity_type", "")).lower()
        entity_name = task_data.get("entity_name", "")
        
        # Priorizar short_name para archivos (ej. 'anim' o 'modelado')
        task_name = task_data.get("task_type_short_name", task_data.get("task_type_name", "generic")).lower()
        
        # Normalizar strings con acentos comunes en entornos en español (animación -> anim)
        if "anim" in task_name:
            task_name = "anim"
        elif "model" in task_name:
            task_name = "model"

        # NUEVO: Soporte explícito para Storyboard (Entidad Secuencia)
        if entity_type == "sequence" or task_name == "storyboard":
            # Para las secuencias, 'entity_name' es el nombre de la secuencia (ej: '01' o 'sq010')
            seq_name = task_data.get("entity_name", task_data.get("sequence_name", "")).lower()
            if not seq_name: return None
            
            # Leemos la ruta que el HeadlessBuilder forjó (Regla estricta de Topología)
            return f"edit/storyboards/{seq_name}-storyboard.blend"
        
        # NUEVO: Soporte explícito para Tareas de Edición
        if task_name == "edit" or entity_type == "edit":
            project_name = task_data.get("project_name", "project").strip().lower().replace(" ", "-")
            return f"edit/{project_name}-edit.blend"

        if entity_type == "shot":
            seq_name = task_data.get("sequence_name", "")
            if not seq_name or not entity_name: return None
            return f"pro/shots/{seq_name}/{entity_name}/{entity_name}-{task_name}.blend"
            
        elif entity_type == "asset":
            asset_type = task_data.get("asset_type_name", "props").lower()
            if not entity_name: return None
            return f"pro/assets/{asset_type}/{entity_name}/{asset_type}-{entity_name}-{task_name}.blend"
            
        return None

```

--------------------------------------------------------------------------------

### Archivo: `core/production_manager.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/production_manager.py
# Rol Arquitectónico: Production Orchestrator / Batch Entity Genesis
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0
# =========================================================================================

"""
Logical orchestrator for the Production Manager (PM).
Connects to Gazu (Kitsu API) to fetch entities proposed by Editorial, batch-spawns 
production tasks, and executes the physical generation of master .blend files inside 
the VCS repository via Semantic Topography. Anchored to English standard.
"""

import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple
import gazu

class ProductionManager:
    def __init__(self, auth_manager, config_factory):
        self.auth_manager = auth_manager
        self.config_factory = config_factory
        
        try:
            self.vault_root = self.config_factory.get_workspace_root() / "openstudio_vault"
        except Exception:
            self.vault_root = Path.home() / "openstudio_vault"
            
        self.vault_templates_dir = self.vault_root / "project_templates"

    def get_pending_entities(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Queries the Kitsu API for Shots and Assets that require PM validation.
        Typically, these are pushed by the Editorial department (Blender VSE) 
        and sit in 'Pending Validation' or 'Waiting for Approval' statuses.
        """
        pending_list = []
        try:
            # Ampliamos el espectro para atrapar las tomas recién creadas por el Editor
            valid_statuses = ["Todo", "Ready To Start"]
            
            shots = gazu.shot.all_shots_for_project(project_id)
            for shot in shots:
                status = shot.get("status", "Todo") # Fallback a Todo si es nueva
                if status in valid_statuses:
                    seq = gazu.shot.get_sequence(shot.get("sequence_id"))
                    pending_list.append({
                        "id": shot["id"],
                        "name": shot["name"],
                        "type": "Shot",
                        "parent": seq["name"] if seq else "Unknown",
                        "frame_in": shot.get("nb_frames", 0),
                        "status": status,
                        "raw_data": shot
                    })
                    
            assets = gazu.asset.all_assets_for_project(project_id)
            for asset in assets:
                status = asset.get("status", "Todo")
                if status == "Todo":
                    
                    asset_type_id = asset.get("entity_type_id", "")

                    asset_type = gazu.asset.get_asset_type(asset.get("entity_type_id"))
                    
                    pending_list.append({
                        "id": asset["id"],
                        "name": asset["name"],
                        "Parent": asset.get("parent"),
                        "type": asset_type["name"] if asset_type else "Unknown",
                        "asset_type_id": asset_type_id,
                        "frame_in": 0,
                        "status": status,
                        "raw_data": asset
                    })
                    
        except Exception as e:
            print(f"[PRODUCTION MANAGER] Gazu API Error fetching entities: {e}")
            
        return pending_list

    def map_file_to_task(self, entity_dict: dict, task_type_name: str, relative_path: str) -> bool:
        """
        Utility for the Spawning Workers: Inyecta la ruta física del .blend generado 
        en la Metadata de la entidad (Custom Data) para que el PathResolver la encuentre.
        """
        try:
            entity_data = entity_dict.get("data")
            if not entity_data:
                entity_data = {}
                
            entity_data["blend_file_path"] = relative_path
            gazu.entity.update_entity_data(entity_dict["id"], entity_data)
            return True
        except Exception as e:
            print(f"[PRODUCTION MANAGER] Error maping file to Kitsu: {e}")
            return False

    def batch_create_entity_files(self, project_name: str, entities: List[Dict[str, Any]], 
                                  base_template: str, task_types: List[str], status_callback) -> Tuple[bool, str]:
        """
        The genesis engine. Iterates over approved entities to:
        1. Spawn production tasks in Kitsu.
        2. Generate the physical nested directories in the VCS Workspace.
        3. Copy the base template .blend file to prevent Sparse Checkout deadlocks.
        """
        if not entities:
            return False, "No entities provided for batch creation."

        # 1. Resolve Project Root & Topography
        try:
            project_root = self.config_factory.get_workspace_root() / project_name
            vfs_svn = self.config_factory.get_vfs_svn_name()
            vcs_root = project_root / vfs_svn
        except Exception as e:
            return False, f"Failed to resolve NAS topography: {e}"

        template_path = self.vault_templates_dir / base_template
        if not template_path.exists() or not template_path.is_file():
            return False, f"Master template '{base_template}' not found in Vault."

        success_count = 0
        error_count = 0

        for idx, entity in enumerate(entities):
            e_name = entity.get("name", "unknown").lower().replace(" ", "_")
            e_type = entity.get("type", "Shot")
            e_parent = entity.get("parent", "unknown").lower().replace(" ", "_")
            e_id = entity.get("id")
            
            status_callback(f"Processing {e_type}: {e_name} ({idx + 1}/{len(entities)})...", "yellow")
            
            # 2. Path Generation (Blender Studio Standard via Semantic Topography)
            if e_type == "Shot":
                entity_dir = vcs_root / "pro" / "shots" / e_parent / e_name
            else:
                entity_dir = vcs_root / "pro" / "assets" / e_parent / e_name

            try:
                # 3. Directory Scaffolding
                entity_dir.mkdir(parents=True, exist_ok=True)
                
                # 4. Kitsu Task Spawning & File Injection
                for task_name in task_types:
                    # Spawn in API (Silent fail if already exists)
                    try:
                        gazu_task_type = gazu.task.get_task_type_by_name(task_name)
                        if gazu_task_type:
                            gazu.task.create_task(e_id, gazu_task_type)
                    except Exception as api_e:
                        print(f"[PRODUCTION MANAGER] Task {task_name} already exists or API error: {api_e}")

                    # Spawn Physical .blend file
                    safe_task_name = task_name.lower().replace(" ", "")
                    blend_filename = f"{e_name}-{safe_task_name}.blend"
                    dest_blend_path = entity_dir / blend_filename
                    
                    if not dest_blend_path.exists():
                        shutil.copy2(template_path, dest_blend_path)
                
                # Update Kitsu Status to active (Ready to Start / WIP)
                # In a real scenario, you map a specific status UUID.
                # gazu.entity.update_entity_status(e_id, "Ready to Start")
                
                success_count += 1
                
            except Exception as io_error:
                print(f"[PRODUCTION MANAGER] File System error on {e_name}: {io_error}")
                error_count += 1

        status_callback(f"Batch completed: {success_count} created, {error_count} failed.", "green" if error_count == 0 else "yellow")
        return True, f"Successfully processed {success_count} entities."

    def get_or_create_storyboard_task_type(self, project_id: str) -> dict:
        """
        Busca el Task Type 'Storyboard' para 'Sequence'. 
        Gracias a la plantilla del TD, este ya existe en el proyecto.
        """
        # 1. Buscar a nivel global
        task_types = gazu.task.all_task_types()
        storyboard_tt = next((tt for tt in task_types if tt["name"].lower() == "storyboard" and tt["for_entity"].lower() == "sequence"), None)
        
        # 2. Fallback de seguridad (solo lo crea en memoria global si alguien lo borró)
        if not storyboard_tt:
            storyboard_tt = gazu.task.new_task_type(
                name="Storyboard", 
                color="#F97316",
                for_entity="Sequence"
            )
            
        # ¡ELIMINADO el gazu.project.add_task_type que causaba el error de permisos!
        return storyboard_tt

    def create_sequence_with_task(self, project_id: str, sequence_name: str, task_type_id: str) -> dict:
        """Crea la entidad Sequence y le adjunta la tarea de Storyboard."""
        # Kitsu requiere el nombre del proyecto como objeto o dict para crear la secuencia
        project = gazu.project.get_project(project_id)
        
        # Crear la secuencia en Kitsu
        sequence = gazu.shot.new_sequence(project, name=sequence_name)
        
        # Crear la tarea inicial de Storyboard
        # El estado inicial suele ser 'todo' o el por defecto del estudio
        default_status = gazu.task.get_default_task_status()
        gazu.task.new_task(
            entity=sequence, 
            task_type=task_type_id, 
            name="main", 
            task_status=default_status
        )
        return sequence

```

--------------------------------------------------------------------------------

### Archivo: `core/project_builder.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/project_builder.py
# Rol Arquitectónico: I/O Orchestrator / Project Generator (B2B Multi-OS)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.6.1 (Restauración de Headless Builder)
# =========================================================================================

# import os
import json
import shutil
# import zipfile
# import tarfile
# import subprocess
# import tempfile
import platform
from pathlib import Path

from core.vcs_router import VCSRouter
from core.kitsu_manager import KitsuManager

class ProjectBuilder:
    def __init__(self, config_factory):
        self.config_factory = config_factory

    @property
    def base_dir(self) -> Path:
        return self.config_factory.get_workspace_root()

    @property
    def vault_root(self) -> Path:
        return self.config_factory.get_vault_path()

    @property
    def vault_templates_dir(self) -> Path:
        return self.vault_root / "project_templates"

    @property
    def vault_blender_dir(self) -> Path:
        return self.vault_root / "blender_versions"

    def _get_os_info(self) -> str:
        system = platform.system().lower()
        if system == "linux": return "linux"
        elif system == "windows": return "windows"
        else: return "macos"

    def create_project(self, project_name: str, blender_version: str, dependencies: dict, project_template: str, splash_image_path: str = "", vcs_user: str = "", vcs_pwd: str = "") -> tuple[bool, str]:
        if not project_name.strip(): return False, "Project name cannot be empty."
        if not blender_version.strip(): return False, "You must specify a Blender version."

        folder_name = project_name.strip().lower().replace(" ", "-")
        project_path = self.base_dir / folder_name

        if project_path.exists():
            return False, f"Folder '{folder_name}' already exists on the NAS."

        kitsu = KitsuManager()
        
        # INYECCIÓN DE LA PLANTILLA DE KITSU POR DEFECTO
        success, kitsu_msg, kitsu_project = kitsu.create_project_from_template(
            project_name.strip(), 
            template_name="standard-3d-production"
        )
        
        if not success:
            return False, f"Abortado por Kitsu: {kitsu_msg}"
            
        project_id = kitsu_project.get("id", "")
        print(f"[ProjectBuilder] Entidad Kitsu forjada con plantilla. ID: {project_id}")

        try:
            vfs_svn = self.config_factory.get_vfs_svn_name()
            vfs_shared = self.config_factory.get_vfs_shared_name()
            vfs_local = self.config_factory.get_vfs_local_name()
            vfs_pipe = self.config_factory.get_vfs_pipeline_name()
            custom_dirs = self.config_factory.get_custom_dirs()

            # Solo carpetas estructurales, el PM generará el resto a demanda
            base_folders = [
                vfs_local, vfs_shared, vfs_pipe,
                f"{vfs_svn}/pro", f"{vfs_svn}/tools"
                f"{vfs_svn}/pro/assets", 
                f"{vfs_svn}/pro/shots", 
                f"{vfs_svn}/pro/edit", 
                f"{vfs_svn}/pro/strips"
            ] + custom_dirs

            for folder in base_folders:
                (project_path / folder).mkdir(parents=True, exist_ok=True)

            template_path = self.vault_templates_dir / project_template
            if template_path.exists() and template_path.is_dir():
                for item in template_path.iterdir():
                    if item.is_file(): shutil.copy2(item, project_path / vfs_svn)
                    elif item.is_dir(): shutil.copytree(item, project_path / vfs_svn / item.name, dirs_exist_ok=True)

            payload_data = {
                "project_name": project_name.strip(),
                "kitsu_project_id": project_id,
                "blender_version": blender_version.strip(),
                "template": project_template.strip(),
                "dependencies": dependencies,
                "topography_signature": {
                    "vfs_svn": vfs_svn, "vfs_shared": vfs_shared,
                    "vfs_local": vfs_local, "vfs_pipeline": vfs_pipe
                }
            }

            payload_file_svn = project_path / vfs_svn / "project_init.json"
            with open(payload_file_svn, 'w', encoding='utf-8') as f: json.dump(payload_data, f, indent=4)
            shutil.copy2(payload_file_svn, project_path / vfs_pipe / "project_init.json")

            if splash_image_path:
                splash_source = Path(splash_image_path)
                if splash_source.exists() and splash_source.is_file():
                    shutil.copy(splash_source, project_path / vfs_pipe / "splash.png")
                    kitsu.upload_project_splash(project_id, splash_image_path)

            base_repo_url = self.config_factory.get_vcs_repository_url()
            
            try:
                vcs_type = self.config_factory.get_vcs_adapter_type()
                final_repo_url = f"{base_repo_url}/{folder_name}/{vfs_svn}" if "localhost" in base_repo_url else f"{base_repo_url}/{folder_name}/{vfs_svn}"
                
                vcs_root = project_path / vfs_svn
                router = VCSRouter(vcs_type=vcs_type, repo_url=final_repo_url, workspace_dir=vcs_root)
                adapter = router.get_adapter()
                
                if "localhost" in base_repo_url and not vcs_user:
                    vcs_user, vcs_pwd = "admin", "admin123"
                    
                adapter.create_server_repository(project_name, vfs_svn)
                
                if vcs_user and vcs_pwd:
                    adapter.full_pull(username=vcs_user, password=vcs_pwd)
                    print("[ProjectBuilder] Repositorio VCS emparejado.")
                    
                    ignore_patterns = [f"{vfs_local}", f"{vfs_shared}", f"{vfs_pipe}", "*.blend1", "*.blend2", "quit.blend"]
                    adapter.setup_ignore(ignore_patterns)

                    # INYECCIÓN DEL SCRIPT PARA SVN/VFS LOCAL
                    startup_dir = project_path / vfs_local / "blender_data" / "scripts" / "startup"
                    startup_dir.mkdir(parents=True, exist_ok=True)
                    patch_file = startup_dir / "00_openstudio_vfs_patch.py"
                    
                    template_patch_path = Path(__file__).parent / "templates" / "vfs_patch.py.template"
                    if template_patch_path.exists():
                        with open(template_patch_path, "r", encoding="utf-8") as t_file:
                            patch_content = t_file.read()
                        patch_content = patch_content.replace("{VFS_SVN_PLACEHOLDER}", vfs_svn)
                        with open(patch_file, "w", encoding="utf-8") as f:
                            f.write(patch_content)
                        print(f"[ProjectBuilder] Parche VFS inyectado exitosamente.")

                    # COMMIT INICIAL LIMPIO (Sin forzar edición)
                    adapter.add_all(".")
                    adapter.commit(
                        message="Initial commit: Hub Project Blueprint established.", 
                        paths=["."], 
                        username=vcs_user, 
                        password=vcs_pwd
                    )
                else:
                    print("[ProjectBuilder] No VCS credentials provided. Skipping initial commit.")
            except Exception as e:
                print(f"[ProjectBuilder] Warning: Initial VCS commit failed: {e}")

            return True, f"Project '{folder_name}' successfully generated."

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"\n[ProjectBuilder] CRASH FATAL:\n{error_trace}\n")
            return False, f"System error creating directory tree: {str(e)}"

```

--------------------------------------------------------------------------------

### Archivo: `core/provisioning_workers.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/provisioning_workers.py
# Rol Arquitectónico: Core Services / Network Downloaders & Archivers
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0
# =========================================================================================

import shutil
import tempfile
import urllib.request
import zipfile
import os

from pathlib import Path
from html.parser import HTMLParser
from PySide6.QtCore import Signal, QThread

from core.addon_inspector import AddonInspector
from core.manifest_manager import ManifestManager
from core.addon_parser import AddonParser

class ApacheIndexParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href':
                    self.links.append(value)

class RepoFolderFetcherWorker(QThread):
    folders_ready = Signal(list)
    status = Signal(str, str)

    def run(self):
        try:
            req = urllib.request.Request("https://download.blender.org/release/", headers={'User-Agent': 'OpenStudioHub/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            parser = ApacheIndexParser()
            parser.feed(html)
            raw_folders = [l for l in parser.links if l.endswith('/') and ('Blender' in l or l.replace('/', '').replace('.', '').isdigit())]
            raw_folders.sort(reverse=True)
            self.folders_ready.emit(raw_folders)
            self.status.emit("✓ Remote directory tree fetched.", "green")
        except Exception as e:
            self.status.emit(f"✗ Failed to reach remote repository: {str(e)}", "red")
            self.folders_ready.emit([])

class RepoFileFetcherWorker(QThread):
    files_ready = Signal(list)
    status = Signal(str, str)

    def __init__(self, folder_name: str):
        super().__init__()
        self.folder_name = folder_name

    def run(self):
        try:
            url = f"https://download.blender.org/release/{self.folder_name}"
            req = urllib.request.Request(url, headers={'User-Agent': 'OpenStudioHub/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            parser = ApacheIndexParser()
            parser.feed(html)
            valid_exts = ('.zip', '.xz', '.dmg', '.msi', '.exe', '.pkg')
            raw_files = [f for f in parser.links if f.endswith(valid_exts) and not f.startswith('?')]
            raw_files.sort()
            self.files_ready.emit(raw_files)
        except Exception as e:
            self.status.emit(f"✗ Failed to fetch binaries: {str(e)}", "red")
            self.files_ready.emit([])

class BlenderDirectDownloadWorker(QThread):
    progress = Signal(int)
    status = Signal(str, str)
    finished = Signal(bool, str)

    def __init__(self, folder_name: str, file_name: str, target_dir: Path):
        super().__init__()
        self.folder_name = folder_name
        self.file_name = file_name
        self.target_dir = target_dir

    def run(self):
        try:
            final_path = self.target_dir / self.file_name
            
            # 1. Inteligencia de Caché: Evitar descargas duplicadas
            if final_path.exists():
                self.status.emit(f"✓ Asset '{self.file_name}' already exists in Vault. Skipped download.", "green")
                self.progress.emit(100)
                self.finished.emit(True, self.file_name)
                return

            # 2. Flujo de Descarga
            url = f"https://download.blender.org/release/{self.folder_name}{self.file_name}"
            self.target_dir.mkdir(parents=True, exist_ok=True)
            archive_path = self.target_dir / f"{self.file_name}.tmp"
            
            self.status.emit(f"Downloading selected package: {self.file_name}...", "yellow")
            req = urllib.request.Request(url, headers={'User-Agent': 'OpenStudioHub/1.0'})
            
            with urllib.request.urlopen(req) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                block_size = 1024 * 64

                with open(archive_path, 'wb') as out_file:
                    while True:
                        block = response.read(block_size)
                        if not block: break
                        downloaded += len(block)
                        out_file.write(block)
                        if total_size > 0:
                            self.progress.emit(int((downloaded / total_size) * 100))

            archive_path.rename(final_path)
            self.status.emit(f"✓ Compressed asset '{self.file_name}' mirrored on NAS.", "green")
            self.finished.emit(True, self.file_name)

        except Exception as e:
            self.status.emit(f"✗ Archive transfer failed: {str(e)}", "red")
            self.finished.emit(False, "")

class StudioToolsFetchWorker(QThread):
    """
    Descarga la release oficial de Studio Tools, detecta las carpetas internas,
    las re-empaqueta en archivos .zip dinámicamente según la barrera de Blender 4.2,
    y registra los add-ons compatibles en la bóveda.
    """
    progress_updated = Signal(int)
    status_update = Signal(str, str)
    finished_packing = Signal(dict) 
    error_occurred = Signal(str)

    def __init__(self, vault_root: Path, current_version: str):
        super().__init__()
        self.vault_root = vault_root
        self.current_version = current_version
        self.url = "https://projects.blender.org/studio/blender-studio-tools/releases/download/latest/blender_studio_add-ons_latest.zip"

    def run(self):
        # 0. Instanciamos el manager de forma segura, asilado dentro de este hilo
        from core.manifest_manager import ManifestManager
        self.manifest_manager = ManifestManager(self.vault_root)

        temp_dir = Path(tempfile.mkdtemp())
        master_zip_path = temp_dir / "blender_studio_add-ons_latest.zip"
        
        try:
            # 1. Descarga del Release ZIP usando urllib.request nativo
            # (Mantén exactamente el mismo bloque try/except que tenías para la descarga, 
            # extracción y re-empaquetado dual de la iteración anterior)
            
            self.status_update.emit("Descargando release oficial de Studio Tools...", "yellow")
            import urllib.request
            req = urllib.request.Request(self.url, headers={'User-Agent': 'OpenStudioHub/1.0'})
            
            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                with open(master_zip_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk: break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            self.progress_updated.emit(int((downloaded / total_size) * 30))
                            
            self.status_update.emit("Extrayendo master branch...", "yellow")
            
            # 2. Extracción del Master ZIP
            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir()
            with zipfile.ZipFile(master_zip_path, 'r') as zf:
                zf.extractall(extract_dir)
                
            # 3. Ubicar el directorio raíz de los add-ons (manejando la subcarpeta de Gitea)
            addons_root = extract_dir
            subdirs = [d for d in addons_root.iterdir() if d.is_dir()]
            if len(subdirs) == 1 and "blender_studio_add-ons" in subdirs[0].name:
                addons_root = subdirs[0]

            addon_dirs = [d for d in addons_root.iterdir() if d.is_dir() and ((d / "blender_manifest.toml").exists() or (d / "__init__.py").exists())]
            
            if not addon_dirs:
                raise ValueError("No se encontraron directorios de add-ons válidos en la release.")
                
            total_addons = len(addon_dirs)
            registered_count = 0
            
            # 2. Creamos un diccionario para acumular lo que logramos registrar
            nuevos_addons_ram = {}
            import os

            addons_dir =self.vault_root / "addons"
            addons_dir.mkdir(parents=True, exist_ok=True)

            for i, addon_dir in enumerate(addon_dirs):
                self.status_update.emit(f"Empaquetando y validando {addon_dir.name}...", "yellow")
                addon_zip_path = temp_dir / f"{addon_dir.name}.zip"
                
                # Barrera Blender 4.2+: Las extensiones exigen el manifiesto en la raíz absoluta del ZIP.
                # Legacy (<4.2): Los add-ons clásicos exigen estar contenidos en una subcarpeta.
                is_extension = (addon_dir / "blender_manifest.toml").exists()
                
                with zipfile.ZipFile(addon_zip_path, 'w', zipfile.ZIP_DEFLATED) as out_zf:
                    for root, _, files in os.walk(addon_dir):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(addon_dir) if is_extension else file_path.relative_to(addon_dir.parent)
                            out_zf.write(file_path, arcname)
                
                # Validación y Registro en la Bóveda
                parsed = AddonParser.parse_zip(addon_zip_path)
                if parsed["is_valid"]:
                    if AddonParser.is_compatible(parsed["min_blender_version"], self.current_version):
                        addon_name_parsed = parsed["name"]
                        addon_ver_parsed = parsed["version"]

                        target_zip_name = f"{addon_name_parsed}-{addon_ver_parsed}.zip"
                        target_zip_path = addons_dir / target_zip_name
                        shutil.copy2(addon_zip_path, target_zip_path)

                        exito, msg = self.manifest_manager.register_addon(
                            blender_version=self.current_version,
                            addon_name=addon_name_parsed,
                            addon_version=addon_ver_parsed,
                            source_zip=target_zip_path
                        )
                        if exito:
                            registered_count += 1
                            # 3. Guardamos los datos con la misma estructura que usa TabSoftware
                            desc = parsed.get("description", "Blender Studio Tool")
                            nuevos_addons_ram[addon_name_parsed] = {
                                "version": addon_ver_parsed,
                                "description": desc[:60] + "..." if len(desc) > 60 else desc,
                                "mandatory": False,
                                "requires": []
                            }
                            
                self.progress_updated.emit(30 + int(((i + 1) / total_addons) * 70))
                
            self.status_update.emit(f"✓ Studio Tools Auto-Fetch completado. {registered_count} add-ons registrados.", "green")
            
            # 4. Emitimos la señal entregando el diccionario a la interfaz
            self.finished_packing.emit(nuevos_addons_ram)
            
        except Exception as e:
            import traceback
            print(f"[StudioToolsFetchWorker] ERROR: {traceback.format_exc()}")
            self.error_occurred.emit(str(e))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

```

--------------------------------------------------------------------------------

### Archivo: `core/sparse_manager.py`

```python
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
a la capa de abstracción VCS de forma iterativa y recursiva leyendo los 
manifiestos de dependencias locales (*-meta.json).
"""

import os
import json
from pathlib import Path
from typing import Dict, Callable, List, Set
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
        Orquesta el descubrimiento de ruta inicial y detona el pull recursivo.
        """
        self.status_callback("Calculando ruta estricta de Jailing...", "yellow")
        
        print("\n[SPARSE DEBUG] Iniciando Jailing...")
        print(f"[SPARSE DEBUG] Metadata recibida de Kitsu: {task_metadata}")

        try:
            # 1. Resolución de Ruta Principal (Traducción Kitsu -> LocalFS)
            sparse_path = PathResolver.get_sparse_path(task_metadata)
            
            print(f"[SPARSE DEBUG] Ruta resuelta por el PathResolver: {sparse_path}")
            
            if not sparse_path:
                print("[SPARSE ERROR] La ruta resuelta está vacía o es inválida.")
                self.status_callback("Error: Metadatos de tarea inválidos o vacíos.", "red")
                return False
            
            self.status_callback(f"Jailing activo. Descargando dependencias...", "yellow")
            
            # 2. Delegación Recursiva al Adaptador VCS
            adapter = self.router.get_adapter()
            visited_paths = set()
            
            # Disparamos la recursividad con la carpeta inicial de la tarea
            self._pull_recursive(
                paths=[sparse_path], 
                adapter=adapter, 
                username=username, 
                password=password, 
                visited=visited_paths
            )
            
            print("[SPARSE DEBUG] Jailing completado con éxito.")
            self.status_callback("Jailing completado: Workspace restrictivo preparado.", "green")
            return True
            
        except ValueError as ve:
            print(f"[SPARSE ERROR FATAL] ValueError atrapado (Lógica Kitsu): {ve}")
            self.status_callback(f"Error de Resolución Kitsu: {str(ve)}", "red")
            return False
        except RuntimeError as re:
            print(f"[SPARSE ERROR FATAL] RuntimeError (VCS/Red): {re}")
            self.status_callback("Fallo de conexión en Sparse Checkout. Revisa credenciales.", "red")
            return False
        except Exception as e:
            print(f"[SPARSE ERROR FATAL] Excepción crítica general: {e}")
            self.status_callback(f"Error crítico durante el Jailing: {str(e)}", "red")
            return False

    def _pull_recursive(self, paths: List[str], adapter, username: str, password: str, visited: Set[str]):
        """
        Descarga las rutas dadas, busca manifiestos (*-meta.json) en ellas y 
        dispara una nueva descarga para las dependencias descubiertas.
        """
        unvisited = [p for p in paths if p not in visited]
        if not unvisited:
            return

        print(f"[SPARSE DEBUG] Descargando lote: {unvisited}")
        # Descarga física de los archivos o directorios
        adapter.sparse_pull(paths=unvisited, username=username, password=password)
        visited.update(unvisited)

        next_batch = set()

        for path in unvisited:
            local_path = Path(adapter.workspace_dir) / path
            
            # Buscar manifiestos de dependencias
            meta_files = []
            if local_path.is_dir():
                meta_files = list(local_path.glob("*-meta.json"))
            elif local_path.is_file() and local_path.name.endswith("-meta.json"):
                meta_files = [local_path]
            
            # Analizar cada manifiesto encontrado
            for meta_file in meta_files:
                print(f"[SPARSE DEBUG] Analizando manifiesto: {meta_file.name}")
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    deps = data.get("dependencies", [])
                    for dep in deps:
                        if dep.startswith("//"):
                            # Limpiar la sintaxis relativa de Blender
                            rel_to_blend = dep[2:] 
                            # Determinar ruta relativa al repositorio (SVN root)
                            rel_dir = meta_file.parent.relative_to(adapter.workspace_dir)
                            
                            # Normalizar la ruta final uniendo la base del meta con el destino del dep
                            combined = os.path.normpath(os.path.join(str(rel_dir), rel_to_blend))
                            combined = combined.replace("\\", "/") # SVN exige forward slashes
                            
                            if combined not in visited:
                                next_batch.add(combined)
                                # Si requerimos un .blend, exigimos también su manifiesto para continuar la cadena
                                if combined.endswith(".blend"):
                                    meta_combo = combined.replace(".blend", "-meta.json")
                                    if meta_combo not in visited:
                                        next_batch.add(meta_combo)
                                        
                except Exception as e:
                    print(f"[SPARSE ERROR] Fallo al leer manifiesto {meta_file.name}: {e}")
        
        # Si descubrimos nuevas rutas, las enviamos a descargar en el siguiente ciclo
        if next_batch:
            self._pull_recursive(list(next_batch), adapter, username, password, visited)

```

--------------------------------------------------------------------------------

### Archivo: `core/templates/bootstrap.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/templates/bootstrap.py
# Rol Arquitectónico: DCC Scripting / Pre-Flight Config & Jailing
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.6.1 (Kitsu Wake Parity with Headless)
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

# =================================================================
# 1. RESOLUCIÓN DINÁMICA DE EXTENSIONES
# =================================================================
def _get_kitsu_addon_key() -> str:
    """Encuentra la clave exacta de Kitsu en el nuevo sistema de extensiones (v4.2+)."""
    for key in bpy.context.preferences.addons.keys():
        if "blender_kitsu" in key:
            return key
    
    # Búsqueda profunda si no está en las preferencias activas
    for mod in addon_utils.modules():
        if "blender_kitsu" in mod.__name__:
            return mod.__name__
            
    return "blender_kitsu" # Fallback legacy

def _get_kitsu_module():
    """Devuelve el módulo cargado en memoria de Kitsu."""
    addon_key = _get_kitsu_addon_key()
    import sys
    return sys.modules.get(addon_key)

# =================================================================
# 2. HANDLERS PERSISTENTES (Sobreviven a F8 y apertura de archivos)
# =================================================================
@bpy.app.handlers.persistent
def _apply_persistent_overrides(dummy=None):
    """
    Se ejecuta CADA VEZ que se carga un archivo .blend.
    Garantiza que el Monkey Patch y el RBAC nunca desaparezcan.
    """
    # 1. Extraer variables de entorno vitales
    project_root = os.environ.get("OPENSTUDIO_PROJECT_ROOT", "")
    prod_folder = os.environ.get("OPENSTUDIO_PRODUCTION_FOLDER", "02_archivos_de_produccion")
    user_role = os.environ.get("OPENSTUDIO_USER_ROLE", "artist").lower()
    
    kitsu_mod = _get_kitsu_module()
    
    # 2. Re-aplicar Monkey Patch del VFS
    if kitsu_mod and project_root:
        try:
            kitsu_prefs_mod = importlib.import_module(f"{kitsu_mod.__name__}.prefs")
            
            def custom_project_root_dir_get(context):
                pref_instance = kitsu_prefs_mod.addon_prefs_get(context)
                return Path(pref_instance.project_root_dir) / prod_folder
                
            kitsu_prefs_mod.project_root_dir_get = custom_project_root_dir_get

            # Parche de clase (Evita el hardcodeo del add-on)
            if hasattr(kitsu_prefs_mod, "KITSU_addon_preferences"):
                def custom_project_root_path(self):
                    return Path(self.project_root_dir) / prod_folder
                
                kitsu_prefs_mod.KITSU_addon_preferences.project_root_path = custom_project_root_path

        except Exception as e:
            print(f"[OPENSTUDIO HUB] Error en Monkey Patch: {e}")

    # 3. Re-aplicar Guardrails (Jailing RBAC)
    if user_role not in ["lead", "supervisor", "td"]:
        @classmethod
        def poll_restringido(cls, context):
            return False 
            
        if hasattr(bpy.types, "ASSETPIPE_OT_force_push"):
            bpy.types.ASSETPIPE_OT_force_push.poll = poll_restringido
            
        if hasattr(bpy.types, "OPENSTUDIO_OT_override_sanity"):
            bpy.types.OPENSTUDIO_OT_override_sanity.poll = poll_restringido

# =================================================================
# 3. SECUENCIA DE ARRANQUE INICIAL (One-Shot Timer)
# =================================================================
def _startup_sequence():
    """
    Función de un solo uso. Configura preferencias, abre el archivo,
    y establece la sesión. Retorna None para que el timer se autodestruya.
    """
    try:
        print("\n" + "="*50)
        print("[OPENSTUDIO HUB] Iniciando Secuencia de Arranque...")

        target_file = os.environ.get("OPENSTUDIO_TARGET_FILE", "")
        task_type = os.environ.get("OPENSTUDIO_TASK_TYPE", "generic").lower()
        
        kitsu_user = os.environ.get("OPENSTUDIO_KITSU_USER", "")
        kitsu_pwd = os.environ.get("OPENSTUDIO_KITSU_PWD", "")
        kitsu_host = os.environ.get("OPENSTUDIO_KITSU_HOST", "")
        project_id = os.environ.get("OPENSTUDIO_KITSU_PROJECT_ID", "")
        project_root = os.environ.get("OPENSTUDIO_PROJECT_ROOT", "")
        prod_folder = os.environ.get("OPENSTUDIO_PRODUCTION_FOLDER", "02_archivos_de_produccion")

        addon_key = _get_kitsu_addon_key()

        # =========================================================
        # NUEVO: FORZAR ACTIVACIÓN (Paridad exacta con Headless Builder)
        # =========================================================
        if addon_key not in bpy.context.preferences.addons:
            print(f"[OPENSTUDIO HUB] Despertando extensión: {addon_key}...")
            try:
                # Evitamos addon_utils.enable porque dispara un unregister() buggeado en Kitsu
                bpy.ops.preferences.addon_enable(module=addon_key)
            except Exception as e:
                print(f"[OPENSTUDIO HUB] Advertencia al activar Kitsu: {e}")
            
            # Forzamos la importación en memoria para el registro de RNA
            importlib.import_module(addon_key)
        # =========================================================
        
        # 1. Configurar Preferencias Físicas y Credenciales
        if addon_key in bpy.context.preferences.addons:
            addon_prefs = bpy.context.preferences.addons[addon_key].preferences
            
            # Enrutamiento de Kitsu
            if project_root and hasattr(addon_prefs, "project_root_dir"):
                addon_prefs.project_root_dir = project_root
            if hasattr(addon_prefs, "version_control"): addon_prefs.version_control = True
            if hasattr(addon_prefs, "shot_dir_name"): addon_prefs.shot_dir_name = "shots"
            if hasattr(addon_prefs, "asset_dir_name"): addon_prefs.asset_dir_name = "assets"
            if hasattr(addon_prefs, "seq_dir_name"): addon_prefs.seq_dir_name = "strips"
            if hasattr(addon_prefs, "edit_dir_name"): addon_prefs.edit_dir_name = "edit"
            
            # Enrutamiento de Playblasts
            vfs_root = Path(project_root) / prod_folder
            footage_dir = vfs_root / "edit" / "footage"
            if hasattr(addon_prefs, "shot_playblast_root_dir"): addon_prefs.shot_playblast_root_dir = str(footage_dir / "pro")
            if hasattr(addon_prefs, "seq_playblast_root_dir"): addon_prefs.seq_playblast_root_dir = str(footage_dir / "pre")
            if hasattr(addon_prefs, "frames_root_dir"): addon_prefs.frames_root_dir = str(footage_dir / "post")

            # Autenticación RAM
            if kitsu_user and kitsu_pwd:
                addon_prefs.host = kitsu_host
                addon_prefs.email = kitsu_user
                addon_prefs.passwd = kitsu_pwd
                try:
                    print(f"[OPENSTUDIO HUB] Autenticando Kitsu con {kitsu_user}...")
                    bpy.ops.kitsu.session_start('EXEC_DEFAULT')
                    bpy.ops.kitsu.con_productions_load('EXEC_DEFAULT')
                    if project_id:
                        kitsu_mod = _get_kitsu_module()
                        if kitsu_mod:
                            kitsu_mod.cache.project_active_set_by_id(bpy.context, project_id)
                        addon_prefs.project_active_id = project_id 
                except Exception as e:
                    print(f"[OPENSTUDIO HUB] Error al autenticar Kitsu API: {e}")
        else:
            print(f"[OPENSTUDIO HUB] ❌ ERROR: El addon {addon_key} no pudo inicializarse en las preferencias.")

        # 2. Carga del Archivo Maestro
        if target_file and os.path.exists(target_file):
            print(f"[OPENSTUDIO HUB] Cargando archivo de producción: {target_file}")
            try:
                bpy.ops.wm.open_mainfile(filepath=target_file)
                
                # Autodetección o forzado de contexto
                if hasattr(bpy.ops.kitsu, "con_detect_context"):
                    bpy.ops.kitsu.con_detect_context('EXEC_DEFAULT')
                    
                # Forzado Visual de Workspaces
                ws_map = {"edit": "Video Editing", "editorial": "Video Editing", "montaje": "Video Editing", "storyboard": "Storyboard"}
                ws_name = ws_map.get(task_type)
                if ws_name and ws_name in bpy.data.workspaces:
                    bpy.context.window.workspace = bpy.data.workspaces[ws_name]
                    
            except Exception as e:
                print(f"[OPENSTUDIO HUB] Fallo al abrir archivo: {e}")
        else:
            print(f"[OPENSTUDIO HUB] ADVERTENCIA: Archivo base inexistente en {target_file}")

        print("="*50 + "\n")
        return None # Destruye el timer para evitar ejecuciones repetidas

    except Exception as e:
        print(f"[OPENSTUDIO HUB] ❌ ERROR FATAL EN ARRANQUE: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("="*50 + "\n")
        # GARANTÍA ABSOLUTA DE DESTRUCCIÓN DEL TIMER
        return None 

# =================================================================
# 4. REGISTRO EN EL MOTOR DE BLENDER
# =================================================================
def register():
    # Registrar el hook persistente
    if _apply_persistent_overrides not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_apply_persistent_overrides)
        
    # Disparar la secuencia de arranque un instante después de que la UI respire
    bpy.app.timers.register(_startup_sequence, first_interval=0.1)

if __name__ == "__main__":
    register()

```

--------------------------------------------------------------------------------

### Archivo: `core/templates/bootstrap_old.py`

```python
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
from pathlib import Path

# =================================================================
# 1. RESOLUCIÓN DINÁMICA DE EXTENSIONES
# =================================================================
def _get_kitsu_addon_key() -> str:
    """Encuentra la clave exacta de Kitsu en el nuevo sistema de extensiones (v4.2+)."""
    for key in bpy.context.preferences.addons.keys():
        if "blender_kitsu" in key:
            return key
    return "blender_kitsu" # Fallback legacy

def _get_kitsu_module():
    """Devuelve el módulo cargado en memoria de Kitsu."""
    addon_key = _get_kitsu_addon_key()
    import sys
    return sys.modules.get(addon_key)

# =================================================================
# 2. HANDLERS PERSISTENTES (Sobreviven a F8 y apertura de archivos)
# =================================================================
@bpy.app.handlers.persistent
def _apply_persistent_overrides(dummy=None):
    """
    Se ejecuta CADA VEZ que se carga un archivo .blend.
    Garantiza que el Monkey Patch y el RBAC nunca desaparezcan.
    """
    # 1. Extraer variables de entorno vitales
    project_root = os.environ.get("OPENSTUDIO_PROJECT_ROOT", "")
    prod_folder = os.environ.get("OPENSTUDIO_PRODUCTION_FOLDER", "02_archivos_de_produccion")
    user_role = os.environ.get("OPENSTUDIO_USER_ROLE", "artist").lower()
    
    kitsu_mod = _get_kitsu_module()
    
    # 2. Re-aplicar Monkey Patch del VFS
    if kitsu_mod and project_root:
        try:
            kitsu_prefs_mod = importlib.import_module(f"{kitsu_mod.__name__}.prefs")
            
            def custom_project_root_dir_get(context):
                pref_instance = kitsu_prefs_mod.addon_prefs_get(context)
                return Path(pref_instance.project_root_dir) / prod_folder
                
            kitsu_prefs_mod.project_root_dir_get = custom_project_root_dir_get

            # Parche de clase (Evita el hardcodeo del add-on)
            if hasattr(kitsu_prefs_mod, "KITSU_addon_preferences"):
                def custom_project_root_path(self):
                    return Path(self.project_root_dir) / prod_folder
                
                kitsu_prefs_mod.KITSU_addon_preferences.project_root_path = custom_project_root_path


        except Exception as e:
            print(f"[OPENSTUDIO HUB] Error en Monkey Patch: {e}")

    # 3. Re-aplicar Guardrails (Jailing RBAC)
    if user_role not in ["lead", "supervisor", "td"]:
        @classmethod
        def poll_restringido(cls, context):
            return False 
            
        if hasattr(bpy.types, "ASSETPIPE_OT_force_push"):
            bpy.types.ASSETPIPE_OT_force_push.poll = poll_restringido
            
        if hasattr(bpy.types, "OPENSTUDIO_OT_override_sanity"):
            bpy.types.OPENSTUDIO_OT_override_sanity.poll = poll_restringido

# =================================================================
# 3. SECUENCIA DE ARRANQUE INICIAL (One-Shot Timer)
# =================================================================
def _startup_sequence():
    """
    Función de un solo uso. Configura preferencias, abre el archivo,
    y establece la sesión. Retorna None para que el timer se autodestruya.
    """
    try:

        print("\n" + "="*50)
        print("[OPENSTUDIO HUB] Iniciando Secuencia de Arranque...")

        target_file = os.environ.get("OPENSTUDIO_TARGET_FILE", "")
        task_type = os.environ.get("OPENSTUDIO_TASK_TYPE", "generic").lower()
        entity_type = os.environ.get("OPENSTUDIO_KITSU_ENTITY_TYPE", "").upper()
        
        kitsu_user = os.environ.get("OPENSTUDIO_KITSU_USER", "")
        kitsu_pwd = os.environ.get("OPENSTUDIO_KITSU_PWD", "")
        kitsu_host = os.environ.get("OPENSTUDIO_KITSU_HOST", "")
        project_id = os.environ.get("OPENSTUDIO_KITSU_PROJECT_ID", "")
        project_root = os.environ.get("OPENSTUDIO_PROJECT_ROOT", "")
        prod_folder = os.environ.get("OPENSTUDIO_PRODUCTION_FOLDER", "02_archivos_de_produccion")

        addon_key = _get_kitsu_addon_key()
        
        # 1. Configurar Preferencias Físicas y Credenciales
        if addon_key in bpy.context.preferences.addons:
            addon_prefs = bpy.context.preferences.addons[addon_key].preferences
            
            # Enrutamiento de Kitsu
            if project_root and hasattr(addon_prefs, "project_root_dir"):
                addon_prefs.project_root_dir = project_root
            if hasattr(addon_prefs, "version_control"): addon_prefs.version_control = True
            if hasattr(addon_prefs, "shot_dir_name"): addon_prefs.shot_dir_name = "shots"
            if hasattr(addon_prefs, "asset_dir_name"): addon_prefs.asset_dir_name = "assets"
            if hasattr(addon_prefs, "seq_dir_name"): addon_prefs.seq_dir_name = "strips"
            if hasattr(addon_prefs, "edit_dir_name"): addon_prefs.edit_dir_name = "edit"
            
            # Enrutamiento de Playblasts
            vfs_root = Path(project_root) / prod_folder
            footage_dir = vfs_root / "edit" / "footage"
            if hasattr(addon_prefs, "shot_playblast_root_dir"): addon_prefs.shot_playblast_root_dir = str(footage_dir / "pro")
            if hasattr(addon_prefs, "seq_playblast_root_dir"): addon_prefs.seq_playblast_root_dir = str(footage_dir / "pre")
            if hasattr(addon_prefs, "frames_root_dir"): addon_prefs.frames_root_dir = str(footage_dir / "post")

            # Autenticación RAM
            if kitsu_user and kitsu_pwd:
                addon_prefs.host = kitsu_host
                addon_prefs.email = kitsu_user
                addon_prefs.passwd = kitsu_pwd
                try:
                    bpy.ops.kitsu.session_start('EXEC_DEFAULT')
                    bpy.ops.kitsu.con_productions_load('EXEC_DEFAULT')
                    if project_id:
                        kitsu_mod = _get_kitsu_module()
                        if kitsu_mod:
                            kitsu_mod.cache.project_active_set_by_id(bpy.context, project_id)
                        addon_prefs.project_active_id = project_id 
                except Exception as e:
                    print(f"[OPENSTUDIO HUB] Error al autenticar: {e}")

        # 2. Carga del Archivo Maestro
        if target_file and os.path.exists(target_file):
            print(f"[OPENSTUDIO HUB] Cargando archivo de producción: {target_file}")
            try:
                bpy.ops.wm.open_mainfile(filepath=target_file)
                
                # Autodetección o forzado de contexto
                if hasattr(bpy.ops.kitsu, "con_detect_context"):
                    bpy.ops.kitsu.con_detect_context('EXEC_DEFAULT')
                    
                # Forzado Visual de Workspaces
                ws_map = {"edit": "Video Editing", "editorial": "Video Editing", "montaje": "Video Editing", "storyboard": "Storyboard"}
                ws_name = ws_map.get(task_type)
                if ws_name and ws_name in bpy.data.workspaces:
                    bpy.context.window.workspace = bpy.data.workspaces[ws_name]
                    
            except Exception as e:
                print(f"[OPENSTUDIO HUB] Fallo al abrir archivo: {e}")
        else:
            print(f"[OPENSTUDIO HUB] ADVERTENCIA: Archivo base inexistente en {target_file}")

        print("="*50 + "\n")
        return None # Destruye el timer para evitar ejecuciones repetidas

    except Exception as e:
        print(f"[OPENSTUDIO HUB] ❌ ERROR FATAL EN ARRANQUE: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("="*50 + "\n")
        # GARANTÍA ABSOLUTA DE DESTRUCCIÓN DEL TIMER
        return None 

# =================================================================
# 4. REGISTRO EN EL MOTOR DE BLENDER
# =================================================================
def register():
    # Registrar el hook persistente
    if _apply_persistent_overrides not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_apply_persistent_overrides)
        
    # Disparar la secuencia de arranque un instante después de que la UI respire
    bpy.app.timers.register(_startup_sequence, first_interval=0.1)

if __name__ == "__main__":
    register()

```

--------------------------------------------------------------------------------

### Archivo: `core/templates/headless_builder.py`

```python
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
import importlib
from pathlib import Path

# =================================================================
# 1. RESOLUCIÓN DINÁMICA DE EXTENSIONES (Paridad con bootstrap.py)
# =================================================================
def _get_kitsu_addon_key() -> str:
    """Encuentra la clave exacta de Kitsu en el nuevo sistema de extensiones (v4.2+)."""
    # 1. Buscar en preferencias activas
    for key in bpy.context.preferences.addons.keys():
        if "blender_kitsu" in key:
            return key
            
    # 2. Si no está activa, buscar en la lista de módulos instalados
    import addon_utils
    for mod in addon_utils.modules():
        if "blender_kitsu" in mod.__name__:
            return mod.__name__
            
    return "blender_kitsu" # Fallback legacy

def _get_kitsu_module():
    """Devuelve el módulo cargado en memoria de Kitsu."""
    addon_key = _get_kitsu_addon_key()
    return sys.modules.get(addon_key)

def despertar_kitsu_module():
    """Busca y activa el módulo usando el operador oficial de Blender asegurando inicialización RNA."""
    addon_key = _get_kitsu_addon_key()
    
    try:
        bpy.ops.preferences.addon_enable(module=addon_key)
    except Exception as e:
        print(f"[HeadlessBuilder] Advertencia al habilitar {addon_key}: {e}")
        
    # Forzar la importación a sys.modules
    importlib.import_module(addon_key)
    return sys.modules.get(addon_key), addon_key


# =================================================================
# 2. MECANISMOS DE PROTECCIÓN
# =================================================================
def inyectar_parche_proteccion_memoria():
    """
    Evita el crash de RNA desactivando la carga de archivos .blend 
    DENTRO de los operadores de Kitsu. Cargar archivos destruye 
    la instancia `self` del operador en modo Headless.
    """
    try:
        kitsu_module = _get_kitsu_module()
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
    kitsu_module = _get_kitsu_module()
    addon_key = _get_kitsu_addon_key()
    
    # 1. EXTRACCIÓN DE SALVAVIDAS (Antes de destruir la memoria de la escena)
    project_id = ""
    if kitsu_module and addon_key in bpy.context.preferences.addons:
        prefs = bpy.context.preferences.addons[addon_key].preferences
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
        # 3. REINYECCIÓN DEL MONKEY PATCH VFS
        # =======================================================
        vfs_svn = os.environ.get("OPENSTUDIO_PRODUCTION_FOLDER", "svn")
        try:
            kitsu_prefs_mod = importlib.import_module(f"{kitsu_module.__name__}.prefs")
            
            # 1. Parche a nivel de módulo (Legacy)
            def custom_root_dir_get(context):
                pref_instance = kitsu_prefs_mod.addon_prefs_get(context)
                return Path(pref_instance.project_root_dir) / vfs_svn
                
            kitsu_prefs_mod.project_root_dir_get = custom_root_dir_get
            
            # 2. NUEVO: Parche profundo a nivel de clase para eliminar 'project_files'
            if hasattr(kitsu_prefs_mod, "KITSU_addon_preferences"):
                def custom_project_root_path(self):
                    # 'self' es la instancia de preferencias. Devolvemos la ruta limpia.
                    return Path(self.project_root_dir) / vfs_svn
                
                # Inyectamos el método directamente en la clase original del add-on
                kitsu_prefs_mod.KITSU_addon_preferences.project_root_path = custom_project_root_path
                
            print(f"[HeadlessBuilder] 🛡️ Monkey patch VFS ({vfs_svn}) inyectado (Bypass 'project_files').")
        except Exception as e:
            print(f"[HeadlessBuilder] ⚠️ Advertencia: Fallo al inyectar Monkey Patch VFS: {e}")

        # =======================================================
        # 4. PARCHE DE GUARDADO SÍNCRONO (Anti-Timer)
        # =======================================================
        try:
            kitsu_file_save = kitsu_module.shot_builder.file_save
            
            def save_shot_sync(file_path: str) -> bool:
                path_obj = Path(file_path)
                if path_obj.exists(): 
                    print(f"[HeadlessBuilder] ⚠️ El archivo ya existe: {path_obj.name}")
                    return False
                    
                path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                # Guardado instantáneo, bloqueando el hilo principal hasta terminar
                bpy.ops.wm.save_mainfile(filepath=str(path_obj), relative_remap=True)
                print(f"[HeadlessBuilder] 💾 Archivo físico escrito síncronamente: {path_obj.name}")
                return True
                
            # Sobrescribimos la función original
            kitsu_file_save.save_shot_builder_file = save_shot_sync
            print("[HeadlessBuilder] ✓ Parche de guardado síncrono (Anti-Timer) inyectado exitosamente.")
        except AttributeError as attr_err:
            print(f"[HeadlessBuilder] ⚠️ No se pudo inyectar el parche Anti-Timer: {attr_err}")


# =======================================================
# 3. FUNCIÓN MAESTRA DE I/O Y AUTENTICACIÓN
# =======================================================
def autenticar_kitsu_headless(kitsu_module, mod_name):
    """
    Inyecta el Host y las credenciales (provistas por EnvLauncher a través del OS env)
    dentro del addon de Kitsu e inicia sesión de forma estricta.
    Resuelve el problema de Gazu intentando conectar a 'gazu.change.serverhost'.
    """
    hub_host = os.environ.get("OPENSTUDIO_KITSU_HOST", "http://localhost:8080/api")
    hub_user = os.environ.get("OPENSTUDIO_KITSU_USER", "")
    hub_pwd = os.environ.get("OPENSTUDIO_KITSU_PWD", "")
    project_id = os.environ.get("OPENSTUDIO_KITSU_PROJECT_ID", "")
    project_root = os.environ.get("OPENSTUDIO_PROJECT_ROOT", "")
    
    if not (hub_user and hub_pwd):
        print(f"[HeadlessBuilder] ⚠️ Advertencia: No se proporcionaron credenciales completas para {hub_host}")
        return False

    print(f"[HeadlessBuilder] 🔒 Autenticando estricto en RAM como: {hub_user} en {hub_host}")
    
    prefs = bpy.context.preferences.addons[mod_name].preferences
    prefs.host = hub_host
    prefs.email = hub_user
    prefs.passwd = hub_pwd
    
    if project_root:
        prefs.project_root_dir = project_root

    try:
        bpy.ops.kitsu.session_start('EXEC_DEFAULT')
    except Exception as e:
        print(f"[HeadlessBuilder] ❌ Error de autenticación con Kitsu API: {e}")
        return False
    
    if project_id:
        print(f"[HeadlessBuilder] ♻️ Fijando proyecto activo global (ID: {project_id})")
        kitsu_module.cache.project_active_set_by_id(bpy.context, project_id)
        prefs.project_active_id = project_id

    # Inyectar el Monkey Patch VFS Inicial
    vfs_svn = os.environ.get("OPENSTUDIO_PRODUCTION_FOLDER", "svn")
    try:
        kitsu_prefs_mod = importlib.import_module(f"{kitsu_module.__name__}.prefs")
        def custom_root_dir_get(context):
            pref_instance = kitsu_prefs_mod.addon_prefs_get(context)
            return Path(pref_instance.project_root_dir) / vfs_svn
            
        kitsu_prefs_mod.project_root_dir_get = custom_root_dir_get
    except Exception as e:
        print(f"[HeadlessBuilder] ⚠️ Advertencia: Fallo al inyectar Monkey Patch VFS inicial: {e}")

    return True


def _guardar_entidad_forjada(filepath_str: str, debug_label: str = "ENTIDAD"):
    """
    Centraliza la I/O de disco: crea los directorios padres si no existen
    y ejecuta el guardado síncrono del archivo .blend maestro.
    """
    out_path = Path(filepath_str)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Guardado manual forzado (Síncrono y bloqueante)
    bpy.ops.wm.save_mainfile(filepath=str(out_path), relative_remap=True)
    print(f"[HeadlessBuilder DEBUG] 💾 GUARDADO DE {debug_label} EXITOSO EN: {out_path}")
    return out_path


# =======================================================
# CONSTRUCTORES ESPECÍFICOS (Estrategias)
# =======================================================
def forjar_storyboard():
    print("[HeadlessBuilder] Iniciando forjado del Archivo Maestro de Storyboard...")
    inyectar_parche_proteccion_memoria()
    
    # Para consistencia y evitar sorpresas, despertamos y autenticamos
    kitsu_module, mod_name = despertar_kitsu_module()
    if kitsu_module:
        autenticar_kitsu_headless(kitsu_module, mod_name)
    
    # 1. Cargamos la plantilla nativa de Blender para Storyboard (2D Animation)
    try:
        print("[HeadlessBuilder] 🎬 Cargando plantilla nativa 'Storyboarding'...")
        cargar_plantilla_segura(app_template="Storyboarding")
    except Exception as e:
        print(f"[HeadlessBuilder] ⚠️ Plantilla Storyboarding no encontrada, usando default. Error: {e}")
        bpy.ops.wm.read_homefile()
        
    try:
        # 2. Extraer contexto inyectado por el Hub
        project_root = Path(os.environ.get("OPENSTUDIO_PROJECT_ROOT", ""))
        vfs_svn = os.environ.get("OPENSTUDIO_PRODUCTION_FOLDER", "svn")
        seq_name = os.environ.get("OPENSTUDIO_TARGET_SEQUENCE", "SQ000").lower()
        
        # 3. Construir la ruta (En la carpeta de edición, tal como lo definimos)
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
    
    # 0. DESPERTAR EL MÓDULO (Nos devuelve el módulo y su nombre oficial)
    kitsu_module, mod_name = despertar_kitsu_module()
    if not kitsu_module: return
    
    # 1. AUTENTICACIÓN CENTRALIZADA
    autenticar_kitsu_headless(kitsu_module, mod_name)

    # 2. DISPARAR LA CREACIÓN DEL EDIT
    try:
        print("[HeadlessBuilder] 🎬 Ejecutando kitsu.create_edit_file()...")
        bpy.ops.kitsu.create_edit_file(create_kitsu_edit=True, save_file=False)
        print("[HeadlessBuilder] ✓ Archivo Maestro de Edición configurado en memoria por Kitsu.")

        # 3. EXTRACCIÓN DE LA RUTA Y GUARDADO FÍSICO
        edit_entity = kitsu_module.cache.edit_default_get(episode_id=bpy.context.scene.kitsu.episode_active_id)
        filepath_str = edit_entity.get_filepath(bpy.context)
        
        _guardar_entidad_forjada(filepath_str, "EDIT MASTER")
        
    except Exception as e:
        import traceback
        print(f"[HeadlessBuilder] ❌ Fallo crítico al crear el archivo Edit: {e}")
        traceback.print_exc()


def forjar_shot():
    print("[HeadlessBuilder] Iniciando forjado de Shot (Toma)...")
    inyectar_parche_proteccion_memoria()
    
    try:
        kitsu_module, mod_name = despertar_kitsu_module()
        if not kitsu_module: return

        # 1. AUTENTICACIÓN CENTRALIZADA
        autenticar_kitsu_headless(kitsu_module, mod_name)

        # 2. EXTRAER NOMBRES DESDE LAS VARIABLES DE ENTORNO
        seq_name = os.environ.get("OPENSTUDIO_KITSU_SEQUENCE_NAME", "")
        shot_name = os.environ.get("OPENSTUDIO_KITSU_ENTITY_NAME", "")
        task_type_name = os.environ.get("OPENSTUDIO_KITSU_TASK_TYPE_NAME", "Layout")
        
        # 3. PREPARAR PLANTILLA USANDO LA TAREA
        # task_type = kitsu_module.cache.task_type_active_get()
        # if task_type:
        #     cargar_plantilla_segura(task_type_name=task_type.name)
        # else:
        #     cargar_plantilla_segura()
        # 4. INYECTAR VARIABLES EN LA ESCENA ACTUAL (SIMULANDO CLICS EN LA UI)
        if seq_name:
            print(f"[HeadlessBuilder] ♻️ Fijando Secuencia en Escena: {seq_name}")
            bpy.context.scene.kitsu.sequence_active_name = seq_name
            
        if shot_name:
            print(f"[HeadlessBuilder] ♻️ Fijando Shot en Escena: {shot_name}")
            bpy.context.scene.kitsu.shot_active_name = shot_name

        if task_type_name:
            print(f"[HeadlessBuilder] ♻️ Fijando Task Type en Escena: {task_type_name}")
            bpy.context.scene.kitsu.task_type_active_name = task_type_name 

        # 5. FORJAR EL ARCHIVO
        print("[HeadlessBuilder] 🎬 Ejecutando kitsu.build_new_shot()...")
        bpy.ops.kitsu.build_new_shot(save_file=False)
        
        # 6. EXTRACCIÓN DE LA RUTA Y GUARDADO
        task_type = kitsu_module.cache.task_type_active_get()
        shot = kitsu_module.cache.shot_active_get()
        filepath_str = shot.get_filepath(bpy.context, task_type.get_short_name() if task_type else "")
        
        out_path = _guardar_entidad_forjada(filepath_str, "SHOT")
        
        # ==========================================================
        # 7. REGISTRAR RUTA EN EL CUSTOM FIELD DE LA TAREA EN KITSU
        # ==========================================================
        try:
            import gazu
            # EXTRAEMOS LOS IDs CRUDOS (.id) DE LOS OBJETOS DE BLENDER_KITSU
            shot_id = shot.id
            tt_id = task_type.id
            
            # Usamos los IDs en formato texto para buscar en gazu
            task = gazu.task.get_task_by_entity(shot_id, tt_id)
            
            if task:
                # Calculamos la ruta relativa al VFS (Ej: pro/shots/01/010/010-layout.blend)
                vfs_root = Path(os.environ.get("OPENSTUDIO_PROJECT_ROOT", "")) / os.environ.get("OPENSTUDIO_PRODUCTION_FOLDER", "svn")
                rel_path = out_path.relative_to(vfs_root).as_posix()
                
                # Preparamos e inyectamos los datos en Kitsu
                task_data = task.get("data")
                if not task_data: 
                    task_data = {}
                    
                task_data["filepath"] = rel_path
                task["data"] = task_data
                #gazu.task.update_task(task["id"], task_data)
                gazu.task.update_task(task)
                
                print(f"[HeadlessBuilder] ✓ Metadata guardada en Kitsu Task ({task_type.name}): {rel_path}")
            else:
                print(f"[HeadlessBuilder] ⚠️ Tarea {task_type.name} no encontrada en Kitsu para actualizar metadatos.")
        except Exception as api_e:
            print(f"[HeadlessBuilder] ❌ Error actualizando la Tarea en Kitsu: {api_e}")
        # ==========================================================

    except Exception as e:
        import traceback
        print(f"[HeadlessBuilder] ❌ Fallo crítico al crear el Shot: {e}")
        traceback.print_exc()

def forjar_asset():
    print("[HeadlessBuilder] Iniciando forjado de Asset (Recurso)...")
    inyectar_parche_proteccion_memoria()
    
    try:
        kitsu_module, mod_name = despertar_kitsu_module()
        if not kitsu_module: return

        # 1. AUTENTICACIÓN CENTRALIZADA
        autenticar_kitsu_headless(kitsu_module, mod_name)

        # 2. RECUPERAR IDs DEL ENTORNO
        target_id = os.environ.get("OPENSTUDIO_TARGET_ENTITY_ID", "")
        asset_type_id = os.environ.get("OPENSTUDIO_KITSU_ASSET_TYPE_ID", "")

        # --- DEBUG TEMPORAL ---
        print(f"[DEBUG Headless] TARGET_ID recibido: '{target_id}'")
        print(f"[DEBUG Headless] ASSET_TYPE_ID recibido: '{asset_type_id}'")
        # ----------------------
        
        # 3. EXTRAER NOMBRES DIRECTAMENTE VÍA ID DE Kitsu/Gazu
        import gazu
        asset_type_name = ""
        asset_name = ""
        
        if asset_type_id:
            try:
                at_data = gazu.asset.get_asset_type(asset_type_id)
                asset_type_name = at_data.get("name", "") if at_data else ""
            except Exception as e:
                print(f"[HeadlessBuilder] Error obteniendo Asset Type: {e}")
                
        if target_id:
            try:
                asset_data = gazu.asset.get_asset(target_id)
                asset_name = asset_data.get("name", "") if asset_data else ""
            except Exception as e:
                print(f"[HeadlessBuilder] Error obteniendo Asset: {e}")

        # 4. INYECTAR VARIABLES EN LA ESCENA ACTUAL ANTES DEL OPERADOR
        if asset_type_name:
            print(f"[HeadlessBuilder] ♻️ Fijando Asset Type en Escena: {asset_type_name}")
            bpy.context.scene.kitsu.asset_type_active_name = asset_type_name
            
        if asset_name:
            print(f"[HeadlessBuilder] ♻️ Fijando Asset en Escena: {asset_name}")
            bpy.context.scene.kitsu.asset_active_name = asset_name

        # 5. FORJAR EL ARCHIVO (El operador carga la plantilla internamente)
        print("[HeadlessBuilder] 🎬 Ejecutando kitsu.build_new_asset()...")
        bpy.ops.kitsu.build_new_asset(save_file=False)
        
        # 6. EXTRACCIÓN DE LA RUTA Y GUARDADO
        asset = kitsu_module.cache.asset_active_get()
        filepath_str = asset.get_filepath(bpy.context)
        
        _guardar_entidad_forjada(filepath_str, "ASSET")
        
    except Exception as e:
        import traceback
        print(f"[HeadlessBuilder] ❌ Fallo crítico al crear el Asset: {e}")
        traceback.print_exc()

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

```

--------------------------------------------------------------------------------

### Archivo: `core/vault_manager.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/vault_manager.py
# Rol Arquitectónico: Core Service / Vault Inventory Engine & Session Bridge
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.1.0 (Environment Variables Injection)
# =========================================================================================

"""
Centralized CRUD manager for the vault_manifest.json shared inventory file.
Acts as the Single Source of Truth for software availability, templates, and addons.
Implements robust polymorphic parsing and retains transient credentials compatibility,
injecting them into the OS environment for headless subprocesses.
"""

import os
import json
from pathlib import Path

class VaultManager:
    def __init__(self, config_factory):
        """
        Inicializa el gestor de inventario inyectando dinámicamente la fábrica de configuración.
        """
        self.config_factory = config_factory
        self._cached_manifest = {}
        
        # Estado efímero de sesión (Compatibilidad con el flujo legacy de login)
        self._transient_email = None
        self._transient_password = None

    @property
    def manifest_path(self) -> Path:
        """Resuelve reactivamente la coordenada real del manifiesto en la raíz de la Bóveda."""
        return self.config_factory.get_vault_path() / "vault_manifest.json"

    def cargar_inventario(self) -> dict:
        """
        Lee, procesa y normaliza el manifiesto compartido en el NAS.
        Garantiza compatibilidad polimórfica de esquemas y auto-sembrado seguro.
        """
        self._cached_manifest = {}
        target_path = self.manifest_path

        # 1. Red de Seguridad: Auto-Sembrado si el estudio es virgen
        if not target_path.exists():
            print(f"[VAULT MANAGER] Manifest not found. Initializing seed at: {target_path}")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            esqueleto_base = {
                "5.1.2": {
                    "categories": {
                        "templates": {
                            "Macuare_Estudio_Base": {
                                "version": "1.0",
                                "description": "Plantilla oficial generada automáticamente",
                                "mandatory": True,
                                "requires": []
                            }
                        },
                        "addons": {}
                    }
                }
            }
            try:
                self.guardar_inventario(esqueleto_base)
            except Exception as e:
                print(f"[VAULT MANAGER ERROR] Critical failure during auto-seeding: {e}")

        # 2. Operación de lectura atómica y parseo elástico
        if target_path.exists():
            try:
                with open(target_path, 'r', encoding='utf-8') as f:
                    manifesto_crudo = json.load(f)
                    
                    for key, val in manifesto_crudo.items():
                        if isinstance(val, dict):
                            # Normalización polimórfica de llaves de versión
                            raw_version = val.get("blender_version") or key
                            clean_version = str(raw_version).lstrip("vV ")
                            
                            # Aislamiento elástico de bloques de categorías
                            categories_block = val.get("categories") if "categories" in val else val
                            if isinstance(categories_block, dict):
                                self._cached_manifest[clean_version] = categories_block
                                
            except Exception as e:
                print(f"[VAULT MANAGER ERROR] Failed to parse vault manifest file: {e}")
                self._cached_manifest = {}

        return self._cached_manifest

    def guardar_inventario(self, payload: dict) -> bool:
        """
        Persiste de forma atómica el estado del manifiesto en el disco compartido del NAS.
        """
        try:
            target_path = self.manifest_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[VAULT MANAGER ERROR] Failed to write manifest to disk: {e}")
            return False

    def obtener_datos_locales(self) -> dict:
        """Devuelve el caché de memoria ram actual sin forzar I/O de disco."""
        return self._cached_manifest

    # ---------------------------------------------------------
    # TRANSIENT SESSION LAYER (Backward Compatibility Patch)
    # ---------------------------------------------------------

    def save_kitsu_credentials(self, email: str, password: str):
        """Retiene de forma efímera las credenciales de red e inyecta al ambiente del OS."""
        self._transient_email = email
        self._transient_password = password
        
        # Inyectar al entorno para que los subprocesos (ProjectBuilder) puedan consumirlo
        os.environ["OPENSTUDIO_KITSU_USER"] = email
        os.environ["OPENSTUDIO_KITSU_PWD"] = password

    def clear(self):
        """Limpia los estados temporales de memoria al cerrar sesión o purgar la app."""
        self._transient_email = None
        self._transient_password = None
        self._cached_manifest = {}
        
        # Purgar el entorno por seguridad
        os.environ.pop("OPENSTUDIO_KITSU_USER", None)
        os.environ.pop("OPENSTUDIO_KITSU_PWD", None)
        
        print("[VAULT MANAGER] Transient session states successfully flushed.")

```

--------------------------------------------------------------------------------

### Archivo: `core/vcs_adapters/abstract_vcs.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/vcs_adapters/abstract_vcs.py
# Rol Arquitectónico: Adaptador VCS / Capa de Abstracción
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.4.2
# =========================================================================================

"""
Interfaz base para todos los adaptadores de Control de Versiones.
Garantiza que cualquier motor (SVN, Git) exponga los mismos métodos al Hub.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from pathlib import Path

class AbstractVCS(ABC):
    """
    Interfaz base para todos los adaptadores de Control de Versiones.
    Garantiza que cualquier motor (SVN, Git) exponga los mismos métodos al Hub.
    """
    def __init__(self, repo_url: str, workspace_dir: Path):
        self.repo_url = repo_url
        self.workspace_dir = workspace_dir

    @abstractmethod
    def full_pull(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Descarga o actualiza el repositorio completo."""
        pass

    @abstractmethod
    def sparse_pull(self, paths: List[str], username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Descarga estrictamente las rutas especificadas ignorando el resto (Jailing)."""
        pass

    @abstractmethod
    def commit(self, message: str, paths: Optional[List[str]] = None, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Sube los cambios locales al servidor."""
        pass

    @abstractmethod
    def lock(self, path: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Bloquea un archivo en el servidor para evitar conflictos."""
        pass

    @abstractmethod
    def unlock(self, path: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Libera un archivo bloqueado en el servidor."""
        pass

    @abstractmethod
    def revert(self, path: str) -> bool:
        """Revierte los cambios locales a la última versión del servidor."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, str]:
        """Devuelve el estado de los archivos locales (modificados, añadidos, etc)."""
        pass

    @abstractmethod
    def set_needs_lock(self, path: str) -> bool:
        """
        Aplica la propiedad de bloqueo estricto (ej. svn:needs-lock en SVN) a un archivo o ruta.
        Obliga a que el sistema de archivos local lo marque como Solo Lectura por defecto.
        """
        pass

    @abstractmethod
    def cleanup(self) -> bool:
        """
        Sanea la base de datos interna local del VCS para resolver bloqueos locales (local locks)
        provocados por cortes abruptos de energía, caídas de red o cierres forzados.
        """
        pass

    @abstractmethod
    def setup_ignore(self, patterns: List[str]) -> bool:
        """
        Configura las reglas nativas del motor VCS para ignorar archivos temporales.
        (Ej: Escribir un .gitignore en Git o aplicar svn:ignore en Subversion).
        """
        pass

    @abstractmethod
    def add_all(self, path: str = ".") -> bool:
        """
        Registra todos los archivos nuevos o modificados en la ruta dada, 
        preparándolos para el commit.
        """
        pass

    @abstractmethod
    def create_server_repository(self, project_name: str, vfs_svn: str) -> bool:
        """
        Crea el repositorio remoto en el servidor para el nuevo proyecto 
        e inicializa la topología base si es necesario.
        """
        pass


```

--------------------------------------------------------------------------------

### Archivo: `core/vcs_adapters/git_lfs_adapter.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/vcs_adapters/git_lfs_adapter.py
# Rol Arquitectónico: Adaptador VCS / Capa de Abstracción
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.0
# =========================================================================================

"""
Concrete adapter for Git LFS operations.
(Currently in 'NotImplemented' state preparing for future support).
Anchored to English standard.
"""

from typing import List, Dict, Optional
from pathlib import Path
from .abstract_vcs import AbstractVCS

class GitLFSAdapter(AbstractVCS):
    """
    Concrete adapter for Git LFS operations.
    (Currently in 'NotImplemented' state preparing for future support).
    """

    def full_pull(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        raise NotImplementedError("Git LFS support is currently under development.")

    def sparse_pull(self, paths: List[str], username: Optional[str] = None, password: Optional[str] = None) -> bool:
        # According to SDD 3.3: git clone --filter=blob:none --sparse
        raise NotImplementedError("Git LFS support is currently under development.")

    def commit(self, message: str, paths: Optional[List[str]] = None, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        raise NotImplementedError("Git LFS support is currently under development.")

    def lock(self, path: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        raise NotImplementedError("Git LFS support is currently under development.")

    def unlock(self, path: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        raise NotImplementedError("Git LFS support is currently under development.")

    def revert(self, path: str) -> bool:
        raise NotImplementedError("Git LFS support is currently under development.")

    def get_status(self) -> Dict[str, str]:
        raise NotImplementedError("Git LFS support is currently under development.")

    def set_needs_lock(self, path: str) -> bool:
        raise NotImplementedError("Git LFS support is currently under development.")

    def cleanup(self) -> bool:
        raise NotImplementedError("Git LFS support is currently under development.")

```

--------------------------------------------------------------------------------

### Archivo: `core/vcs_adapters/svn_adapter.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/vcs_adapters/svn_adapter.py
# Rol Arquitectónico: Adaptador VCS / Capa de Abstracción
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.0
# =========================================================================================

"""
Concrete adapter for Subversion (SVN) operations via CLI.
Implements the Sparse Checkout mechanism to orchestrate Vendor Jailing.
Anchored to English standard.
"""

import subprocess
from typing import List, Dict, Optional
from pathlib import Path
from .abstract_vcs import AbstractVCS

class SVNAdapter(AbstractVCS):
    """Concrete adapter for Subversion (SVN) operations via CLI."""

    def _build_auth_args(self, username: Optional[str], password: Optional[str]) -> List[str]:
        """Builds authentication arguments without caching them on disk."""
        args = ["--non-interactive", "--trust-server-cert"]

        # =========================================================
        # BYPASS TEMPORAL: Forzar credenciales Dummy en Localhost
        # =========================================================
        if "localhost" in self.repo_url:
            username = "admin"
            password = "admin123"
            print("[SVNAdapter] BYPASS: Inyectando credenciales locales de SVN (admin)...")
        # =========================================================

        if username and password:
            args.extend(["--username", username, "--password", password, "--no-auth-cache"])
        return args

    def _run_subprocess(self, cmd: List[str], cwd: Optional[Path] = None) -> str:
        """Secure wrapper to execute subprocesses and capture errors."""
        cwd_path = str(cwd) if cwd else None
        
        # === DEBUG MODE: Security mask to avoid printing the password in the console ===
        safe_cmd = []
        skip_next = False
        for token in cmd:
            if skip_next:
                safe_cmd.append("********")
                skip_next = False
            elif token == "--password":
                safe_cmd.append(token)
                skip_next = True
            else:
                safe_cmd.append(token)
                
        print(f"\n[SVN DEBUG] Executing (CWD: {cwd_path or 'Current'}):")
        print(f" -> {' '.join(safe_cmd)}")
        # ==============================================================================

        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd_path, 
                check=True, 
                capture_output=True, 
                text=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            # Captures the real stderr from SVN (e.g., Incorrect Password) to pass it to the UI/Console
            error_msg = e.stderr.strip() if e.stderr else str(e)
            print(f"[SVN FATAL ERROR] Code {e.returncode}: {error_msg}\n")
            raise RuntimeError(f"SVN Failure: {error_msg}")

    def full_pull(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        # If the folder already exists and is an SVN repo, perform an update
        if (self.workspace_dir / ".svn").exists():
            cmd = ["svn", "update"]
            cmd.extend(self._build_auth_args(username, password))
            self._run_subprocess(cmd, cwd=self.workspace_dir)
        else:
            # Otherwise, perform a full checkout
            cmd = ["svn", "checkout", self.repo_url, str(self.workspace_dir)]
            cmd.extend(self._build_auth_args(username, password))
            self._run_subprocess(cmd)
        return True

    def sparse_pull(self, paths: List[str], username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """Restrictive download (Jailing) for Vendors."""
        # 1. Empty checkout (Fetches only structure, no files)
        if not (self.workspace_dir / ".svn").exists():
            cmd_co = ["svn", "checkout", "--depth", "empty", self.repo_url, str(self.workspace_dir)]
            cmd_co.extend(self._build_auth_args(username, password))
            self._run_subprocess(cmd_co)
        
        # 2. Download only the approved directories in the paths list
        for path in paths:
            # FIX: Added the --parents flag to build the mandatory empty hierarchy
            cmd_up = ["svn", "update", "--set-depth", "infinity", "--parents", path]
            cmd_up.extend(self._build_auth_args(username, password))
            self._run_subprocess(cmd_up, cwd=self.workspace_dir)
            
        return True

    def commit(self, message: str, paths: Optional[List[str]] = None, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        cmd = ["svn", "commit", "-m", message]
        if paths:
            cmd.extend(paths)
        cmd.extend(self._build_auth_args(username, password))
        self._run_subprocess(cmd, cwd=self.workspace_dir)
        return True

    def lock(self, path: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        cmd = ["svn", "lock", path]
        cmd.extend(self._build_auth_args(username, password))
        self._run_subprocess(cmd, cwd=self.workspace_dir)
        return True

    def unlock(self, path: str, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        cmd = ["svn", "unlock", path]
        cmd.extend(self._build_auth_args(username, password))
        self._run_subprocess(cmd, cwd=self.workspace_dir)
        return True

    def revert(self, path: str) -> bool:
        cmd = ["svn", "revert", "-R", path]
        self._run_subprocess(cmd, cwd=self.workspace_dir)
        return True

    def get_status(self) -> Dict[str, str]:
        cmd = ["svn", "status"]
        output = self._run_subprocess(cmd, cwd=self.workspace_dir)
        # Raw parsing to return dict: {'A': 'path/file.blend', 'M': 'path/other.blend'}
        status_dict = {}
        for line in output.splitlines():
            if len(line) > 8:
                state = line[0]
                file_path = line[8:].strip()
                status_dict[file_path] = state
        return status_dict

    def set_needs_lock(self, path: str) -> bool:
        """
        Applies the svn:needs-lock property to the specified file.
        Forces the VCS to keep the file in 'Read-Only' mode until an authorized user locks it.
        """
        cmd = ["svn", "propset", "svn:needs-lock", "*", path]
        self._run_subprocess(cmd, cwd=self.workspace_dir)
        return True

    def cleanup(self) -> bool:
        """
        Sanitizes the local internal VCS database to resolve local locks
        caused by abrupt power outages, network drops, or forced closures.
        """
        if self.workspace_dir.exists():
            cmd = ["svn", "cleanup"]
            self._run_subprocess(cmd, cwd=self.workspace_dir)
            return True
        return False

    def setup_ignore(self, patterns: List[str]) -> bool:
        """Aplica la propiedad svn:ignore sobre la raíz del workspace."""
        if not (self.workspace_dir / ".svn").exists():
            return False
            
        # Escribimos un archivo temporal con los patrones
        ignore_file = self.workspace_dir / ".svn_ignore_temp"
        with open(ignore_file, "w", encoding="utf-8") as f:
            f.write("\n".join(patterns) + "\n")
        
        # Aplicamos la propiedad de SVN leyendo el archivo
        cmd = ["svn", "propset", "svn:ignore", "-F", str(ignore_file), "."]
        self._run_subprocess(cmd, cwd=self.workspace_dir)
        
        # Limpieza del temporal
        ignore_file.unlink(missing_ok=True)
        return True

    def add_all(self, path: str = ".") -> bool:
        """Registra archivos forzando la recursividad, ignorando los no-versionados por regla."""
        cmd = ["svn", "add", "--force", path]
        self._run_subprocess(cmd, cwd=self.workspace_dir)
        return True

    def create_server_repository(self, project_name: str, vfs_svn: str) -> bool:
        """Crea el repositorio SVN en el servidor (Soporta Docker local para desarrollo)."""
        if "localhost" not in self.repo_url:
            # Hay que implementar la creación del repositorio en servers remotos con SSH.
            print("[SVNAdapter] Repositorio remoto detectado. Asumiendo que el repo ya existe en el servidor.")
            return True # Si es un server real, asumimos que el admin ya creó el repo o se hace vía API
            
        try:
            import subprocess
            # Creación del repositorio en el contenedor Docker
            subprocess.run(["docker", "exec", "openstudio_local_svn", "svnadmin", "create", f"/home/svn/{project_name}"], check=True, capture_output=True)
            
            # Configuración de permisos
            conf_cmd = (
                f"echo '[general]' > /home/svn/{project_name}/conf/svnserve.conf && "
                f"echo 'anon-access = none' >> /home/svn/{project_name}/conf/svnserve.conf && "
                f"echo 'auth-access = write' >> /home/svn/{project_name}/conf/svnserve.conf && "
                f"echo 'password-db = passwd' >> /home/svn/{project_name}/conf/svnserve.conf"
            )
            subprocess.run(["docker", "exec", "openstudio_local_svn", "sh", "-c", conf_cmd], check=True, capture_output=True)
            
            # Creación del usuario admin default para localhost
            pwd_cmd = f"echo '[users]' > /home/svn/{project_name}/conf/passwd && echo 'admin = admin123' >> /home/svn/{project_name}/conf/passwd"
            subprocess.run(["docker", "exec", "openstudio_local_svn", "sh", "-c", pwd_cmd], check=True, capture_output=True)
            
            # Inyección de la topología VFS base
            mkdir_cmd = f"svn mkdir file:///home/svn/{project_name}/{vfs_svn} -m 'Init Hub Topology'"
            subprocess.run(["docker", "exec", "openstudio_local_svn", "sh", "-c", mkdir_cmd], check=True, capture_output=True)
            
            print(f"[SVNAdapter] ✓ Repositorio local '{project_name}' creado en Docker exitosamente.")
            return True
        except Exception as e:
            print(f"[SVNAdapter] WARNING: Fallo en la configuración del SVN Docker: {e}")
            return False

```

--------------------------------------------------------------------------------

### Archivo: `core/vcs_router.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/vcs_router.py
# Rol Arquitectónico: VCS Layer Router / Factory
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.8.0
# =========================================================================================

"""
Main router for the VCS layer. Instantiates and returns the correct adapter
based on the configuration extracted from the ConfigFactory.
Anchored to English standard.
"""

from pathlib import Path
from .vcs_adapters.abstract_vcs import AbstractVCS
from .vcs_adapters.svn_adapter import SVNAdapter
from .vcs_adapters.git_lfs_adapter import GitLFSAdapter

class VCSRouter:
    """
    Main router for the VCS layer. Instantiates and returns the correct adapter
    based on the configuration extracted from the ConfigFactory.
    """
    def __init__(self, vcs_type: str, repo_url: str, workspace_dir: Path):
        self.vcs_type = vcs_type.lower()
        self.repo_url = repo_url
        self.workspace_dir = workspace_dir
        self._ensure_workspace()

    def _ensure_workspace(self):
        """Ensures the destination folder exists before operating."""
        if not self.workspace_dir.exists():
            self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def get_adapter(self) -> AbstractVCS:
        """
        Returns the instance of the concrete adapter to use.
        """
        if self.vcs_type == "svn":
            return SVNAdapter(self.repo_url, self.workspace_dir)
        elif self.vcs_type == "git-lfs":
            return GitLFSAdapter(self.repo_url, self.workspace_dir)
        else:
            raise ValueError(f"Unsupported or unknown VCS engine: '{self.vcs_type}'")

```

--------------------------------------------------------------------------------

### Archivo: `core/watchtower_launcher.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/watchtower_launcher.py
# Rol Arquitectónico: Subprocess Orchestrator / Ephemeral Web Server
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.6.5
# =========================================================================================

"""
Orquestador encargado de la integración de Watchtower (Visualización de Producción).
Extrae datos desde Kitsu, compila el cliente web mediante watchtower-pipeline 
y sirve los archivos JSON generados a través de un servidor HTTP local efímero 
en el navegador predeterminado del usuario.
"""

import os
import sys
import time
import socket
import threading
import subprocess
#import webbrowser
import http.server
import socketserver
from pathlib import Path

from PySide6.QtCore import QObject, Signal

class WatchtowerLauncher(QObject):

    server_ready = Signal(str)

    def __init__(self, project_root: Path, kitsu_host: str, kitsu_user: str, kitsu_pwd: str, status_callback, config_factory):
        super().__init__()
        self.project_root = project_root
        self.kitsu_host = kitsu_host
        self.kitsu_user = kitsu_user
        self.kitsu_pwd = kitsu_pwd
        self.status_callback = status_callback
        self.config_factory = config_factory
        
        self.server_thread = None
        self.httpd = None

    def launch(self):
        """Inicia la extracción y el servidor en un hilo secundario."""
        threading.Thread(target=self._run_pipeline_and_serve, daemon=True).start()

    def _get_free_port(self) -> int:
        """Encuentra un puerto libre en el sistema operativo para evitar colisiones."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def _run_pipeline_and_serve(self):
        # 1. Preparar directorio de trabajo aislado
        vfs_local = self.config_factory.get_vfs_local_name()
        wt_dir = self.project_root / vfs_local / "watchtower_build"
        wt_dir.mkdir(parents=True, exist_ok=True)

        self.status_callback("Watchtower: Extrayendo datos desde la API de Kitsu...", "yellow")

        # 2. Inyectar Credenciales JIT (Zero-Disk) en el subproceso
        env_file_path = wt_dir / ".env.local"
        env_content=(
                f"KITSU_DATA_SOURCE_URL={self.kitsu_host}/api\n"
                f"KITSU_DATA_SOURCE_USER_EMAIL={self.kitsu_user}\n"
                f"KITSU_DATA_SOURCE_USER_PASSWORD={self.kitsu_pwd}\n"
        )

        #breakpoint()
        # 3. Ejecutar el compilador (watchtower_pipeline.kitsu -b)
        try:
            with open(env_file_path, "w", encoding="utf-8") as f:
                f.write(env_content)
            cmd = [sys.executable, "-m", "watchtower_pipeline.kitsu", "-b"]
            # Redirigimos el CWD al directorio temporal
            result = subprocess.run(cmd, cwd=str(wt_dir), capture_output=True, text=True)

            if env_file_path.exists():
                env_file_path.unlink()

            if result.returncode != 0:
                self.status_callback("Watchtower: Error al procesar datos de Kitsu.", "red")
                #print(f"[WATCHTOWER ERROR]\n{result.stderr}")
                print("[WATCHTOWER ERROR DETALLADO]")
                print(f"--- STDOUT ---\n{result.stdout}")
                print(f"--- STDERR ---\n{result.stderr}")
                print("----------------------------")
                return

            self.status_callback("Watchtower: Datos procesados. Iniciando servidor local...", "yellow")

            # 4. Iniciar el servidor local apuntando al bundle generado
            serve_dir = wt_dir / "watchtower"
            if not serve_dir.exists():
                serve_dir = wt_dir # Fallback en caso de que la API de watchtower cambie

            self._start_ephemeral_server(serve_dir)

        except Exception as e:
            self.status_callback(f"Watchtower: Fallo crítico en subproceso: {e}", "red")

    def _start_ephemeral_server(self, serve_dir: Path):
        """Levanta un SimpleHTTPRequestHandler y abre el navegador del OS."""
        if self.httpd:
            self.status_callback("Watchtower ya se encuentra en ejecución.", "green")
            self.server_ready.emit(f"http://localhost:{self.httpd.server_address[1]}")
            return 

        port = self._get_free_port()
        
        # Redirigir la ruta al directorio estático
        os.chdir(str(serve_dir))
        
        #Handler = http.server.SimpleHTTPRequestHandler
        try:
            from RangeHTTPServer import RangeRequestHandler as Handler
        except ImportError:
            self.status_callback("Watchtower: RangeHTTPServer no instalado. El video fallará.", "red")
            Handler = http.server.SimpleHTTPRequestHandler

        class DualStackServer(socketserver.ThreadingTCPServer):
            allow_reuse_address = True

        try:
            self.httpd = DualStackServer(("", port), Handler)
            
            # Lanzamos el servidor de forma asíncrona
            self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.server_thread.start()

            self.status_callback(f"Watchtower activo en puerto {port}", "green")
            
            # Damos un pequeño respiro al socket antes de abrir el navegador
            time.sleep(1.0)
            #webbrowser.open(f"http://localhost:{port}")
            self.server_ready.emit(f"http://localhost:{port}")

        except OSError as e:
            self.status_callback(f"Watchtower: Fallo al enlazar el servidor local: {e}", "red")

```

--------------------------------------------------------------------------------

### Archivo: `openstudio_hub.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: openstudio_hub.py
# Rol Arquitectónico: Main App Root / Orquestador Inicial (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.8.0
# =========================================================================================

"""
Punto de entrada principal de OpenStudio Hub.
Inicializa el entorno gráfico nativo en Qt (PySide6), lee la configuración maestra B2B,
gestiona el enrutamiento base (Login vs Dashboard) e implementa el guardián de procesos.
Optimizado para Cero-Latencia en el arranque del Dashboard y enrutamiento PM.
"""

from _version import __version__

import sys
from pathlib import Path
import urllib.parse

# --- PySide6 (Motor Gráfico) ---
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QStackedWidget
from ui.web_context_view import WebContextView
from PySide6.QtCore import QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices

# --- CORE (Motores) ---
#from core import vault_manager
from core.auth_manager import AuthManager
from core.vault_manager import VaultManager
from core.config_factory import ConfigFactory
from core.watchtower_launcher import WatchtowerLauncher
from core.kitsu_manager import KitsuManager

# --- UI (Vistas) ---
from ui.view_login import ViewLogin
from ui.view_artist import ViewArtist
from ui.view_td import ViewTD
from ui.view_pm import ViewPM


class OpenStudioHub(QMainWindow):
    def __init__(self):
        super().__init__()

        # Título base (Se sobrescribe dinámicamente tras el login)
        self.setWindowTitle(f"OpenStudioHub - v{__version__}")
        self.resize(1000, 700) 
        self.setMinimumSize(800, 600)

        # Guardián de Procesos (Protección de Lock Passing)
        self.blender_instances = 0

        # 1. Inicializar los Motores Base
        self.auth = AuthManager()
        settings_path = Path("settings.json")
        self.config_factory = ConfigFactory(settings_path)
        self.vault = VaultManager(self.config_factory)
        

        # 2. Enrutador Inicial (State Machine MVC)
        self.mostrar_login()

    def registrar_instancia(self, activa: bool):
        """Incrementa o decrementa el contador de instancias de Blender activas."""
        if activa:
            self.blender_instances += 1
        else:
            self.blender_instances = max(0, self.blender_instances - 1)

    def closeEvent(self, event: QCloseEvent):
        """Intercepta el cierre de la ventana nativa de Qt para proteger la integridad del SVN."""
        if self.blender_instances > 0:
            mensaje = self.tr(
                "You have {0} 3D environment session(s) open.\n\n"
                "Please close the program first to release the master files on the server (SVN Unlock) "
                "and avoid production corruption."
            ).format(self.blender_instances)
            
            QMessageBox.warning(
                self,
                self.tr("Blocked Operation"),
                mensaje
            )
            event.ignore() 
        else:
            self.auth.logout()
            self.vault.clear()
            event.accept()

    def mostrar_login(self):
        """Monta la vista de Login en el contenedor central."""
        self.setWindowTitle(f"OpenStudio Hub - v{__version__}")
        
        vista_login = ViewLogin(
            parent=self, 
            auth_manager=self.auth, 
            vault_manager=self.vault, 
            config_factory=self.config_factory,
            on_login_success=self.mostrar_dashboard
        )
        self.setCentralWidget(vista_login)

    def mostrar_dashboard(self):
        """Monta el Dashboard inyectando el contexto B2B local (Cero Latencia)."""
        # Leemos el nombre del estudio directamente de la configuración local (SSoT)
        studio_name = self.config_factory.get_studio_name()
        if not studio_name:
            studio_name = "OpenStudio"
            
        self.setWindowTitle(f"{studio_name} Hub - v{__version__}")
        
        # Enrutamiento de Vistas (Factory)
        rol = self.auth.get_user_role()
        posicion = self.auth.get_user_position()

        nas_dir = self.config_factory.get_workspace_root()
        
        if rol in ["td"]:
            self.vista_actual = ViewTD(
                parent=self, 
                auth_manager=self.auth, 
                nas_dir=nas_dir, 
                vault_manager=self.vault,
                config_factory=self.config_factory,
                on_logout=self.ejecutar_logout
            )
        elif rol in ["manager"]:
            # Función anónima para mapear el status_callback a la barra de estado de QMainWindow

            if "lead" in posicion:
                # EL INFILTRADO: Es un Manager en Kitsu, pero Artista (Editor) en el Hub
                print("[OpenStudio Hub] Perfil Híbrido Detectado: Editor (Manager+Lead). Enrutando a ViewArtist.")
                self.vista_actual = ViewArtist(
                    self,
                    self.auth,
                    nas_dir,
                    self.vault,
                    self.config_factory,
                    self.ejecutar_logout)
            else:
                # El Production Manager real
                self.vista_actual = ViewPM(
                    parent=self,
                    auth_manager=self.auth,
                    config_factory=self.config_factory,
                    vault_manager=self.vault,
                    on_logout=self.ejecutar_logout
                )
        else:
            self.vista_actual = ViewArtist(
                parent=self, 
                auth_manager=self.auth, 
                nas_dir=nas_dir,
                vault_manager=self.vault,
                config_factory=self.config_factory,
                on_logout=self.ejecutar_logout
            )

        # 2. NUEVO: Implementamos el Sistema de Capas (Stack)
        self.view_stack = QStackedWidget()
        
        # Capa 0: El Dashboard 
        self.view_stack.addWidget(self.vista_actual)
        
        # Capa 1: El Contexto Web (Kitsu/Watchtower)
        self.web_context = WebContextView(self)
        self.web_context.back_requested.connect(self.cerrar_kitsu)
        self.view_stack.addWidget(self.web_context)
        
        self.setCentralWidget(self.view_stack)

    def abrir_kitsu(self, target_url: str = None):
        """Extrae la URL de Kitsu, limpia el sufijo /api y cambia la capa visual."""
        # Obtenemos la URL (ej: "http://localhost:8080" o "http://localhost:8080/api")
        kitsu_url = self.config_factory.get_kitsu_api_url()
        
        # Limpiamos /api porque queremos cargar la Interfaz Gráfica, no el endpoint crudo
        if kitsu_url.endswith("/api"):
            kitsu_url = kitsu_url[:-4]
        
        if not target_url:
            target_url = f"{kitsu_url}/news-feed"

        if False: # hay que solucionar el SSO primero
            # Parseamos el host para inyectarlo en la lista blanca de seguridad (Whitelisting de enlaces)
            parsed_url = urllib.parse.urlparse(kitsu_url)
            allowed_hosts = [parsed_url.hostname, "localhost", "127.0.0.1"]

            token = self.auth.get_current_token()
            
            # Cargamos el navegador y cambiamos la vista
            self.web_context.load_context(target_url, "Kitsu", allowed_hosts, sso_token=token)
            self.view_stack.setCurrentWidget(self.web_context)
            
        else:
            QDesktopServices.openUrl(QUrl(target_url))

    def cerrar_kitsu(self):
        """Regresa al Dashboard nativo (Capa 0) y gatilla un refresco de datos."""
        self.view_stack.setCurrentWidget(self.vista_actual)
        
        # Aquí más adelante podemos hacer que dispare una señal para que 
        # el ActivityCard o el PM Dashboard recarguen los datos recientes.
        print("[OpenStudio Hub] Regreso de Kitsu completado.")

    def abrir_watchtower(self, project_root_path: Path, project_id: str = ""):
        """Inicializa el servidor local de Watchtower y enruta la vista."""

        # --- VERIFICACIÓN DE VIDEO DE EDICIÓN ---
        if project_id:
            kitsu_mgr = KitsuManager()
            if not kitsu_mgr.check_edit_preview_exists(project_id):
                QMessageBox.warning(
                    self, 
                    "Edición No Renderizada", 
                    "No hay un video renderizado para el Edit en Kitsu.\n\n"
                    "Watchtower requiere el archivo de edición principal para funcionar.\n"
                    "Por favor, renderiza y haz Push del Master Edit desde Blender antes de abrir Watchtower."
                )
                return
        # ----------------------------------------

        # Extraemos las credenciales guardadas en la bóveda
        kitsu_url = self.config_factory.get_kitsu_api_url()
        kitsu_user = getattr(self.vault, '_transient_email', "")
        kitsu_pwd = getattr(self.vault, '_transient_password', "")

        #breakpoint()

        # Instanciamos el launcher
        self.wt_launcher = WatchtowerLauncher(
            project_root_path,
            kitsu_url,
            kitsu_user,
            kitsu_pwd,
            lambda msg, color: print(f"[Watchtower] {msg}"),
            self.config_factory
        )
        
        # Conectamos la señal que emite la URL
        self.wt_launcher.server_ready.connect(self._on_watchtower_ready)
        self.wt_launcher.launch()

    def _on_watchtower_ready(self, url: str):
        """Recibe la URL del servidor local y cambia la capa visual."""
        # Como no enviamos el parámetro sso_token, la vista actuará como un navegador normal
        self.web_context.load_context(url, "Watchtower", ["localhost", "127.0.0.1"])
        self.view_stack.setCurrentWidget(self.web_context)

    def ejecutar_logout(self):
        """Limpia el estado global de Qt y revierte al formulario de acceso."""
        if self.blender_instances > 0:
            self.close() 
            return
            
        self.auth.logout()
        self.vault.clear()  
        self.mostrar_login()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # ---------------------------------------------------------
    # INYECCIÓN GLOBAL DE ESTILOS (QSS)
    # ---------------------------------------------------------
    theme_path = Path("macuare_theme.qss")
    if theme_path.exists():
        try:
            with open(theme_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
            print("[OPENSTUDIO HUB] ✓ Corporate QSS theme loaded successfully.")
        except Exception as e:
            print(f"[OPENSTUDIO HUB] ❌ Error reading QSS file: {e}")
    else:
        print("[OPENSTUDIO HUB] ⚠️ WARNING: 'macuare_theme.qss' not found. Starting with OS native theme.")
        
    window = OpenStudioHub()
    window.show()
    sys.exit(app.exec())

```

--------------------------------------------------------------------------------

### Archivo: `tests/__init__.py`

```python

```

--------------------------------------------------------------------------------

### Archivo: `tests/dev_tools/audit_kitsu_structure.py`

```python
import gazu
import getpass
import sys

def main():
    print("==================================================")
    print("🔍 Kitsu Structural Audit Tool - OpenStudio Hub")
    print("==================================================")
    
    # 1. Autenticación
    host_url = input("URL de Kitsu (ej. https://proyectos.macuare.com.ve/api): ").strip()
    if not host_url.endswith("/api"):
        host_url = f"{host_url.rstrip('/')}/api"
        
    email = input("Email de Admin: ").strip()
    password = getpass.getpass("Contraseña: ")
    
    print("\n[+] Conectando a la API...")
    gazu.client.set_host(host_url)
    
    try:
        gazu.log_in(email, password)
        print("[+] Login exitoso.\n")
    except Exception as e:
        print(f"[-] Error de conexión: {e}")
        sys.exit(1)

    print("==================================================")
    print("RADIOGRAFÍA DEL ESTUDIO")
    print("==================================================")

    # 2. Volcado de Departamentos
    print("\n--- 1. DEPARTAMENTOS ---")
    departments = gazu.task.all_departments()
    for dept in departments:
        print(f"  • {dept['name']}")

    # 3. Volcado de Tipos de Tareas (Task Types)
    print("\n--- 2. TIPOS DE TAREAS (Task Types) ---")
    task_types = gazu.task.all_task_types()
    # Agrupamos por entidad para mayor claridad
    tt_by_entity = {}
    for tt in task_types:
        entity = tt.get('for_entity', 'Desconocido')
        if entity not in tt_by_entity:
            tt_by_entity[entity] = []
        tt_by_entity[entity].append(tt['name'])
        
    for entity, names in tt_by_entity.items():
        print(f"\n  [{entity}]")
        for name in names:
            print(f"    • {name}")

    # 4. Volcado de Tipos de Assets (Asset Types)
    print("\n--- 3. TIPOS DE ASSETS (Asset Types) ---")
    asset_types = gazu.asset.all_asset_types()
    for at in asset_types:
        print(f"  • {at['name']}")

    # 5. Volcado de Proyectos Activos
    print("\n--- 4. PROYECTOS ---")
    projects = gazu.project.all_projects()
    if not projects:
        print("  (No hay proyectos creados)")
    for p in projects:
        status = p.get('project_status_name', 'Activo')
        print(f"  • {p['name']} [{status}]")

    print("\n==================================================")
    print("✅ Auditoría completada.")
    print("==================================================")

if __name__ == "__main__":
    main()

```

--------------------------------------------------------------------------------

### Archivo: `tests/dev_tools/seed_kitsu_data.py`

```python
import gazu
import getpass
import sys
import json
from pathlib import Path

# Definimos la ruta del archivo de configuración relativo a este script
CONFIG_FILE = Path(__file__).parent / "kitsu_test_env.json"

def get_credentials():
    """Carga las credenciales desde el JSON o las pide al usuario y las guarda."""
    if CONFIG_FILE.exists():
        print(f"[+] Cargando credenciales cacheadas desde {CONFIG_FILE.name}...")
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("[-] Error: El archivo de configuración está corrupto. Borrándolo...")
            CONFIG_FILE.unlink()
            
    print("[!] Primer inicio detectado. Configura tu entorno de pruebas:")
    host_url = input("URL de Kitsu (ej. https://proyectos.macuare.com.ve/api): ").strip()
    if not host_url.endswith("/api"):
        host_url = f"{host_url.rstrip('/')}/api"
        
    email = input("Email de Admin: ").strip()
    password = getpass.getpass("Contraseña: ")
    
    config_data = {
        "host_url": host_url,
        "email": email,
        "password": password
    }
    
    # Guardamos para el futuro
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)
    print(f"[+] Credenciales guardadas exitosamente en {CONFIG_FILE.name}\n")
    
    return config_data

def main():
    print("==================================================")
    print("🌱 Kitsu Seed Data Generator - RAW API Edition")
    print("==================================================")
    
    # 1. Recolección de credenciales automatizada
    creds = get_credentials()
    
    print("[+] Conectando a la API...")
    gazu.client.set_host(creds["host_url"])
    
    try:
        gazu.log_in(creds["email"], creds["password"])
        print("[+] Login exitoso.")
    except Exception as e:
        print(f"[-] Error de red/credenciales: {e}")
        # Si la clave cambió, borramos el caché para que pregunte de nuevo la próxima vez
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
            print("[!] Archivo de caché purgado. Vuelve a ejecutar el script.")
        sys.exit(1)

    # 2. Creación del Proyecto
    project_name = "p0004-hub-test"
    print(f"\n[+] Buscando/Creando Proyecto: {project_name}")
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        project = gazu.project.new_project(project_name)
        print(f"    -> Proyecto '{project_name}' creado.")
    else:
        print(f"    -> Proyecto '{project_name}' ya existe.")

    # 3. Creación de Tipología y Asset
    print("\n[+] Configurando Assets...")
    asset_type = gazu.asset.get_asset_type_by_name("Character")
    if not asset_type:
        asset_type = gazu.asset.new_asset_type("Character")
        
    asset_name = "Prota"
    asset = gazu.asset.get_asset_by_name(project, asset_name)
    if not asset:
        asset = gazu.asset.new_asset(project, asset_type, asset_name)
        print(f"    -> Asset '{asset_name}' (Character) creado.")
    else:
        print(f"    -> Asset '{asset_name}' ya existe.")

    # 4. Creación de Secuencia y Shots
    print("\n[+] Configurando Shots...")
    seq_name = "sq01"
    sequence = gazu.shot.get_sequence_by_name(project, seq_name)
    if not sequence:
        sequence = gazu.shot.new_sequence(project, seq_name)
        print(f"    -> Secuencia '{seq_name}' creada.")
        
    shots = ["sh010", "sh020"]
    for shot_name in shots:
        shot = gazu.shot.get_shot_by_name(sequence, shot_name)
        if not shot:
            gazu.shot.new_shot(project, sequence, shot_name)
            print(f"    -> Shot '{shot_name}' creado en '{seq_name}'.")
        else:
            print(f"    -> Shot '{shot_name}' ya existe.")

    # 5. Creación de Usuarios Dummy (RBAC)
    print("\n[+] Configurando Usuarios Dummy (Contraseña por defecto: openstudio123)...")
    dummy_users = [
        {"first_name": "Test", "last_name": "Vendor", "email": "vendor@dummy.com", "role": "user", "title": "Vendor"},
        {"first_name": "Test", "last_name": "Artist", "email": "artist@dummy.com", "role": "user", "title": "Artist"},
    ]
    
    created_users = {}
    for du in dummy_users:
        user = gazu.person.get_person_by_email(du["email"])
        if not user:
            try:
                user = gazu.person.new_person(
                    first_name=du["first_name"],
                    last_name=du["last_name"],
                    email=du["email"],
                    role=du["role"],
                    password="openstudio123"
                )
                print(f"    -> Usuario '{du['email']}' ({du['title']}) creado.")
            except Exception as e:
                print(f"    -> Advertencia: No se pudo crear el usuario {du['email']}. Detalle: {e}")
        else:
            print(f"    -> Usuario '{du['email']}' ya existe.")
        if user:
            created_users[du["title"]] = user

    # 6. Búsqueda Segura de Tipos de Tarea (Vía RAW API)
    print("\n[+] Buscando Tipos de Tarea compatibles vía RAW API...")
    try:
        raw_task_types = gazu.client.get("data/task-types")
        
        shot_task_type = None
        asset_task_type = None
        
        for tt in raw_task_types:
            if tt.get("for_entity") == "Shot" and not shot_task_type:
                shot_task_type = tt
            elif tt.get("for_entity") == "Asset" and tt.get("name") == "Rigging":
                asset_task_type = tt
                
        if not asset_task_type:
            for tt in raw_task_types:
                if tt.get("for_entity") == "Asset":
                    asset_task_type = tt
                    break

        if not shot_task_type or not asset_task_type:
            print("[-] ERROR: Faltan tipos de tarea en Kitsu. Necesitas al menos una tarea configurada para 'Shots' y una para 'Assets'.")
            sys.exit(1)
            
        print(f"    -> Tarea para Shot encontrada: {shot_task_type['name']}")
        print(f"    -> Tarea para Asset encontrada: {asset_task_type['name']}")

    except Exception as e:
        print(f"[-] Error consultando la API cruda: {e}")
        sys.exit(1)

    # 7. Asignaciones
    print("\n[+] Asignando Tareas a Usuarios...")
    
    shot_10 = gazu.shot.get_shot_by_name(sequence, "sh010")
    if shot_10 and created_users.get("Vendor"):
        task = gazu.task.get_task_by_entity(shot_10, shot_task_type)
        if not task: 
            task = gazu.task.new_task(shot_10, shot_task_type)
        gazu.task.assign_task(task, created_users["Vendor"])
        print(f"    -> Tarea '{shot_task_type['name']}' en 'sh010' asignada al Vendor.")

    if asset and created_users.get("Artist"):
        task = gazu.task.get_task_by_entity(asset, asset_task_type)
        if not task: 
            task = gazu.task.new_task(asset, asset_task_type)
        gazu.task.assign_task(task, created_users["Artist"])
        print(f"    -> Tarea '{asset_task_type['name']}' en 'Prota' asignada al Artist.")

    print("\n==================================================")
    print("✅ Siembra de datos completada con éxito.")
    print("==================================================")

if __name__ == "__main__":
    main()

```

--------------------------------------------------------------------------------

### Archivo: `tests/dev_tools/seed_project_template.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Herramienta de Desarrollo: seed_project_template.py
# Rol: Configura el esqueleto AAA en Kitsu (Departamentos, Task Types y Plantilla)
# =========================================================================================

import gazu
import os

def get_credentials():
    """Obtiene las credenciales del entorno o usa los valores por defecto de desarrollo."""
    host = os.environ.get("KITSU_HOST", "http://localhost:8080/api")
    email = os.environ.get("KITSU_USER", "admin@example.com")
    pwd = os.environ.get("KITSU_PWD", "mysecretpassword")
    return host, email, pwd

def main():
    print("\n" + "="*50)
    print("🎬 OPENSTUDIO HUB - KITSU TEMPLATE SEEDER 🎬")
    print("="*50)

    host, email, pwd = get_credentials()
    
    try:
        print(f"[*] Conectando a Kitsu en: {host}")
        gazu.client.set_host(host)
        gazu.log_in(email, pwd)
        print("[*] ✓ Autenticación exitosa.")

        # 1. LOCALIZAR O CREAR LA PLANTILLA
        template_name = "standard-3d-production"
        template = gazu.project_template.get_project_template_by_name(template_name)
        
        if not template:
            print(f"[*] Plantilla '{template_name}' no encontrada. Creándola...")
            template = gazu.project_template.new_project_template(
                name=template_name,
                description="OpenStudioHub Default",
                production_style="3d",
                fps="24",
                ratio="16:9",
                resolution="1920x1080"
            )
            print(f"[*] ✓ Plantilla creada con ID: {template['id']}")
        else:
            print(f"[*] ✓ Plantilla '{template_name}' localizada.")

        # 2. ASEGURAR DEPARTAMENTOS
        print("\n[*] Verificando Departamentos...")
        depts = gazu.person.all_departments()
        
        dept_storyboard = next((d for d in depts if d["name"].lower() == "storyboard"), None)
        if not dept_storyboard:
            dept_storyboard = gazu.person.new_department(name="Storyboard")
            print("    ↳ ✓ Departamento 'Storyboard' creado.")
            
        dept_edit = next((d for d in depts if d["name"].lower() == "editorial" or d["name"].lower() == "edit"), None)
        if not dept_edit:
            dept_edit = gazu.person.new_department(name="Editorial")
            print("    ↳ ✓ Departamento 'Editorial' creado.")

        # 3. ASEGURAR TASK TYPES Y VINCULARLOS A LA PLANTILLA
        print("\n[*] Verificando Task Types (Tipos de Tareas)...")
        all_tts = gazu.task.all_task_types()
        template_tts = gazu.project_template.all_task_types_for_project_template(template)
        template_tt_ids = [tt["id"] for tt in template_tts]

        # A. STORYBOARD (Asignado a Secuencias)
        stb_tt = next((tt for tt in all_tts if tt["name"].lower() == "storyboard" and tt["for_entity"].lower() == "sequence"), None)
        if not stb_tt:
            stb_tt = gazu.task.new_task_type(name="Storyboard", for_entity="Sequence", department_id=dept_storyboard["id"], color="#F97316")
            print("    ↳ ✓ Task Type 'Storyboard' (Sequence) creado.")
        
        if stb_tt["id"] not in template_tt_ids:
            gazu.project_template.add_task_type_to_project_template(template, stb_tt)
            print("    ↳ ✓ 'Storyboard' anclado a la plantilla.")

        # B. EDITORIAL (Asignado a Edits)
        edit_tt = next((tt for tt in all_tts if tt["name"].lower() == "editorial" and tt["for_entity"].lower() == "edit"), None)
        if not edit_tt:
            edit_tt = gazu.task.new_task_type(name="Editorial", for_entity="Edit", department_id=dept_edit["id"], color="#3B82F6")
            print("    ↳ ✓ Task Type 'Editorial' (Edit) creado.")
            
        if edit_tt["id"] not in template_tt_ids:
            gazu.project_template.add_task_type_to_project_template(template, edit_tt)
            print("    ↳ ✓ 'Editorial' anclado a la plantilla.")

        # 4. CREAR UN PROYECTO DE PRUEBA
        test_project_name = "Neon Chase Hub Test"
        print(f"\n[*] Creando proyecto de prueba: '{test_project_name}'...")
        
        existing_proj = gazu.project.get_project_by_name(test_project_name)
        if existing_proj:
            print(f"[*] ⚠️ El proyecto '{test_project_name}' ya existe. Saltando creación.")
        else:
            new_proj = gazu.project.new_project(name=test_project_name, project_template=template)
            print(f"[*] ✓ Proyecto '{test_project_name}' creado exitosamente a partir de la plantilla.")

        print("\n" + "="*50)
        print("✅ SEEDING COMPLETADO CON ÉXITO")
        print("="*50 + "\n")

    except Exception as e:
        print(f"\n[!] ERROR CRÍTICO: {e}")

if __name__ == "__main__":
    main()

```

--------------------------------------------------------------------------------

### Archivo: `tests/dev_tools/seed_svn_ssh.py`

```python
import json
import getpass
import paramiko
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "svn_ssh_env.json"

def get_credentials():
    """Carga o solicita las credenciales SSH y de SVN."""
    if CONFIG_FILE.exists():
        print(f"[+] Cargando credenciales cacheadas desde {CONFIG_FILE.name}...")
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("[-] Error: Configuración corrupta. Borrando...")
            CONFIG_FILE.unlink()
            
    print("[!] Configuración de Conexión SSH al Servidor SVN:")
    ssh_host = input("IP/Dominio del Servidor SSH (ej. 192.168.1.100): ").strip()
    
    ssh_port = input("Puerto SSH [Enter para 2222]: ").strip()
    if not ssh_port:
        ssh_port = "2222"
        
    ssh_user = input("Usuario SSH (ej. root o ubuntu): ").strip()
    ssh_passphrase = getpass.getpass("Passphrase de la llave SSH (o contraseña): ")
    
    print("\n[!] Configuración del Proyecto SVN:")
    project_name = input("Nombre del Proyecto (ej. p0004-hub-test): ").strip()
    svn_user = input("Usuario SVN a crear (ej. vendor): ").strip()
    svn_pass = getpass.getpass("Contraseña del Usuario SVN: ")
    
    config_data = {
        "ssh_host": ssh_host,
        "ssh_port": int(ssh_port),
        "ssh_user": ssh_user,
        "ssh_passphrase": ssh_passphrase,
        "project_name": project_name,
        "svn_user": svn_user,
        "svn_pass": svn_pass
    }
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)
    print(f"[+] Credenciales guardadas en {CONFIG_FILE.name}\n")
    return config_data

def execute_remote_cmd(ssh_client, command, step_name):
    """Ejecuta un comando vía SSH e imprime el resultado."""
    print(f"⚙️  {step_name}...")
    stdin, stdout, stderr = ssh_client.exec_command(command)
    
    # Bloquea hasta que el comando termine y lee los resultados
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    
    if exit_status == 0:
        if out: print(f"    Salida: {out}")
        return True
    else:
        # Ignoramos el error si el repositorio ya existe
        if "already exists" in err or "ya existe" in err:
            print("    -> El repositorio/directorio ya existe. Omitiendo.")
            return True
        print(f"    ❌ Error: {err}")
        return False

def main():
    print("==================================================")
    print("🚀 SVN SSH Aprovisionador Automático (Docker)")
    print("==================================================")
    
    creds = get_credentials()
    project = creds["project_name"]
    repo_path = f"/var/opt/svn/{project}"
    file_url = f"file://{repo_path}"
    
    # 1. Establecer conexión SSH
    print(f"\n[+] Conectando vía SSH a {creds['ssh_user']}@{creds['ssh_host']}:{creds['ssh_port']}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # paramiko intentará usar la llave por defecto (~/.ssh/id_rsa, etc.)
        # Le pasamos el passphrase explícitamente para descifrarla, o como fallback de contraseña
        ssh.connect(
            hostname=creds["ssh_host"],
            port=creds["ssh_port"],
            username=creds["ssh_user"],
            password=creds["ssh_passphrase"],
            passphrase=creds["ssh_passphrase"],
            timeout=10
        )
    except Exception as e:
        print(f"❌ Fallo de conexión SSH: {e}")
        # Purgamos el archivo corrupto/inválido para forzar la re-evaluación la próxima vez
        if CONFIG_FILE.exists(): CONFIG_FILE.unlink()
        return

    # 2. Definir Comandos Docker
    cmd_create = f"docker exec estudio_svn svnadmin create {repo_path}"
    
    cmd_conf = (
        f"docker exec estudio_svn sh -c \"echo '[general]' > {repo_path}/conf/svnserve.conf && "
        f"echo 'anon-access = none' >> {repo_path}/conf/svnserve.conf && "
        f"echo 'auth-access = write' >> {repo_path}/conf/svnserve.conf && "
        f"echo 'password-db = passwd' >> {repo_path}/conf/svnserve.conf\""
    )
    
    cmd_users = (
        f"docker exec estudio_svn sh -c \"echo '[users]' > {repo_path}/conf/passwd && "
        f"echo '{creds['svn_user']} = {creds['svn_pass']}' >> {repo_path}/conf/passwd\""
    )
    
    cmd_mkdir = (
        f"docker exec estudio_svn svn mkdir "
        f"{file_url}/02_archivos_de_produccion "
        f"{file_url}/02_archivos_de_produccion/edit "
        f"{file_url}/02_archivos_de_produccion/pro "
        f"{file_url}/02_archivos_de_produccion/pro/assets "
        f"{file_url}/02_archivos_de_produccion/pro/assets/Character "
        f"{file_url}/02_archivos_de_produccion/pro/assets/Character/Prota "
        f"{file_url}/02_archivos_de_produccion/pro/shots "
        f"{file_url}/02_archivos_de_produccion/pro/shots/sq01 "
        f"{file_url}/02_archivos_de_produccion/pro/shots/sq01/sh010 "
        f"{file_url}/02_archivos_de_produccion/pro/shots/sq01/sh020 "
        f"-m 'Init: Estructura base automatizada y Kitsu Sandbox para {project}'"
    )

    # 3. Ejecutar la secuencia
    print(f"\n[+] Forjando el Árbol de Producción SVN...")
    
    if not execute_remote_cmd(ssh, cmd_create, "[1/4] Creando la bóveda SVN"): return
    if not execute_remote_cmd(ssh, cmd_conf, "[2/4] Blindando el acceso (svnserve.conf)"): return
    if not execute_remote_cmd(ssh, cmd_users, "[3/4] Inyectando credenciales base de artistas"): return
    if not execute_remote_cmd(ssh, cmd_mkdir, "[4/4] Forjando la topología de carpetas"): return

    ssh.close()
    print("\n==================================================")
    print(f"✅ ÉXITO: El repositorio {project} está online y estructurado.")
    print("==================================================")

if __name__ == "__main__":
    main()

```

--------------------------------------------------------------------------------

### Archivo: `tests/dev_tools/test_api_kitsu.py`

```python
import gazu
import getpass

host = input("URL de Kitsu: ").strip()
if not host.endswith("/api"): host += "/api"

gazu.client.set_host(host)
gazu.log_in(input("Email: "), getpass.getpass("Clave: "))

print("\n--- DUMP DE LA API ---")
for task_name in ["Animation", "Rigging"]:
    t = gazu.task.get_task_type_by_name(task_name)
    if t:
        print(f"[{task_name}] ID: {t.get('id')}")
        print(f"[{task_name}] For Entity: {t.get('for_entity')}")
    else:
        print(f"[{task_name}] No encontrado.")

```

--------------------------------------------------------------------------------

### Archivo: `tests/test_kitsu.py`

```python
from core.auth_manager import AuthManager

auth = AuthManager()

# Intentar usar sesión guardada
if auth.login_with_saved_session():
    print("✅ Sesión restaurada automáticamente.")
else:
    print("❌ No hay sesión, iniciando login manual...")
    # Reemplaza con tus datos reales de Kitsu (Vectra Genisys / Aether X)
    url = "https://proyectos.macuare.com.ve" 
    email = "ernesto@macuare.com.ve"
    password = 'fFs&"b?#?Y5>tz&1'
    
    exito, mensaje = auth.login_with_credentials(email, password, url)
    print(mensaje)

if auth.user_data:
    print(f"👤 Hola, {auth.user_data['first_name']}!")
    
    rol = auth.get_user_role()
    if rol == "td":
        print("👑 Eres un DIRECTOR TÉCNICO. Tienes acceso a crear proyectos.")
    else:
        print("🎨 Eres un ARTISTA. Tienes acceso al Hub de trabajo.")

```

--------------------------------------------------------------------------------

### Archivo: `tests/test_kitsu_mapping.py`

```python
import gazu
import json

def main():
    print("=======================================")
    print(" KITSU API ISOLATED TEST: TASK MAPPING ")
    print("=======================================\n")

    # 1. CONFIGURACIÓN (Reemplaza con tus datos reales)
    # ---------------------------------------------------------
    KITSU_HOST = "http://localhost:8080/api"  # Ajusta tu URL y puerto
    KITSU_USER = "admin@example.com"     # Tu correo de admin
    KITSU_PWD  = "entrando1"      # Tu contraseña
    
    PROJECT_NAME = "01_test" # Pon el nombre de tu proyecto de prueba
    SEQUENCE_NAME = "01"              # Secuencia que sepas que existe
    # ---------------------------------------------------------

    try:
        # Autenticación
        print(f"[*] Conectando a Kitsu en {KITSU_HOST}...")
        gazu.client.set_host(KITSU_HOST)
        gazu.log_in(KITSU_USER, KITSU_PWD)
        print("[✓] Login exitoso.\n")

        # Buscar Proyecto y Secuencia
        print(f"[*] Buscando proyecto '{PROJECT_NAME}'...")
        project = gazu.project.get_project_by_name(PROJECT_NAME)
        if not project:
            print("[X] Proyecto no encontrado. Abortando.")
            return

        print(f"[*] Buscando secuencia '{SEQUENCE_NAME}'...")
        sequence = gazu.shot.get_sequence_by_name(project, SEQUENCE_NAME)
        if not sequence:
            print("[X] Secuencia no encontrada. Abortando.")
            return
        breakpoint()
        # Listar tareas de la secuencia
        tasks = gazu.task.all_tasks_for_sequence(sequence)
        print(f"\n[✓] Se encontraron {len(tasks)} tareas para la secuencia {SEQUENCE_NAME}.")
        
        if not tasks:
            print("[!] No hay tareas para inspeccionar. Crea una primero.")
            return

        # Tomar la primera tarea (Debería ser Storyboard si es la única)
        target_task = tasks[0]
        
        print("\n--- CONTENIDO ORIGINAL DE LA TAREA ---")
        # Imprimimos los campos clave para ver si "data" es None, dict, o string
        print(f"ID: {target_task.get('id')}")
        print(f"Task Type: {target_task.get('task_type_name')}")
        print(f"Data actual: {target_task.get('data')}")
        print("--------------------------------------\n")

        print("[*] Inyectando ruta dummy...")
        
        # Extracción hiper-segura
        task_data = target_task.get("data")
        
        # Validamos qué tipo de dato es para evitar el 'NoneType is not subscriptable'
        print(f"    -> Tipo de 'data' recibido de Gazu: {type(task_data)}")
        
        if task_data is None:
            task_data = {}
        elif not isinstance(task_data, dict):
            # Por si Gazu devuelve un string vacío o algo raro
            task_data = {}
            
        task_data["file_path"] = "svn/edit/storyboards/dummy_path-storyboard.blend"
        task_data["file_name"] = "dummy_path-storyboard.blend"
        
        # Intento de actualización
        print(f"[*] Enviando payload: {task_data}")
        gazu.task.update_task_data(target_task["id"], task_data)
        print("[✓] Petición enviada.\n")

        # Verificación
        print("[*] Consultando nuevamente la base de datos...")
        updated_task = gazu.task.get_task(target_task["id"])
        
        print("\n--- CONTENIDO ACTUALIZADO ---")
        print(f"Data verificada: {updated_task.get('data')}")
        print("-----------------------------\n")
        
        if updated_task.get('data') and updated_task['data'].get('file_path'):
            print("[SUCCESS] ¡La inserción fue exitosa y Kitsu la guardó!")
        else:
            print("[FAIL] Kitsu no retuvo la información de 'data'.")

    except Exception as e:
        print(f"\n[ERROR CRÍTICO] Excepción capturada:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

```

--------------------------------------------------------------------------------

### Archivo: `tests/test_webengine.py`

```python
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

app = QApplication(sys.argv)
view = QWebEngineView()
view.load("https://www.google.com")
view.show()
sys.exit(app.exec())

```

--------------------------------------------------------------------------------

### Archivo: `tools/context_dumper.py`

```python
import ast
import argparse
import re
from pathlib import Path
from typing import List, Set

# =====================================================================
# MACUARE ESTUDIO - CONTEXT DUMPER (Políglota)
# =====================================================================
# Descripción: Script de utilidad para extraer firmas de Python,
# endpoints de JavaScript/Vue, y firmas de C++. Ideal para "hidratar" 
# el contexto de un LLM leyendo APIs y estructuras de código.
# =====================================================================

IGNORE_DIRS: Set[str] = {
    ".git", 
    ".venv", 
    "venv", 
    "__pycache__", 
    "node_modules", 
    "build", 
    "dist"
}

# Extensiones soportadas actualizadas para incluir C++
TARGET_EXTENSIONS: Set[str] = {".py", ".js", ".vue", ".cc", ".hh"}

class ContextExtractor(ast.NodeVisitor):
    """Extractor AST estricto para archivos Python."""
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.extracted_data: List[str] = []
        self.current_class = None

    def _get_docstring_summary(self, node) -> str:
        doc = ast.get_docstring(node)
        if doc:
            first_line = doc.strip().split('\n')[0]
            return f'"""{first_line}..."""'
        return ""

    def visit_ClassDef(self, node: ast.ClassDef):
        bases = [ast.unparse(b) for b in node.bases] if hasattr(ast, 'unparse') else []
        bases_str = f"({', '.join(bases)})" if bases else ""
        
        self.extracted_data.append(f"\nclass {node.name}{bases_str}:")
        doc = self._get_docstring_summary(node)
        if doc:
            self.extracted_data.append(f"    {doc}")
            
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._process_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._process_function(node, is_async=True)

    def _process_function(self, node, is_async=False):
        try:
            args_str = ast.unparse(node.args)
            returns_str = f" -> {ast.unparse(node.returns)}" if node.returns else ""
            prefix = "async def " if is_async else "def "
            indent = "    " if self.current_class else ""
            
            sig = f"{indent}{prefix}{node.name}({args_str}){returns_str}:"
            self.extracted_data.append(sig)
            
            doc = self._get_docstring_summary(node)
            if doc:
                self.extracted_data.append(f"{indent}    {doc}")
                
        except AttributeError:
            sig = self.source_lines[node.lineno - 1].strip()
            indent = "    " if self.current_class else ""
            self.extracted_data.append(f"{indent}{sig}")

def process_py_file(filepath: Path) -> str:
    """Procesa archivos .py usando Abstract Syntax Trees."""
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content)
        lines = content.splitlines()
        
        extractor = ContextExtractor(lines)
        extractor.visit(tree)
        
        if extractor.extracted_data:
            return _format_header(filepath) + "\n".join(extractor.extracted_data) + "\n"
        return ""
    except SyntaxError:
        return f"\n# [ERROR SINTÁCTICO] No se pudo analizar {filepath}\n"
    except Exception as e:
        return f"\n# [ERROR] Fallo leyendo {filepath}: {e}\n"

def process_js_file(filepath: Path) -> str:
    """Procesa archivos .js/.vue usando Regex para capturar Endpoints y Exports."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        extracted = []
        
        # Regex para atrapar exportaciones, funciones o peticiones HTTP comunes en Vue/Vuex
        api_pattern = re.compile(r"^(export\s+(const|function|default)|const\s+\w+\s*=\s*(async\s+)?\(|Vue\.http\.|axios\.)")
        
        for line in content.splitlines():
            stripped = line.strip()
            if api_pattern.match(stripped) or "=>" in stripped and "http" in stripped:
                # Truncamos líneas minificadas extremadamente largas
                if len(stripped) < 250: 
                    extracted.append(stripped)
                    
        if extracted:
            return _format_header(filepath) + "\n".join(extracted) + "\n"
        return ""
    except Exception as e:
        return f"\n# [ERROR JS] Fallo leyendo {filepath}: {e}\n"

def process_cpp_file(filepath: Path) -> str:
    """Procesa archivos .cc/.hh usando Regex para capturar Clases y Firmas de Funciones."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        extracted = []
        
        # Regex básico para atrapar:
        # 1. Declaraciones de class, struct o namespace.
        # 2. Firmas de funciones y métodos (incluyendo constructores/destructores).
        cpp_pattern = re.compile(
            r"^\s*(?:class|struct|namespace)\s+[a-zA-Z_]\w*" 
            r"|^\s*(?:virtual\s+|static\s+|inline\s+)?(?:[a-zA-Z_][\w:]*(?:<[^>]+>)?\s+)+[a-zA-Z_~][\w:]*\s*\([^)]*\)"
        )
        
        for line in content.splitlines():
            stripped = line.strip()
            if cpp_pattern.search(stripped):
                # Evitar truncar si la línea de C++ es extremadamente larga por macros/templates
                if len(stripped) < 250: 
                    extracted.append(stripped)
                    
        if extracted:
            return _format_header(filepath) + "\n".join(extracted) + "\n"
        return ""
    except Exception as e:
        return f"\n# [ERROR CPP] Fallo leyendo {filepath}: {e}\n"

def _format_header(filepath: Path) -> str:
    return f"\n{'='*50}\n# FILE: {filepath.name}\n# PATH: {filepath}\n{'='*50}\n"

def dump_context(root_dir: Path, output_file: Path):
    print(f"[MAREIWA] Iniciando escaneo en: {root_dir.resolve()}")
    
    with open(output_file, "w", encoding="utf-8") as out_f:
        out_f.write("# ==========================================\n")
        out_f.write("# MACUARE HUB - AUTOMATED CONTEXT DUMP\n")
        out_f.write("# ==========================================\n\n")
        
        files_found = 0
        
        for filepath in root_dir.rglob("*"):
            if filepath.suffix not in TARGET_EXTENSIONS:
                continue
                
            if any(part in IGNORE_DIRS for part in filepath.parts):
                continue
                
            # Enrutamiento basado en extensión
            if filepath.suffix == ".py":
                dump = process_py_file(filepath)
            elif filepath.suffix in {".cc", ".hh"}:
                dump = process_cpp_file(filepath)
            else:
                dump = process_js_file(filepath)
                
            if dump:
                out_f.write(dump)
                files_found += 1
                print(f"  -> Procesado: {filepath.name}")

    print(f"\n[MAREIWA] ¡Dump completado! {files_found} archivos procesados.")
    print(f"[MAREIWA] El contexto está listo en: {output_file.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrae firmas de Python, JS/Vue y C++.")
    parser.add_argument("--root", type=str, default=".", help="Directorio raíz a escanear.")
    parser.add_argument("--out", type=str, default="prompt_context.txt", help="Archivo de salida.")
    
    args = parser.parse_args()
    
    root_path = Path(args.root)
    output_path = Path(args.out)
    
    if not root_path.exists() or not root_path.is_dir():
        print(f"[ERROR] El directorio {root_path} no existe.")
    else:
        dump_context(root_path, output_path)

```

--------------------------------------------------------------------------------

### Archivo: `tools/kitsu_bruteforce_edit.py`

```python
import gazu

def main():
    print("=========================================")
    print(" KITSU API: BRUTE FORCE EDIT PERMISSIONS ")
    print("=========================================\n")

    # 1. CONFIGURACIÓN
    KITSU_HOST = "http://localhost:8080/api"  
    PROJECT_NAME = "01_test" # Reemplaza con tu proyecto de prueba

    # Diccionario de cuentas a someter a fuerza bruta (Ajusta las contraseñas)
    USERS_TO_TEST = {
        "Super Admin": ("admin@example.com", "entrando1"),
        "Production Manager": ("pm@estudiomacuare.com", "entrar123"),
        "3D Artist": ("editor@estudiomacuare.com", "entrar123")
    }

    gazu.client.set_host(KITSU_HOST)

    for role_name, (email, pwd) in USERS_TO_TEST.items():
        print(f"--- Probando cuenta: {role_name} ({email}) ---")
        try:
            # Iniciamos sesión
            gazu.log_in(email, pwd)
            project = gazu.project.get_project_by_name(PROJECT_NAME)

            if not project:
                print(f"[!] Proyecto '{PROJECT_NAME}' no encontrado. Abortando prueba.")
                break

            print("[*] Intentando ejecutar gazu.edit.new_edit()...")
            
            # Ejecutamos la función exacta que usa el addon de Blender[cite: 4]
            test_edit = gazu.shot.new_shot(project, sequence="675ca7b8-0b4e-4283-82b5-1fb6b123369d", name=f"Test_Sot_{role_name.replace(' ', '_')}")

            print(f"[SUCCESS] ¡El usuario {role_name} SÍ TIENE PERMISOS para crear Shots!")

            # Limpieza inmediata si tuvo éxito[cite: 4]
            gazu.shot.remove_shot(test_edit, force=True)
            print("[*] Shot de prueba eliminado exitosamente.\n")

        # Capturamos específicamente el rebote de permisos de Zou[cite: 4]
        except gazu.exception.NotAllowedException:
            print(f"[FAIL] 403 Forbidden: El usuario {role_name} REBOTÓ (Sin permisos).\n")
            
        except Exception as e:
            print(f"[ERROR] Fallo inesperado: {e}\n")
            
        finally:
            # Deslogueamos para no contaminar la siguiente prueba del bucle[cite: 4]
            gazu.log_out()

if __name__ == "__main__":
    main()

```

--------------------------------------------------------------------------------

### Archivo: `tools/kitsu_check_role.py`

```python
import gazu

def main():
    print("=========================================")
    print(" KITSU API: VERIFICAR ROL DE USUARIO ")
    print("=========================================\n")

    # 1. CONFIGURACIÓN
    # ---------------------------------------------------------
    KITSU_HOST = "http://localhost:8080/api"  
    KITSU_USER = "admin@example.com"     
    KITSU_PWD  = "entrando1"
    
    # El correo del usuario que quieres investigar
    TARGET_EMAIL = "editor@estudiomacuare.com"         
    # ---------------------------------------------------------

    try:
        # Autenticación
        gazu.client.set_host(KITSU_HOST)
        gazu.log_in(KITSU_USER, KITSU_PWD)
        print("[*] Conexión exitosa a la API.\n")

        # 2. BUSCAR AL USUARIO
        target_user = gazu.person.get_person_by_email(TARGET_EMAIL)

        if not target_user:
            print(f"[X] ERROR: No se encontró ningún usuario con el correo '{TARGET_EMAIL}'.")
            return

        # 3. IMPRIMIR RESULTADOS
        print("=== DATOS DEL USUARIO ===")
        print(f"Nombre: {target_user.get('first_name')} {target_user.get('last_name')}")
        print(f"Correo: {target_user.get('email')}")
        print(f"Activo: {target_user.get('active')}")
        
        # El campo 'role' es la llave maestra en Zou
        print(f"\n--> ROL GLOBAL (Zou RBAC): '{target_user.get('role')}' <--\n")
        print("=========================")

        if target_user.get('role') not in ['admin', 'manager']:
            print("[!] ADVERTENCIA: Este usuario NO tiene permisos para forjar un Master Edit a nivel global.")

    except Exception as e:
        print(f"\n[ERROR CRÍTICO] Excepción capturada: {e}")

if __name__ == "__main__":
    main()

```

--------------------------------------------------------------------------------

### Archivo: `tools/kitsu_role_mod.py`

```python
import gazu
import json

def main():
    print("=========================================")
    print(" KITSU API SURGEON: ROLE & PERMISSIONS ")
    print("=========================================\n")

    # 1. CONFIGURACIÓN
    # ---------------------------------------------------------
    KITSU_HOST = "http://localhost:8080/api"  # Ajusta tu URL y puerto
    KITSU_USER = "admin@example.com"     # DEBE ser un usuario Administrador
    KITSU_PWD  = "entrando1"
    
    # Nombre exacto del rol que quieres modificar (Sensible a mayúsculas)
    TARGET_ROLE_NAME = "Manager"         # Cambia esto por "PM" o tu rol real
    # ---------------------------------------------------------

    try:
        # Autenticación
        print(f"[*] Conectando a Kitsu en {KITSU_HOST}...")
        gazu.client.set_host(KITSU_HOST)
        gazu.log_in(KITSU_USER, KITSU_PWD)
        print("[✓] Login de Administrador exitoso.\n")

        # 2. AUDITORÍA DE ROLES (Endpoint Crudo)
        print("[*] Descargando matriz de roles del sistema...")
        roles = gazu.client.get("data/roles")
        
        print("\n=== ROLES DISPONIBLES ===")
        target_role = None
        for r in roles:
            print(f"- {r.get('name')} (ID: {r.get('id')})")
            if r.get('name') == TARGET_ROLE_NAME:
                target_role = r
        print("=========================\n")

        if not target_role:
            print(f"[X] ERROR: No se encontró ningún rol con el nombre '{TARGET_ROLE_NAME}'.")
            print("Por favor, verifica el nombre exacto en la lista de arriba.")
            return

        # 3. INSPECCIÓN Y PARCHEO
        print(f"[*] Rol objetivo encontrado: {TARGET_ROLE_NAME}")
        
        # En Kitsu, los permisos pueden venir como una lista o como un string separado por comas
        current_permissions = target_role.get("permissions", [])
        print("\n--- PERMISOS ACTUALES ---")
        print(json.dumps(current_permissions, indent=2))
        print("-------------------------\n")

        # Permisos necesarios para interactuar con la entidad Edit
        required_permissions = ["edit:create", "edit:update", "edit:delete", "edit:read"]

        print("[*] Inyectando permisos de Edición (Edit)...")
        
        # Si es una lista (Formato moderno de Zou)
        if isinstance(current_permissions, list):
            for p in required_permissions:
                if p not in current_permissions:
                    current_permissions.append(p)
            target_role["permissions"] = current_permissions
            
        # Si es un string (Formato legacy de algunas versiones)
        elif isinstance(current_permissions, str):
            perm_list = current_permissions.split(",")
            for p in required_permissions:
                if p not in perm_list:
                    perm_list.append(p)
            target_role["permissions"] = ",".join(perm_list)

        # 4. ACTUALIZACIÓN EN LA BASE DE DATOS
        print(f"[*] Guardando cambios en la base de datos para el rol {TARGET_ROLE_NAME}...")
        
        # Hacemos un PUT crudo al endpoint del rol específico
        endpoint = f"data/roles/{target_role['id']}"
        response = gazu.raw.put(endpoint, target_role)
        
        print("\n[SUCCESS] ¡Permisos actualizados con éxito!")
        print("--- NUEVOS PERMISOS ---")
        print(json.dumps(response.get("permissions", []), indent=2))
        print("-----------------------\n")
        
        print("[!] NOTA: El usuario PM debe cerrar sesión e iniciarla nuevamente para que Kitsu recargue su token.")

    except Exception as e:
        print(f"\n[ERROR CRÍTICO] Excepción capturada:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

```

--------------------------------------------------------------------------------

### Archivo: `ui/__init__.py`

```python

```

--------------------------------------------------------------------------------

### Archivo: `ui/base_dashboard.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/base_dashboard.py
# Rol Arquitectónico: UI Component / Master Layout & Shell (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.2.0 (Full-Height Layout Integration)
# =========================================================================================

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame

from ui.components.top_bar import TopBar
from ui.components.sidebar import Sidebar
from ui.components.status_bar import StatusBar

class BaseDashboardView(QWidget):
    def __init__(self, parent, auth_manager, config_factory, on_logout, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.auth = auth_manager
        self.config_factory = config_factory
        self.on_logout = on_logout
        
        self.setObjectName("ViewBase")
        self._build_shell()

    def _build_shell(self):
        """Construye el esqueleto inmutable ensamblando los submódulos."""
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. SIDEBAR (Instanciado por Composición con Branding)
        # La barra lateral ahora abarca el 100% de la altura y contiene el Logo
        self.sidebar = Sidebar(self, self.config_factory)
        self.main_layout.addWidget(self.sidebar)

        # 2. RIGHT PANEL (Contenedor fluido derecho)
        self.right_panel = QFrame()
        self.right_panel.setObjectName("MainContentFrame")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)

        # 3. TOP BAR (Instanciado por Composición - Header Limpio)
        self.top_bar = TopBar(self.right_panel, self.auth, self.config_factory, self.on_logout)
        self.right_layout.addWidget(self.top_bar)

        # 4. CONTENT AREA (Lienzo para subclases)
        self.content_container = QFrame()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(15, 25, 15, 20)
        self.content_layout.setSpacing(20)
        self.right_layout.addWidget(self.content_container, stretch=1)

        # 5. STATUS BAR (Instanciado por Composición)
        self.status_bar = StatusBar(self.right_panel)
        self.right_layout.addWidget(self.status_bar)

        self.main_layout.addWidget(self.right_panel, stretch=1)

    # -------------------------------------------------------------
    # WRAPPERS/PROXIES (Para no romper las subclases existentes)
    # -------------------------------------------------------------
    def add_sidebar_button(self, btn_id: str, texto: str, emoji: str, icon_name: str, callback, activo: bool = False):
        self.sidebar.add_button(btn_id, texto, emoji, icon_name, callback, activo)

    def set_active_sidebar_button(self, btn_id: str):
        self.sidebar.set_active_button(btn_id)

    def actualizar_status(self, mensaje: str, color: str = "white"):
        self.status_bar.actualizar_status(mensaje, color)

```

--------------------------------------------------------------------------------

### Archivo: `ui/components/__init__.py`

```python

```

--------------------------------------------------------------------------------

### Archivo: `ui/components/activity_card.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/activity_card.py
# Rol Arquitectónico: UI Component / Activity Feed Card (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.6.1
# =========================================================================================

"""
Componente visual para la lista del Activity Feed (Bandeja de Entrada).
Migrado a PySide6. Estilos delegados al QSS global para integración inmersiva.
"""

import webbrowser
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QThread, Signal


class AcknowledgeWorker(QThread):
    """Hilo secundario para enviar el Acuse de Recibo a Kitsu sin bloquear la interfaz."""
    ack_finished = Signal(bool)

    def __init__(self, auth_manager, task_id: str, comment_id: str):
        super().__init__()
        self.auth = auth_manager
        self.task_id = task_id
        self.comment_id = comment_id

    def run(self):
        exito = self.auth.acknowledge_activity(self.task_id, self.comment_id)
        self.ack_finished.emit(exito)


class ActivityCard(QFrame):
    def __init__(self, parent, activity_data: dict, auth_manager, on_acknowledge_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.data = activity_data
        self.auth_manager = auth_manager
        self.on_acknowledge_callback = on_acknowledge_callback

        # Unificación B2B: Hereda del contenedor estándar aunque con una variante sutil
        self.setObjectName("FloatingCard")
        
        # Ajuste de color para acentuarla ligeramente sobre el panel derecho
        self.setStyleSheet("""
            QFrame#FloatingCard {
                background-color: #2E3643;
                border: 1px solid #141820;
                border-radius: 8px;
            }
        """)

        self._build_ui()

    def _obtener_color_texto_contraste(self, hex_color: str) -> str:
        """Calcula la luminancia relativa (sRGB) para contrastar el texto del Badge."""
        if not hex_color: return "white"
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6: return "white"
        try:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#0F172A" if luminance > 0.5 else "#F8FAFC"
        except Exception:
            return "white"

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(8)

        # ---------------------------------------------------------
        # Fila 1: Avatar y Título (Autor + Tarea)
        # ---------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Inicial del autor (Placeholder de Avatar)
        author_name = self.data.get("author", {}).get("first_name", "U")
        lbl_avatar = QLabel(author_name[0].upper())
        lbl_avatar.setFixedSize(28, 28)
        lbl_avatar.setAlignment(Qt.AlignCenter)
        lbl_avatar.setStyleSheet("background-color: #3B82F6; color: white; border-radius: 14px; font-weight: bold;")
        header_layout.addWidget(lbl_avatar)
        
        # Texto del autor y entidad
        entity_name = self.data.get("entity", {}).get("name", "Unknown")
        task_name = self.data.get("task_type", {}).get("name", "Task")
        lbl_title = QLabel(f"<b>{author_name}</b> on {entity_name} - {task_name}")
        lbl_title.setStyleSheet("color: #E2E8F0; font-size: 12px;")
        lbl_title.setWordWrap(True)
        header_layout.addWidget(lbl_title, stretch=1)
        
        main_layout.addLayout(header_layout)

        # ---------------------------------------------------------
        # Fila 2: Texto del Comentario (Snippet)
        # ---------------------------------------------------------
        texto = self.data.get("text", "...")
        if len(texto) > 100:
            texto = texto[:97] + "..."
            
        lbl_texto = QLabel(texto)
        lbl_texto.setStyleSheet("color: #94A3B8; font-size: 11px;")
        lbl_texto.setWordWrap(True)
        main_layout.addWidget(lbl_texto)

        # ---------------------------------------------------------
        # Fila 3: Badge de Estado y Botón de Acción
        # ---------------------------------------------------------
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 5, 0, 0)
        
        lbl_estado_tag = QLabel("Estado:")
        lbl_estado_tag.setStyleSheet("color: #64748B; font-size: 11px;")
        footer_layout.addWidget(lbl_estado_tag)

        status_data = self.data.get("task_status", {})
        s_name = status_data.get("short_name", "???")
        s_color = status_data.get("color", "#444444")
        t_color = self._obtener_color_texto_contraste(s_color)

        lbl_badge = QLabel(s_name.upper())
        lbl_badge.setAlignment(Qt.AlignCenter)
        lbl_badge.setStyleSheet(f"""
            background-color: {s_color};
            color: {t_color};
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: bold;
        """)
        footer_layout.addWidget(lbl_badge)
        
        footer_layout.addStretch()

        self.btn_accion = QPushButton("Abrir _Marcar Leído")
        self.btn_accion.setCursor(Qt.PointingHandCursor)
        self.btn_accion.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        self.btn_accion.clicked.connect(self._ejecutar_accion)
        footer_layout.addWidget(self.btn_accion)

        main_layout.addLayout(footer_layout)

    def _ejecutar_accion(self):
        """Abre el navegador, notifica al backend vía QThread y notifica al padre."""
        self.btn_accion.setEnabled(False)
        self.btn_accion.setText("Procesando...")

        # Lanzar al navegador
        url = self.data.get("task_url")
        if url:
            webbrowser.open(url)

        # Enviar el Ack asíncrono
        task_id = self.data.get("task_id", "")
        comment_id = self.data.get("id", "")

        self.worker = AcknowledgeWorker(self.auth_manager, task_id, comment_id)
        self.worker.ack_finished.connect(lambda exito: self.on_acknowledge_callback(self))
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

```

--------------------------------------------------------------------------------

### Archivo: `ui/components/pipeline_wizard.py`

```python
# OPENSTUDIOHUB
# Módulo: ui/components/pipeline_wizard.py
# Rol: Componente visual secuencial para el Production Manager

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QWidget, QSizePolicy)
from PySide6.QtCore import Qt, Signal

class PipelineStepNode(QWidget):
    """Nodo individual de la barra de progreso (Círculo + Título)."""
    
    clicked = Signal(int)

    def __init__(self, step_number: int, title: str):
        super().__init__()
        self.step_number = step_number

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)
        
        self.node_circle = QLabel(str(step_number))
        self.node_circle.setAlignment(Qt.AlignCenter)
        self.node_circle.setFixedSize(44, 44)
        
        self.lbl_title = QLabel(f"{step_number}. {title}")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.node_circle, alignment=Qt.AlignCenter)
        layout.addWidget(self.lbl_title, alignment=Qt.AlignCenter)
        
        self.setCursor(Qt.PointingHandCursor)
        self.set_state(is_active=False, is_completed=False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.step_number)
        return super().mousePressEvent(event)

    def set_state(self, is_active: bool, is_completed: bool):
        # Asignación semántica para el QSS global
        if is_completed:
            self.node_circle.setObjectName("StepNodeCompleted")
            self.lbl_title.setObjectName("StepTitleCompleted")
            self.node_circle.setText("✓")
        elif is_active:
            self.node_circle.setObjectName("StepNodeActive")
            self.lbl_title.setObjectName("StepTitleActive")
            self.node_circle.setText( str(self.step_number) )
        else:
            self.node_circle.setObjectName("StepNodePending")
            self.lbl_title.setObjectName("StepTitlePending")
            self.node_circle.setText( str(self.step_number) )
        
        # Forzar refresco de estilos en Qt
        self.node_circle.style().polish(self.node_circle)
        self.lbl_title.style().polish(self.lbl_title)


class PipelineWizardWidget(QFrame):
    """Barra de progreso secuencial y orquestador de Batch Creation."""
    action_requested = Signal(int) # Emite el paso actual (1=Storyboard, 2=Edit...)

    step_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PipelineWizardCard")
        
        self.current_step = 1
        self.steps_data = ["Storyboard", "Editorial", "Assets", "Shots"]
        self._nodes = []
        self._lines = []
        
        self._build_ui()
        self.set_step(1) # Inicializar en el paso 1

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)

        # Título
        lbl_header = QLabel(self.tr("Overall Project Health"))
        lbl_header.setObjectName("WizardHeader")
        main_layout.addWidget(lbl_header)

        # Contenedor de la barra de progreso
        progress_layout = QHBoxLayout()
        progress_layout.setAlignment(Qt.AlignCenter)
        progress_layout.setSpacing(0)

        for i, title in enumerate(self.steps_data):
            # Crear Nodo
            node = PipelineStepNode(i + 1, title)
            
            node.clicked.connect(self.step_changed.emit)

            self._nodes.append(node)
            progress_layout.addWidget(node)

            # Crear Línea conectora (excepto para el último nodo)
            if i < len(self.steps_data) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self._lines.append(line)
                progress_layout.addWidget(line)

        main_layout.addLayout(progress_layout)

        # Botón Call to Action Central
        btn_layout = QHBoxLayout()
        self.btn_batch_create = QPushButton(self.tr("Batch Create Pending Files"))
        self.btn_batch_create.setObjectName("OrangeCTA")
        self.btn_batch_create.setCursor(Qt.PointingHandCursor)
        self.btn_batch_create.clicked.connect(lambda: self.action_requested.emit(self.current_step))
        
        # Spacer para centrar el botón
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_batch_create, stretch=1)
        btn_layout.addStretch()
        
        main_layout.addLayout(btn_layout)

    def set_step(self, step_number: int):
        """Actualiza el estado visual de los nodos y las líneas."""
        self.current_step = step_number
        
        for i, node in enumerate(self._nodes):
            is_completed = (i + 1) < step_number
            is_active = (i + 1) == step_number
            node.set_state(is_active, is_completed)
            
        for i, line in enumerate(self._lines):
            # Si el nodo a la izquierda de la línea está completado, colorear la línea
            if (i + 1) < step_number:
                line.setObjectName("StepLineCompleted")
            else:
                line.setObjectName("StepLinePending")
            line.style().polish(line)
            
        # Actualizar texto del botón según la etapa
        text_map = {
            1: "Spawn Storyboard Master",
            2: "Spawn Edit Master",
            3: "Batch Create Assets",
            4: "Batch Create Shots"
        }
        self.btn_batch_create.setText(self.tr(text_map.get(step_number, "Batch Create")))

```

--------------------------------------------------------------------------------

### Archivo: `ui/components/progress_dialog.py`

```python
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QTextEdit, QPushButton
from PySide6.QtGui import QTextCursor

class SpawningProgressDialog(QDialog):
    """Modal flotante que muestra el log de terminal en tiempo real con botones reactivos."""
    def __init__(self, parent, title: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(650, 420)
        self.setModal(True)
        self.setObjectName("FloatingCard")
        
        layout = QVBoxLayout(self)
        self.lbl_status = QLabel(self.tr("Initializing..."))
        self.lbl_status.setObjectName("H2Title")
        layout.addWidget(self.lbl_status)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(5)
        layout.addWidget(self.progress)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("FormInput")
        self.log_output.setStyleSheet("font-family: monospace; font-size: 12px; color: #94A3B8; background-color: #0F172A;")
        layout.addWidget(self.log_output)
        
        # --- Botonera Dinámica Inferior ---
        self.btn_layout = QHBoxLayout()
        self.btn_layout.addStretch()
        
        self.btn_action = QPushButton("")
        self.btn_action.setObjectName("PrimaryButton")
        self.btn_action.setFixedHeight(35)
        self.btn_action.hide() # Oculto por defecto
        
        self.btn_close = QPushButton(self.tr("Cancel"))
        self.btn_close.setObjectName("SecondaryButton")
        self.btn_close.setFixedHeight(35)
        self.btn_close.clicked.connect(self.accept)
        
        self.btn_layout.addWidget(self.btn_action)
        self.btn_layout.addWidget(self.btn_close)
        layout.addLayout(self.btn_layout)
        
    def update_progress(self, value: int, status_msg: str):
        if value > 0: self.progress.setValue(value)
        if status_msg: self.lbl_status.setText(status_msg)
        
    def append_log(self, text: str):
        self.log_output.append(text)
        self.log_output.moveCursor(QTextCursor.End)
        
    def finalize(self, success: bool, main_msg: str, action_text: str = "", action_callback = None):
        """Transforma el modal al terminar el proceso para auditar el log."""
        self.lbl_status.setText(main_msg)
        self.lbl_status.setStyleSheet("color: #10B981;" if success else "color: #EF4444;")
        
        self.btn_close.setText(self.tr("Close Window"))
        self.btn_close.setStyleSheet("background-color: #334155;")
        
        if success and action_callback and action_text:
            self.btn_action.setText(action_text)
            self.btn_action.show()
            self.btn_action.clicked.connect(action_callback)
            
        # Si falló, la barra se pone roja
        if not success:
            self.progress.setStyleSheet("QProgressBar::chunk { background-color: #EF4444; }")

```

--------------------------------------------------------------------------------

### Archivo: `ui/components/project_card.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/project_card.py
# Rol Arquitectónico: UI Component / Role-Aware Project Card
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.9.0 (Controller Injection & Code Purge)
# =========================================================================================

"""
Componente visual reutilizable para las Tarjetas de Proyectos.
Actúa estrictamente como la capa de Presentación (View). Delega todas las operaciones
de red (HTTP/Gazu) al KitsuManager y las operaciones de disco (Shutil/JSON) al NasManager,
respetando el patrón MVC y el Principio de Responsabilidad Única.
"""

import subprocess
import json
#import urllib.parse
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QWidget, QToolButton, QMenu,
                               QDialog, QLineEdit, QMessageBox, QApplication,
                               QStackedWidget, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QPixmap, QImage, QCursor, QAction, QDesktopServices, QColor, QIcon

from core.kitsu_manager import KitsuManager
from core.nas_manager import NasManager
from core.local_installer import LocalInstaller

class ProjectThumbnailWorker(QThread):
    """QThread dedicado a la descarga HTTP asíncrona de los avatares de proyectos."""
    image_downloaded = Signal(bytes)
    error_occurred = Signal(str)

    def __init__(self, kitsu_manager: KitsuManager, project_id: str, token: str, host_url: str):
        super().__init__()
        self.kitsu_mgr = kitsu_manager
        self.project_id = project_id
        self.token = token
        self.host_url = host_url

    def run(self):
        img_bytes = self.kitsu_mgr.download_project_thumbnail(self.project_id, self.token, self.host_url)
        if img_bytes: self.image_downloaded.emit(img_bytes)
        else: self.error_occurred.emit("Sin miniatura")

class ProjectInstallWorker(QThread):
    progress_update = Signal(str, str)
    finished_install = Signal(bool, str)

    def __init__(self, installer, project_root, vcs_user, vcs_pwd, user_role):
        super().__init__()
        self.installer = installer
        self.project_root = project_root
        self.vcs_user = vcs_user
        self.vcs_pwd = vcs_pwd
        self.user_role = user_role

    def run(self):
        success, msg = self.installer.instalar_entorno(
            project_root=self.project_root,
            vcs_user=self.vcs_user,
            vcs_pwd=self.vcs_pwd,
            status_callback=self._emit_status,
            user_role=self.user_role
        )
        self.finished_install.emit(success, msg)

    def _emit_status(self, mensaje, color):
        self.progress_update.emit(mensaje, color)

class DeleteProjectDialog(QDialog):
    """Modal de Seguridad (Type-to-Delete) estilo GitHub."""
    def __init__(self, parent, project_name: str):
        super().__init__(parent)
        self.project_name = project_name
        self.setWindowTitle(self.tr("⚠️ Warning: Project Destruction"))
        self.setFixedSize(450, 220)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        lbl_warn = QLabel(self.tr("You are about to permanently delete the project:\n<b>{0}</b>\n\nThis action will destroy Kitsu data, the SVN repository, and local files.").format(self.project_name))
        lbl_warn.setWordWrap(True)
        lbl_warn.setStyleSheet("color: #EF4444; font-size: 13px;")
        layout.addWidget(lbl_warn)

        lbl_instruct = QLabel(self.tr("To confirm, type <b>{0}</b> below:").format(self.project_name))
        lbl_instruct.setStyleSheet("color: #94A3B8;")
        layout.addWidget(lbl_instruct)

        self.entry_confirm = QLineEdit()
        self.entry_confirm.setObjectName("FormInput")
        self.entry_confirm.setFixedHeight(35)
        self.entry_confirm.textChanged.connect(self._validar_input)
        layout.addWidget(self.entry_confirm)

        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton(self.tr("Cancel"))
        self.btn_cancel.setObjectName("SecondaryButton")
        self.btn_cancel.setFixedHeight(35)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_delete = QPushButton(self.tr("Permanently Delete"))
        self.btn_delete.setStyleSheet("background-color: #EF4444; color: white; font-weight: bold; border-radius: 6px;")
        self.btn_delete.setFixedHeight(35)
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

    def _validar_input(self, text: str):
        self.btn_delete.setEnabled(text == self.project_name)

class ProjectCard(QFrame):
    def __init__(self, parent: QWidget, project_data: dict, auth_manager, nas_dir: Path, 
                 config_factory=None, vault_manager=None, on_rebuild_callback: Callable = None, 
                 on_open_wizard_callback: Callable = None, status_callback: Callable = None):
        super().__init__(parent)
        
        self.project_data = project_data
        self.auth = auth_manager
        self.config_factory = config_factory
        self.vault = vault_manager
        self.on_rebuild_callback = on_rebuild_callback
        self.on_open_wizard_callback = on_open_wizard_callback
        self.status_callback = status_callback
        
        # Instanciar Controladores
        self.kitsu_mgr = KitsuManager()
        self.nas_mgr = NasManager(nas_dir)
        
        self.project_dir = None
        self.user_role = self.auth.get_user_role() if hasattr(self.auth, 'get_user_role') else "user"
        
        self.setObjectName("FloatingCard")
        # Tarjeta más alta para acomodar el botón en roles No-Admin
        card_height = 280 if self.user_role == "td" else 330
        self.setFixedSize(320, card_height)
        
        self.setStyleSheet("""
            QFrame#FloatingCard { background-color: #1E293B; border-radius: 12px; border: 1px solid #334155; }
            QFrame#FloatingCard:hover { border: 1px solid #3B82F6; }
        """)

        self._build_ui()
        self._check_nas_status()
        self._cargar_miniatura()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # ---------------------------------------------------------
        # Fila 1: Cabecera (Estado del proyecto y Menú de Contexto)
        # ---------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_status = QLabel(self.project_data.get("project_status_name", self.tr("Active Project")))
        lbl_status.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(lbl_status)
        
        header_layout.addStretch()
        
        # Menú de Contexto (Los 3 puntitos)
        self.btn_options = QToolButton()
        self.btn_options.setText("⋮")
        self.btn_options.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_options.setStyleSheet("""
            QToolButton { background: transparent; color: #94A3B8; font-size: 20px; font-weight: bold; border: none; padding-bottom: 5px; } 
            QToolButton:hover { color: #F8FAFC; } 
            QToolButton::menu-indicator { image: none; }
        """)
        self.btn_options.setPopupMode(QToolButton.InstantPopup)
        
        self.options_menu = QMenu(self)
        # Inyectamos estilos para el menú y un pseudo-clase para el botón rojo
        self.options_menu.setStyleSheet("""
            QMenu { background-color: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; } 
            QMenu::item { padding: 8px 25px; } 
            QMenu::item:selected { background-color: #3B82F6; }
        """)
        
        # Acción Esporádica de Configuración
        action_config = QAction(self.tr("⚙️ Configure Project"), self)
        action_config.triggered.connect(lambda: self._abrir_kitsu_interno("/production-settings"))
        self.options_menu.addAction(action_config)
        
        # Acciones Peligrosas / Administrativas
        if self.user_role == "td":
            self.options_menu.addSeparator()
            action_archive = QAction(self.tr("📦 Archive Project"), self)
            self.options_menu.addAction(action_archive)
            self.options_menu.addSeparator()
            
            # Pseudo-truco en PySide6: Usar HTML en el texto de QAction suele ser ignorado en macOS/Windows, 
            # pero funciona en el estilo Fusion de Linux. Para asegurar el rojo, creamos un icono rojo dinámico.
            red_pixmap = QPixmap(12, 12)
            red_pixmap.fill(QColor("#EF4444"))
            action_delete = QAction(QIcon(red_pixmap), self.tr("Delete Project"), self)
            action_delete.triggered.connect(self._on_delete_requested)
            self.options_menu.addAction(action_delete)

        self.btn_options.setMenu(self.options_menu)
        header_layout.addWidget(self.btn_options)
        main_layout.addLayout(header_layout)

        # ---------------------------------------------------------
        # Fila 2: Miniatura del Proyecto (QStackedWidget)
        # ---------------------------------------------------------
        # ... (Mantén aquí el mismo código de self.thumb_stack y sus páginas que tenías) ...
        self.thumb_stack = QStackedWidget()
        self.thumb_stack.setFixedHeight(130)
        self.thumb_stack.setStyleSheet("QStackedWidget { background-color: #0F172A; border-radius: 8px; border: 1px solid #1E293B; }")
        
        self.page_placeholder = QWidget()
        placeholder_layout = QVBoxLayout(self.page_placeholder)
        placeholder_layout.setAlignment(Qt.AlignCenter)
        self.lbl_placeholder_text = QLabel(self.tr("AWESOME PROJECT"))
        self.lbl_placeholder_text.setStyleSheet("color: #64748B; font-size: 10px; font-weight: bold;")
        placeholder_layout.addWidget(self.lbl_placeholder_text)
        
        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet("border-radius: 8px; background-color: transparent;")
        
        self.thumb_stack.addWidget(self.page_placeholder)
        self.thumb_stack.addWidget(self.thumb_label)
        main_layout.addWidget(self.thumb_stack)

        # ---------------------------------------------------------
        # Fila 3 y 4: Títulos y Sincronización
        # ---------------------------------------------------------
        title_layout = QHBoxLayout()
        self.project_name = self.project_data.get("name", self.tr("Unknown Project"))
        self.lbl_title = QLabel(self.project_name)
        self.lbl_title.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: bold;")
        title_layout.addWidget(self.lbl_title)
        title_layout.addStretch()
        
        self.lbl_badge = QLabel(self.tr("Checking..."))
        self.lbl_badge.setAlignment(Qt.AlignCenter)
        self.lbl_badge.setStyleSheet("background-color: #0F172A; color: #94A3B8; border: 1px solid #334155; border-radius: 6px; padding: 2px 8px; font-size: 10px; font-weight: bold;")
        title_layout.addWidget(self.lbl_badge)
        main_layout.addLayout(title_layout)

        self.lbl_sync_status = QLabel(self.tr("🗄️ Checking..."))
        self.lbl_sync_status.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
        main_layout.addWidget(self.lbl_sync_status)

        # ---------------------------------------------------------
        # Fila 5: Matriz Dinámica de Botones (CTA) por Rol
        # ---------------------------------------------------------
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setContentsMargins(0, 5, 0, 0)
        self.actions_layout.setSpacing(10)
        main_layout.addLayout(self.actions_layout)

        # A) Construir el Split Button de Kitsu (Dropdown)
        self.btn_kitsu_dropdown = QToolButton()
        self.btn_kitsu_dropdown.setPopupMode(QToolButton.InstantPopup)
        self.btn_kitsu_dropdown.setCursor(Qt.PointingHandCursor)
        self.btn_kitsu_dropdown.setFixedHeight(35)
        
        kitsu_menu = QMenu(self)
        kitsu_menu.setStyleSheet("QMenu { background-color: #0F172A; color: #F8FAFC; border: 1px solid #334155; border-radius: 6px; } QMenu::item { padding: 8px 25px; } QMenu::item:selected { background-color: #3B82F6; }")
        
        # Deeplinks Divulgación Progresiva
        kitsu_menu.addAction("📦 To: Assets", lambda: self._abrir_kitsu_interno("/assets"))
        kitsu_menu.addAction("🎬 To: Shots", lambda: self._abrir_kitsu_interno("/shots"))
        kitsu_menu.addAction("🎞️ To: Sequences", lambda: self._abrir_kitsu_interno("/sequences"))
        kitsu_menu.addAction("✂️ To: Edit", lambda: self._abrir_kitsu_interno("/edits"))
        self.btn_kitsu_dropdown.setMenu(kitsu_menu)

        # B) Construir el Ghost Button de Watchtower
        self.btn_watchtower = QPushButton("🗼")
        self.btn_watchtower.setFixedSize(35, 35)
        self.btn_watchtower.setCursor(Qt.PointingHandCursor)
        self.btn_watchtower.setToolTip(self.tr("Open Watchtower Dashboard"))
        self.btn_watchtower.clicked.connect(self._on_watchtower_clicked)

        # C) Construir el CTA Primario del Hub (Wizard / Launch)
        self.btn_primary_action = QPushButton()
        self.btn_primary_action.setFixedHeight(35)
        self.btn_primary_action.setCursor(Qt.PointingHandCursor)

        # MATRIZ DE RENDERIZADO POR ROL
        if self.user_role == "td":
            # TD Layout: Kitsu Dropdown (Orange) + Watchtower
            self.btn_kitsu_dropdown.setText("Open in Kitsu ▼")
            self.btn_kitsu_dropdown.setStyleSheet("""
                QToolButton { background-color: #F97316; color: white; font-weight: bold; border-radius: 6px; padding: 0 15px; }
                QToolButton:hover { background-color: #EA580C; }
                QToolButton::menu-indicator { image: none; }
            """)
            self.btn_kitsu_dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            
            self.btn_watchtower.setStyleSheet("""
                QPushButton { background: transparent; border: 1px solid #334155; border-radius: 6px; font-size: 16px;}
                QPushButton:hover { background-color: #334155; }
            """)
            
            self.actions_layout.addWidget(self.btn_kitsu_dropdown)
            self.actions_layout.addWidget(self.btn_watchtower)
            self.btn_primary_action.hide() # El TD no usa el botón estándar primario aquí
            
        else:
            # PM & Artist Layout: Primary Action (Orange/Blue) + Kitsu Ghost + Watchtower Ghost
            self.btn_kitsu_dropdown.setText("🦊 ▼")
            self.btn_kitsu_dropdown.setStyleSheet("""
                QToolButton { background: transparent; color: #F97316; border: 1px solid #334155; border-radius: 6px; padding: 0 10px; font-weight: bold;}
                QToolButton:hover { background-color: rgba(249, 115, 22, 0.1); border-color: #F97316; }
                QToolButton::menu-indicator { image: none; }
            """)
            
            self.actions_layout.addWidget(self.btn_primary_action, stretch=1)
            self.actions_layout.addWidget(self.btn_kitsu_dropdown)
            
            if self.user_role == "manager":
                self.btn_watchtower.setStyleSheet("""
                    QPushButton { background: transparent; border: 1px solid #334155; border-radius: 6px; font-size: 16px;}
                    QPushButton:hover { background-color: #334155; }
                """)
                self.actions_layout.addWidget(self.btn_watchtower)
            else:
                self.btn_watchtower.hide() #

    def _abrir_kitsu_interno(self, sub_ruta: str):
        """Genera el deeplink absoluto y lo envía al WebContext nativo del Hub."""
        project_id = self.project_data.get("id")
        kitsu_url = self.config_factory.get_kitsu_api_url()
        
        if kitsu_url.endswith("/api"):
            kitsu_url = kitsu_url[:-4]
            
        full_url = f"{kitsu_url}/productions/{project_id}{sub_ruta}"
        
        main_win = self.window()
        if hasattr(main_win, 'abrir_kitsu'):
            main_win.abrir_kitsu(full_url)
        else:
            # Fallback seguro al navegador de OS
            QDesktopServices.openUrl(QUrl(full_url))
    
    def _abrir_ruta_kitsu(self, sub_ruta: str):
        """Enruta al usuario directamente a un módulo específico del proyecto en Kitsu."""
        project_id = self.project_data.get("id")
        host = getattr(self.auth, 'kitsu_host', '')
        url = self.kitsu_mgr.build_web_url(host, project_id, sub_ruta)
        if url: QDesktopServices.openUrl(QUrl(url))

    def _on_watchtower_clicked(self):
        """Enruta la petición de Watchtower al Orquestador pasándole la ruta física."""
        if self.project_dir:
            main_win = self.window()
            if hasattr(main_win, 'abrir_watchtower'):
                project_id = self.project_data.get("id", "")
                main_win.abrir_watchtower(self.project_dir)
        else:
            QMessageBox.warning(self, "Watchtower", self.tr("The project must be mounted on your disk to visualize Watchtower."))

    def _check_nas_status(self):
        """Actualiza estado y colores del botón Primario (Wizard / Launch / Install)."""
        p_name = self.project_data.get("name", "")
        p_code = self.project_data.get("code", "")
        self.project_dir = self.nas_mgr.resolve_project_dir(p_name, p_code)
        
        is_installed = False
        if self.config_factory and self.project_dir:
            installer = LocalInstaller(self.config_factory.get_workspace_root(), self.config_factory)
            is_installed = installer.verificar_instalacion(self.project_dir)

        if is_installed and self.project_dir:
            self.lbl_sync_status.setText(self.tr("🗄️ 🟢 Ready on Disk"))
            self.lbl_sync_status.setStyleSheet("color: #10B981; font-size: 12px; font-weight: bold;")
            blueprint = self.nas_mgr.get_project_blueprint(self.project_dir)
            self.lbl_badge.setText(blueprint.get("blender_version", "Blender"))
            
            # Setup Action Button
            if hasattr(self, 'btn_primary_action') and self.user_role != "td":
                if self.user_role == "manager":
                    self.btn_primary_action.setText(self.tr("Pipeline Wizard"))
                    self.btn_primary_action.setStyleSheet("background-color: #F59E0B; color: #0F172A; font-weight: bold; border-radius: 6px; border: none;")
                    try: self.btn_primary_action.clicked.disconnect()
                    except RuntimeError: pass
                    
                    if self.on_open_wizard_callback:
                        self.btn_primary_action.clicked.connect(lambda: self.on_open_wizard_callback(self.project_name))
                else:
                    self.btn_primary_action.setText(self.tr("Launch Project"))
                    self.btn_primary_action.setStyleSheet("background-color: #3B82F6; color: white; font-weight: bold; border-radius: 6px; border: none;")
                    try: self.btn_primary_action.clicked.disconnect()
                    except RuntimeError: pass
                    
                    self.btn_primary_action.clicked.connect(lambda: self._lanzar_blender(self.project_dir))
        else:
            self.lbl_sync_status.setText(self.tr("🗄️ ⚪ Cloud Only"))
            self.lbl_sync_status.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
            self.lbl_badge.setText(self.tr("Not Mounted"))
            
            # Setup Action Button
            if hasattr(self, 'btn_primary_action') and self.user_role != "td":
                self.btn_primary_action.setText(self.tr("Install Workspace ↓"))
                self.btn_primary_action.setStyleSheet("background-color: #10B981; color: #0F172A; font-weight: bold; border-radius: 6px; border: none;")
                try: self.btn_primary_action.clicked.disconnect()
                except RuntimeError: pass
                
                target_path = self.config_factory.get_workspace_root() / p_name.lower().replace(" ", "-")
                self.btn_primary_action.clicked.connect(lambda _, p=target_path, b=self.btn_primary_action: self._instalar_entorno(p, b))
    

    def _instalar_entorno(self, project_path: Path, boton: QPushButton):
        boton.setEnabled(False)
        boton.setText(self.tr("Installing..."))
        boton.setStyleSheet("background-color: #94A3B8; color: #0F172A; font-weight: bold; border-radius: 6px; border: none;")
        
        installer = LocalInstaller(self.config_factory.get_workspace_root(), self.config_factory)
        
        # Recuperamos credenciales SVN (vía VaultManager)
        vcs_user, vcs_pwd = "", ""
        if self.vault:
            vcs_config = self.config_factory.get_raw_config().get("vcs_engine", {})
            vcs_user = vcs_config.get("vcs_username", "admin")
            vcs_pwd = vcs_config.get("vcs_password", "admin123")

        self.install_worker = ProjectInstallWorker(installer, project_path, vcs_user, vcs_pwd, self.user_role)
        if self.status_callback:
            self.install_worker.progress_update.connect(self.status_callback)
        self.install_worker.finished_install.connect(self._on_install_finished)
        self.install_worker.start()

    def _on_install_finished(self, success: bool, msg: str):
        if success:
            if self.status_callback: self.status_callback(self.tr("✓ Workspace deployed"), "green")
            self._check_nas_status() # Refrescar botones
            if self.on_rebuild_callback: self.on_rebuild_callback()
        else:
            if self.status_callback: self.status_callback(self.tr("✗ Install Failed: {0}").format(msg), "red")
            QMessageBox.critical(self, self.tr("Deployment Error"), msg)
            if hasattr(self, 'btn_action'):
                self.btn_action.setEnabled(True)
                self.btn_action.setText(self.tr("Retry Install ↓"))

    def _lanzar_blender(self, project_path: Path):
        config_path = project_path / "local" / "project_config.json"
        if not config_path.exists():
            if self.status_callback: self.status_callback(self.tr("Error: config missing."), "red")
            return
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                local_config = json.load(f)
            blender_version = local_config.get("blender_version", "")
            
            installer = LocalInstaller(self.config_factory.get_workspace_root(), self.config_factory)
            os_name, _ = installer._get_os_info()
            blender_folder = installer.boveda_blender / f"blender-{blender_version}-{os_name}-x64"
            
            if os_name == "windows": blender_bin = blender_folder / "blender.exe"
            elif os_name == "macos": blender_bin = blender_folder / "Blender.app" / "Contents" / "MacOS" / "Blender"
            else: blender_bin = blender_folder / "blender"

            if not blender_bin.exists():
                if self.status_callback: self.status_callback(self.tr("Blender not found."), "red")
                return

            if self.status_callback: self.status_callback(self.tr("🚀 Launching Blender..."), "green")
            subprocess.Popen([str(blender_bin), "--", "--project_root", str(project_path)])
            
            main_window = self.window()
            if hasattr(main_window, 'registrar_instancia'):
                main_window.registrar_instancia(True)

        except Exception as e:
            if self.status_callback: self.status_callback(self.tr("Failed to launch: {0}").format(str(e)), "red")

    def _on_rebuild_clicked(self):
        # En lugar de solo recargar, forzamos la instalación de infraestructura base (Sandbox)
        p_name = self.project_data.get("name", "")
        target_path = self.config_factory.get_workspace_root() / p_name.lower().replace(" ", "-")
        
        self.btn_rebuild.setEnabled(False)
        self.btn_rebuild.setText(self.tr("Rebuilding..."))
        self._instalar_entorno(target_path, self.btn_rebuild)

    def _on_delete_requested(self):
        dialog = DeleteProjectDialog(self, self.project_name)
        if dialog.exec() == QDialog.Accepted:
            self._ejecutar_destruccion_nuclear(self.project_name)

    def _ejecutar_destruccion_nuclear(self, project_name: str):
        """Coordina la eliminación a través de los controladores y notifica al usuario."""
        project_id = self.project_data.get("id")
        folder_name = project_name.lower().replace(" ", "-")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            # 1. Kitsu DB
            success, msg = self.kitsu_mgr.delete_project(project_id)
            if not success: QMessageBox.warning(self, self.tr("Warning"), msg)
            try: subprocess.run(["docker", "exec", "openstudio_local_svn", "rm", "-rf", f"/home/svn/{folder_name}"], check=False)
            except Exception: pass
            if self.project_dir: self.nas_mgr.delete_project_folder(self.project_dir)
            
            QMessageBox.information(self, self.tr("Deleted"), self.tr("Project destroyed."))
            if self.on_rebuild_callback: self.on_rebuild_callback()

        finally:
            QApplication.restoreOverrideCursor()

    def _cargar_miniatura(self):
        project_id = self.project_data.get("id")
        token = getattr(self.auth, 'get_current_token', lambda: "")()
        base_url = getattr(self.auth, 'kitsu_host', "")
        
        self.worker = ProjectThumbnailWorker(self.kitsu_mgr, project_id, token, base_url)
        self.worker.image_downloaded.connect(self._on_thumbnail_ready)
        self.worker.error_occurred.connect(self._on_thumbnail_error)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _on_thumbnail_ready(self, img_bytes: bytes):
        image = QImage.fromData(img_bytes)
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            pixmap = pixmap.scaled(290, 140, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x_offset = (pixmap.width() - 290) // 2
            y_offset = (pixmap.height() - 140) // 2
            self.thumb_label.setPixmap(pixmap.copy(x_offset, y_offset, 290, 140))
            
            # Cambiar a la Página 1 (Mostrar imagen)
            self.thumb_stack.setCurrentIndex(1)
        else:
            self._on_thumbnail_error(self.tr("Archivo corrupto"))

    def _on_thumbnail_error(self, message: str):
        # Ante cualquier error o falta de imagen, forzamos la Página 0 (Placeholder visual)
        self.thumb_stack.setCurrentIndex(0)

```

--------------------------------------------------------------------------------

### Archivo: `ui/components/sidebar.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/sidebar.py
# Rol Arquitectónico: UI Component / Main Navigation & App Branding
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.1.0
# =========================================================================================

"""
Barra lateral izquierda (Sidebar) de altura completa.
Ahora actúa como el ancla principal de la marca corporativa (Logo + Nombre del Estudio),
además de contener las rutas de navegación dinámicas inyectables por el MasterLayout.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon
from pathlib import Path

class Sidebar(QFrame):
    def __init__(self, parent, config_factory):
        super().__init__(parent)
        self.config_factory = config_factory
        self.setObjectName("SidebarFrame") 
        self.setFixedWidth(240)
        self.sidebar_buttons = {}
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 20, 15, 20)
        self.main_layout.setSpacing(10)

        # 1. Inyección de Branding Unificado
        self._build_branding()

        # 2. Contenedor de Navegación
        self.nav_layout = QVBoxLayout()
        self.nav_layout.setSpacing(10)
        self.main_layout.addLayout(self.nav_layout)
        
        self.main_layout.addStretch()

    def _build_branding(self):
        self.branding_layout = QHBoxLayout()
        self.branding_layout.setContentsMargins(5, 0, 5, 25) # Espacio negativo inferior
        self.branding_layout.setSpacing(12)

        self.logo_icon = QLabel()
        logo_path = Path("assets/logo_topbar.png")
        if logo_path.exists():
            self.logo_icon.setPixmap(QPixmap(str(logo_path)).scaledToHeight(32, Qt.SmoothTransformation))
        self.branding_layout.addWidget(self.logo_icon)
        
        studio_name = self.config_factory.get_studio_name() or "OpenStudio"
        self.lbl_title = QLabel(self.tr("{0} Hub").format(studio_name))
        self.lbl_title.setObjectName("SidebarBrandTitle")
        # Estilo inline tolerado como base de fallback, idealmente se sobrescribe en QSS
        self.lbl_title.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: bold;")
        self.lbl_title.setWordWrap(True)
        self.branding_layout.addWidget(self.lbl_title)

        self.branding_layout.addStretch()
        self.main_layout.addLayout(self.branding_layout)

    def add_button(self, btn_id: str, texto: str, emoji: str, icon_name: str, callback, activo: bool = False):
        btn = QPushButton()
        icon_path = Path(f"assets/icons/{icon_name}")
        color_hex = "#F97316" if activo else "#94A3B8"
        
        if icon_path.exists():
            btn.setIcon(self._crear_icono_coloreado(icon_path, color_hex))
            btn.setIconSize(QSize(22, 22))
            btn.setText(f"   {texto}")
        else:
            btn.setText(f"{emoji}   {texto}")
            
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("SidebarNavActive" if activo else "SidebarNavInactive")
        btn.clicked.connect(callback)
        
        self.sidebar_buttons[btn_id] = btn
        self.nav_layout.addWidget(btn)

    def set_active_button(self, btn_id: str):
        for key, btn in self.sidebar_buttons.items():
            if key == btn_id:
                btn.setObjectName("SidebarNavActive")
            else:
                btn.setObjectName("SidebarNavInactive")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _crear_icono_coloreado(self, icon_path: Path, color_hex: str) -> QIcon:
        if not icon_path.exists(): return QIcon()
        try:
            with open(icon_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            svg_content = svg_content.replace('currentColor', color_hex)
            svg_content = svg_content.replace('#000000', color_hex)
            svg_content = svg_content.replace('#000"', f'{color_hex}"')
            svg_content = svg_content.replace("#000'", f"{color_hex}'")
            pixmap = QPixmap()
            pixmap.loadFromData(svg_content.encode('utf-8'), "SVG")
            return QIcon(pixmap)
        except Exception:
            return QIcon(str(icon_path))

```

--------------------------------------------------------------------------------

### Archivo: `ui/components/status_bar.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/status_bar.py
# =========================================================================================

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

class StatusBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self.setFixedHeight(35)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        
        self.lbl_status = QLabel(self.tr("🟢 Ready."))
        self.lbl_status.setObjectName("StatusText")
        layout.addWidget(self.lbl_status)

    def actualizar_status(self, mensaje: str, color: str = "white"):
        colores = {"green": "#10B981", "yellow": "#F59E0B", "red": "#EF4444", "gray": "#9CA3AF", "white": "#F8FAFC"}
        texto_color = colores.get(color, color)
        self.lbl_status.setText(mensaje)
        self.lbl_status.setStyleSheet(f"color: {texto_color};")

```

--------------------------------------------------------------------------------

### Archivo: `ui/components/task_card.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/task_card.py
# Rol Arquitectónico: UI Component / Reusable Task Card (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.8.0 (CTA Logic Matrix Fix)
# =========================================================================================

"""
Reusable visual component for Task Cards in the Artist Dashboard.
Uses ConfigFactory to resolve dynamic VFS local directory paths natively.
Implements a strict priority matrix for Call-To-Action (CTA) rendering.
"""

import webbrowser
import requests
from pathlib import Path

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QSizePolicy, QStackedWidget,
                               QWidget)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QIcon


class ThumbnailWorker(QThread):
    """QThread dedicado a la descarga de miniaturas por HTTP."""
    image_downloaded = Signal(bytes)
    error_occurred = Signal(str)

    def __init__(self, entity_id: str, token: str, host_url: str):
        super().__init__()
        self.entity_id = entity_id
        self.token = token
        self.host_url = host_url

    def run(self):
        if not self.entity_id:
            self.error_occurred.emit("No Entity ID Available")
            return

        try:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }

            entity_url = f"{self.host_url}/data/entities/{self.entity_id}"

            ent_resp = requests.get(entity_url, headers=headers, timeout=10)
            if ent_resp.status_code != 200:
                self.error_occurred.emit(f"Entity not found (HTTP {ent_resp.status_code})")
                return
            
            entity_data = ent_resp.json()
            preview_id = entity_data.get("preview_file_id")
            
            if not preview_id:
                self.error_occurred.emit("Entity has no preview image")
                return

            img_url = f"{self.host_url}/pictures/thumbnails/preview-files/{preview_id}.png"
            img_resp = requests.get(img_url, headers=headers, timeout=10)

            print(f"[DEBUG WORKER] Pidiendo imagen a: {img_url}")

            #headers = {"Authorization": f"Bearer {self.token}"}
            
            #response = requests.get(img_url, headers=headers, timeout=10)

            #print(f"[DEBUG WORKER] Respuesta: HTTP {response.status_code} | Peso: {len(response.content)} bytes")
            
            if img_resp.status_code == 200:
                self.image_downloaded.emit(img_resp.content)
            else:
                self.error_occurred.emit(f"Thumbnail not found (HTTP {img_resp.status_code})")
            
        except Exception as e:
            print(f"[UI THUMBNAIL ERROR] Download failed: {e}")
            self.error_occurred.emit("Network connection error")


class TaskCard(QFrame):
    def __init__(self, parent, task_data: dict, project_root: Path, is_installed: bool, 
                 auth_manager, config_factory, on_launch_callback, on_install_callback, 
                 can_work: bool = True, blocked_reason: str = "", **kwargs):
        super().__init__(parent, **kwargs)
        
        self.task_data = task_data
        self.project_root = project_root
        self.is_installed = is_installed
        self.auth_manager = auth_manager
        self.config_factory = config_factory
        
        self.can_work = can_work
        self.blocked_reason = blocked_reason
        
        self.on_launch_callback = on_launch_callback
        self.on_install_callback = on_install_callback
        
        if self.project_root and self.config_factory:
            vfs_local = self.config_factory.get_vfs_local_name()
            self.config_path = self.project_root / vfs_local / "project_config.json"
        else:
            self.config_path = None
        
        self.setObjectName("FloatingCard")
        self.setMinimumHeight(280)
        self.setMinimumWidth(380)

        self._build_ui()
        self._cargar_miniatura()

    def _obtener_color_texto_contraste(self, hex_color: str) -> str:
        """Calcula luminancia sRGB relativa para el contraste del badge."""
        if not hex_color: return "white"
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6: return "white"
        try:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#0F172A" if luminance > 0.5 else "#F8FAFC"
        except Exception:
            return "white"

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # ---------------------------------------------------------
        # Fila Superior: Título de Entidad y Tipo de Tarea
        # ---------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        entity_name = self.task_data.get('entity_name', self.task_data.get('name', 'Unknown Entity'))
        task_type = self.task_data.get('task_type_name', 'Task')
        title_text = f"{entity_name} - {task_type}"
        
        self.title_label = QLabel(title_text)
        self.title_label.setObjectName("H2Title")
        self.title_label.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        status_color = self.task_data.get("task_status_color", self.task_data.get("status_color", "#444444"))
        status_name = self.task_data.get("task_status_name", self.task_data.get("status_name", "TODO"))
        text_color_contraste = self._obtener_color_texto_contraste(status_color)
        
        self.status_badge = QLabel(status_name.upper())
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setFixedHeight(22)
        self.status_badge.setStyleSheet(f"""
            background-color: {status_color};
            color: {text_color_contraste};
            border-radius: 11px;
            font-size: 10px;
            font-weight: bold;
            padding: 0 10px;
        """)
        header_layout.addWidget(self.status_badge)
        main_layout.addLayout(header_layout)

        # ---------------------------------------------------------
        # Fila Central: Thumbnail Cinematográfico
        # ---------------------------------------------------------
        # self.thumb_frame = QFrame(self)
        # self.thumb_frame.setFixedHeight(160)
        # self.thumb_frame.setStyleSheet("background-color: #0B1120; border-radius: 8px;") 
        #
        # thumb_layout = QVBoxLayout(self.thumb_frame)
        # thumb_layout.setContentsMargins(5, 5, 5, 5)
        #
        # self.thumb_label = QLabel(self.tr("No Thumbnail Available"))
        # self.thumb_label.setObjectName("PlaceholderText")
        # self.thumb_label.setAlignment(Qt.AlignCenter)
        # self.thumb_label.setStyleSheet("color: #475569; font-style: italic; font-size: 12px;")
        # thumb_layout.addWidget(self.thumb_label)
        # main_layout.addWidget(self.thumb_frame)

        # 2. Miniatura Dinámica (QStackedWidget)
        self.thumb_stack = QStackedWidget()
        self.thumb_stack.setFixedHeight(140)
        self.thumb_stack.setStyleSheet("QStackedWidget { background-color: #0F172A; border-radius: 8px; border: 1px solid #1E293B; }")
        
        # --- Página 0: Placeholder Inteligente ---
        self.page_placeholder = QWidget()
        placeholder_layout = QVBoxLayout(self.page_placeholder)
        placeholder_layout.setAlignment(Qt.AlignCenter)
        placeholder_layout.setSpacing(10)
        
        self.lbl_placeholder_icon = QLabel()
        self.lbl_placeholder_icon.setAlignment(Qt.AlignCenter)
        
        # Resolver nombre de tarea a SVG
        task_type = self.task_data.get("task_type_name", "generic").lower()
        
        icon_map = {
            "storyboard": "task-storyboard.svg",
            "layout": "task-layout.svg",
            "modeling": "task-modeling.svg",
            "rigging": "task-rigging.svg",
            "animation": "task-animation.svg",
            "lighting": "task-lighting.svg",
            "compositing": "task-compositing.svg",
            "editorial": "task-editorial.svg",
            "edit": "task-editorial.svg"
        }
        
        svg_filename = icon_map.get(task_type, "task-generic.svg")
        icon_path = Path(f"assets/icons/{svg_filename}")
        
        if icon_path.exists():
            base_pixmap = QIcon(str(icon_path)).pixmap(55, 55)
            painter = QPainter(base_pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(base_pixmap.rect(), QColor("#64748B"))
            painter.end()
            self.lbl_placeholder_icon.setPixmap(base_pixmap)
        else:
            self.lbl_placeholder_icon.setText("⚙️")
            self.lbl_placeholder_icon.setStyleSheet("font-size: 40px; background: transparent; color: #64748B;")
            
        # Formatear el texto (ej: "ANIMATION PLACEHOLDER")
        safe_task_name = self.task_data.get("task_type_name", "TASK").upper()
        self.lbl_placeholder_text = QLabel(self.tr(f"{safe_task_name} TASK"))
        self.lbl_placeholder_text.setAlignment(Qt.AlignCenter)
        self.lbl_placeholder_text.setStyleSheet("color: #64748B; font-size: 10px; font-weight: bold; letter-spacing: 1px; background: transparent;")
        
        placeholder_layout.addStretch()
        placeholder_layout.addWidget(self.lbl_placeholder_icon)
        placeholder_layout.addWidget(self.lbl_placeholder_text)
        placeholder_layout.addStretch()
        
        # --- Página 1: Imagen Real ---
        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet("border-radius: 8px; background-color: transparent;")
        
        self.thumb_stack.addWidget(self.page_placeholder)
        self.thumb_stack.addWidget(self.thumb_label)
        
        main_layout.addWidget(self.thumb_stack)


        # ---------------------------------------------------------
        # Fila Inferior: Botones de Acción Modulares
        # ---------------------------------------------------------
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)

        task_url = self.task_data.get("task_url")
        if task_url:
            self.kitsu_btn = QPushButton(self.tr("Kitsu ↗"))
            self.kitsu_btn.setObjectName("LinkButton")
            self.kitsu_btn.setFixedSize(80, 36)
            self.kitsu_btn.setCursor(Qt.PointingHandCursor)
            self.kitsu_btn.setStyleSheet("""
                QPushButton#LinkButton { background-color: #1E293B; color: #94A3B8; border: 1px solid #334155; border-radius: 6px; font-size: 12px; }
                QPushButton#LinkButton:hover { background-color: #334155; color: #F8FAFC; }
            """)
            self.kitsu_btn.clicked.connect(lambda checked=False, u=task_url: webbrowser.open(u))
            btn_layout.addWidget(self.kitsu_btn)

        # Matriz Condicional de Renderizado del CTA Primario (Corregida)
        if not self.project_root:
            self.action_btn = QPushButton(self.tr("Folder Missing on NAS"))
            self.action_btn.setEnabled(False)
            self.action_btn.setStyleSheet("QPushButton { border: 1px solid #EF4444; color: #EF4444; background: transparent; border-radius: 6px; font-weight: bold; font-size: 13px; }")
        
        elif not self.can_work:
            # Prioridad Absoluta: Si está bloqueada, no importa si está instalada o no.
            msg = self.blocked_reason if self.blocked_reason else self.tr("Access Denied")
            self.action_btn = QPushButton(f"🔒 {msg}")
            self.action_btn.setEnabled(False)
            self.action_btn.setStyleSheet("QPushButton:disabled { border: 1px solid #475569; color: #94A3B8; background: transparent; border-radius: 6px; font-weight: bold; font-size: 13px; }")
        
        elif self.is_installed:
            self.action_btn = QPushButton(self.tr("Launch Project Environment"))
            self.action_btn.setCursor(Qt.PointingHandCursor)
            self.action_btn.setStyleSheet("""
                QPushButton { border: 1px solid #10B981; color: #10B981; background: transparent; border-radius: 6px; font-weight: bold; font-size: 13px; }
                QPushButton:hover { background-color: rgba(16, 185, 129, 0.1); }
            """)
            self.action_btn.clicked.connect(
                lambda checked=False: self.on_launch_callback(self.project_root, self.config_path, self.task_data)
            )
        
        else:
            self.action_btn = QPushButton(self.tr("Install Project Locally"))
            self.action_btn.setCursor(Qt.PointingHandCursor)
            self.action_btn.setStyleSheet("""
                QPushButton { border: 1px solid #F59E0B; color: #F59E0B; background: transparent; border-radius: 6px; font-weight: bold; font-size: 13px; }
                QPushButton:hover { background-color: rgba(245, 158, 11, 0.1); }
            """)
            self.action_btn.clicked.connect(
                lambda checked=False: self.on_install_callback(self.project_root, self.task_data)
            )

        self.action_btn.setFixedHeight(36)
        self.action_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_layout.addWidget(self.action_btn)

        main_layout.addLayout(btn_layout)

    def _cargar_miniatura(self):
        entity_id = self.task_data.get("entity_id")
        
        # 2. Extraemos el ID del archivo de previsualización de la entidad
        # preview_id = entity_data.get("preview_file_id")
        #
        # task_name = self.task_data.get('name', 'Unknown')
        # print(f"\n[DEBUG THUMB] Tarea: '{task_name}' | Preview ID extraído: {preview_id}")
        
        # Fallback por si Gazu devuelve la data aplanada
        # if not preview_id:
        #     print(f"[DEBUG THUMB] ❌ Cancelando descarga: preview_id es nulo o vacío.")
        #     preview_id = self.task_data.get("preview_file_id")

        if not entity_id:
            print(f"[DEBUG THUMB] ❌ Cancelando descarga: preview_id es nulo o vacío.")
            self._on_thumbnail_error("No preview image mapped")
            return

        token = self.auth_manager.get_current_token()
        base_url = self.auth_manager.kitsu_host
        
        self.worker = ThumbnailWorker(entity_id, token, base_url)
        self.worker.image_downloaded.connect(self._on_thumbnail_ready)
        self.worker.error_occurred.connect(self._on_thumbnail_error)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _on_thumbnail_ready(self, img_bytes: bytes):
        image = QImage.fromData(img_bytes)
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            pixmap = pixmap.scaled(self.thumb_stack.width(), self.thumb_stack.height(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.thumb_label.setPixmap(pixmap)
            self.thumb_label.setText("") 

            self.thumb_stack.setCurrentIndex(1)
        else:
            self._on_thumbnail_error(self.tr("Corrupted image format"))

    def _on_thumbnail_error(self, message: str):
        self.thumb_stack.setCurrentIndex(0)

```

--------------------------------------------------------------------------------

### Archivo: `ui/components/top_bar.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/components/top_bar.py
# Rol Arquitectónico: UI Component / Header (User Utilities)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.2.0
# =========================================================================================

"""
Header superior del Hub.
Diseño minimalista: Alojamiento exclusivo para utilidades de usuario alineadas a la derecha.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from pathlib import Path

class TopBar(QFrame):
    def __init__(self, parent, auth_manager, config_factory, on_logout):
        super().__init__(parent)
        self.auth = auth_manager
        self.config_factory = config_factory
        self.on_logout = on_logout
        
        self.setObjectName("TopBarFrame")
        self.setFixedHeight(65)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 0, 30, 0)
        layout.setSpacing(15)

        # Resorte expansivo para empujar todas las herramientas hacia la extrema derecha
        layout.addStretch()

        # --- NUEVO: Botón de Kitsu ---
        self.btn_kitsu = QPushButton("🦊 Kitsu")
        self.btn_kitsu.setFixedSize(85, 32)
        self.btn_kitsu.setCursor(Qt.PointingHandCursor)
        self.btn_kitsu.setStyleSheet("""
            QPushButton {
                background-color: #F97316; color: white; border: none; 
                font-weight: bold; border-radius: 6px;
            }
            QPushButton:hover { background-color: #EA580C; }
        """)
        self.btn_kitsu.clicked.connect(self._on_kitsu_clicked)
        layout.addWidget(self.btn_kitsu)
        # -----------------------------

        # Info de Usuario
        rol = self.auth.get_user_role().capitalize() if self.auth else "Offline"
        nombre_user = self.auth.user_data.get("first_name", "User") if self.auth and self.auth.user_data else "User"
        
        self.lbl_name = QLabel(self.tr("{0} ({1})").format(nombre_user, rol))
        self.lbl_name.setObjectName("TopBarUserLabel")
        self.lbl_name.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.lbl_name)

        # Iconos de Utilidad
        self.avatar_icon = QLabel()
        self.avatar_icon.setAlignment(Qt.AlignCenter)
        self.avatar_icon.setFixedSize(35, 35)
        avatar_path = Path("assets/icons/user.svg")
        if avatar_path.exists():
            self.avatar_icon.setPixmap(QPixmap(str(avatar_path)).scaledToHeight(20, Qt.SmoothTransformation))
        else:
            self.avatar_icon.setText("👤")
        layout.addWidget(self.avatar_icon)

        self.bell_icon = QLabel()
        self.bell_icon.setAlignment(Qt.AlignCenter)
        bell_path = Path("assets/icons/bell.svg")
        if bell_path.exists():
            self.bell_icon.setPixmap(QPixmap(str(bell_path)).scaledToHeight(18, Qt.SmoothTransformation))
        else:
            self.bell_icon.setText("🔔")
        self.bell_icon.setContentsMargins(10, 0, 15, 0)
        layout.addWidget(self.bell_icon)

        # Botón Logout
        self.btn_logout = QPushButton(self.tr("Log Out"))
        self.btn_logout.setObjectName("SecondaryButton")
        self.btn_logout.setFixedSize(80, 32)
        self.btn_logout.setCursor(Qt.PointingHandCursor)
        if self.on_logout:
            self.btn_logout.clicked.connect(self.on_logout)
        layout.addWidget(self.btn_logout)

    def _on_kitsu_clicked(self):
        """Busca el orquestador principal y dispara el cambio de vista."""
        main_win = self.window()
        if hasattr(main_win, 'abrir_kitsu'):
            main_win.abrir_kitsu()

```

--------------------------------------------------------------------------------

### Archivo: `ui/settings_tabs/__init__.py`

```python

```

--------------------------------------------------------------------------------

### Archivo: `ui/settings_tabs/tab_identity.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/settings_tabs/tab_identity.py
# Rol Arquitectónico: UI Component / Settings Tab
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0 (Extracted from widget_settings)
# =========================================================================================

"""
Sub-vista de configuración encargada de la Identidad del Estudio y la API.
Encapsula la interfaz y la lógica de sincronización asíncrona con Kitsu,
exponiendo métodos limpios de hidratación (cargar_datos) y extracción de payload.
"""

from pathlib import Path
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, 
                               QLineEdit, QFormLayout, QFileDialog)
from PySide6.QtCore import Qt, QThread, Signal

class SyncIdentityWorker(QThread):
    """Worker thread to handle the Kitsu network call for organisation metadata asynchronously."""
    finished_sync = Signal(dict)

    def __init__(self, auth_manager):
        super().__init__()
        self.auth_manager = auth_manager

    def run(self):
        identity_data = self.auth_manager.sync_studio_identity()
        self.finished_sync.emit(identity_data)


class TabIdentity(QWidget):
    # Señal para notificar al orquestador padre que hay cambios sin guardar
    modified = Signal()

    def __init__(self, auth_manager, status_callback, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.status_callback = status_callback
        
        self._is_loading = True
        self.pending_hero_image_path = None
        
        self._build_ui()
        self._conectar_senales()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Nombre del Estudio y Botón Sync
        name_layout = QHBoxLayout()
        self.entry_studio_name = self._crear_input(self.tr("e.g. Macuare Studio"))
        name_layout.addWidget(self.entry_studio_name)

        self.btn_sync_identity = QPushButton(self.tr("Sync from Kitsu"))
        self.btn_sync_identity.setObjectName("SecondaryButton")
        self.btn_sync_identity.setFixedSize(130, 35)
        self.btn_sync_identity.setCursor(Qt.PointingHandCursor)
        self.btn_sync_identity.clicked.connect(self._ejecutar_sincronizacion_identidad)
        name_layout.addWidget(self.btn_sync_identity)

        # URL de Kitsu
        self.entry_kitsu_url = self._crear_input(self.tr("e.g. https://kitsu.mydomain.com/api"))

        # Studio Hero Image
        hero_layout = QHBoxLayout()
        self.entry_hero_image = self._crear_input(self.tr("Select a PNG/JPG for the login background"))
        self.entry_hero_image.setReadOnly(True)
        hero_layout.addWidget(self.entry_hero_image)

        btn_browse_hero = QPushButton(self.tr("Browse..."))
        btn_browse_hero.setObjectName("SecondaryButton")
        btn_browse_hero.setFixedSize(90, 35)
        btn_browse_hero.clicked.connect(self._seleccionar_hero_image)
        hero_layout.addWidget(btn_browse_hero)

        # Ensamblaje en el Formulario
        layout.addRow(self._styled_label(self.tr("Studio Name:")), name_layout)
        layout.addRow(self._styled_label(self.tr("Kitsu API URL:")), self.entry_kitsu_url)
        layout.addRow(self._styled_label(self.tr("Studio Hero Image:")), hero_layout)

    def _crear_input(self, placeholder: str = "") -> QLineEdit:
        campo = QLineEdit()
        campo.setObjectName("FormInput")
        campo.setFixedHeight(35)
        campo.setPlaceholderText(placeholder)
        return campo

    def _styled_label(self, texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 13px;")
        return lbl

    def _conectar_senales(self):
        self.entry_studio_name.textChanged.connect(self._on_field_modified)
        self.entry_kitsu_url.textChanged.connect(self._on_field_modified)

    def _on_field_modified(self):
        if not self._is_loading:
            self.modified.emit()

    def _seleccionar_hero_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select Studio Hero Image"), "", self.tr("Images (*.png *.jpg *.jpeg)")
        )
        if file_path:
            self.entry_hero_image.setText(file_path)
            self.pending_hero_image_path = Path(file_path)
            self._on_field_modified()

    def _ejecutar_sincronizacion_identidad(self):
        self.btn_sync_identity.setEnabled(False)
        self.btn_sync_identity.setText(self.tr("Syncing..."))
        self.status_callback(self.tr("Connecting to Kitsu to pull production profile..."), "yellow")

        url = self.entry_kitsu_url.text().strip()
        if url:
            self.auth_manager.set_host(url)

        self.sync_worker = SyncIdentityWorker(self.auth_manager)
        self.sync_worker.finished_sync.connect(self._on_sync_identity_finished)
        self.sync_worker.finished.connect(self.sync_worker.deleteLater)
        self.sync_worker.start()

    def _on_sync_identity_finished(self, identity_data: dict):
        self.btn_sync_identity.setEnabled(True)
        self.btn_sync_identity.setText(self.tr("Sync from Kitsu"))
        
        if identity_data and "name" in identity_data:
            self.entry_studio_name.setText(identity_data["name"])
            self.status_callback(self.tr("✓ Studio identity synchronized from Kitsu successfully."), "green")
        else:
            self.status_callback(self.tr("✗ Failed to sync identity. Verify API URL or network connection."), "red")

    # ---------------------------------------------------------
    # PUBLIC API (Data-Down, Actions-Up)
    # ---------------------------------------------------------

    def cargar_datos(self, raw_config: dict):
        """Hidrata los inputs con los datos provistos por el Orquestador."""
        self._is_loading = True
        self.entry_studio_name.setText(raw_config.get("studio_profile", {}).get("name", ""))
        self.entry_kitsu_url.setText(raw_config.get("kitsu_production", {}).get("api_url", ""))
        self._is_loading = False

    def get_identity_payload(self) -> dict:
        """Devuelve el diccionario parcial para que el Orquestador lo guarde."""
        return {
            "studio_profile": {
                "name": self.entry_studio_name.text().strip()
            },
            "kitsu_production": {
                "api_url": self.entry_kitsu_url.text().strip()
            }
        }

```

--------------------------------------------------------------------------------

### Archivo: `ui/settings_tabs/tab_software.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/settings_tabs/tab_software.py
# Rol Arquitectónico: UI Component / Manifest View & Local Provisioning
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.5.0 (UI Pure Decoupling & ZIP Parsing)
# =========================================================================================

"""
Sub-vista de configuración purificada. Centraliza los controles en la tabla de la Bóveda.
Los checkboxes ahora interactúan directamente en la tabla y se permite cargar archivos 
.zip locales leyendo sus propiedades automáticamente.
"""

import re
import shutil
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QPushButton, QTreeWidget, QTreeWidgetItem, 
                               QFrame, QProgressBar, QFileDialog)
from PySide6.QtCore import Qt, Signal

# Importación de la lógica separada del Core
from core.addon_inspector import AddonInspector
from core.provisioning_workers import (RepoFolderFetcherWorker, RepoFileFetcherWorker, 
                                       BlenderDirectDownloadWorker, StudioToolsFetchWorker)


class TabSoftware(QWidget):
    modified = Signal()

    def __init__(self, parent, vault_manager, status_callback):
        super().__init__(parent)
        self._is_loading = True
        self.vault_manager = vault_manager
        self.status_callback = status_callback
        self.manifest_data = {}
        
        self._folder_worker = None
        self._file_worker = None
        self._download_worker = None
        self._fetch_worker = None

        self._build_ui()
        self._conectar_crawler_inicial()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)

        # -----------------------------------------------------------------------------
        # 1. EXPLORADOR REMOTO
        # -----------------------------------------------------------------------------
        repo_browser_frame = QFrame()
        repo_browser_frame.setStyleSheet("background-color: #1E293B; border-radius: 6px; border: 1px solid #334155;")
        browser_layout = QVBoxLayout(repo_browser_frame)
        browser_layout.setContentsMargins(15, 15, 15, 15)

        lbl_section_title = QLabel(self.tr("🌐 Official Remote Repository Explorer (download.blender.org)"))
        lbl_section_title.setStyleSheet("color: #F8FAFC; font-weight: bold; font-size: 13px; border: none; margin-bottom: 5px;")
        browser_layout.addWidget(lbl_section_title)

        selectors_layout = QHBoxLayout()
        
        lbl_rem_folder = QLabel(self.tr("Folder:"))
        lbl_rem_folder.setStyleSheet("color: #94A3B8; border: none; font-weight: bold;")
        selectors_layout.addWidget(lbl_rem_folder)

        self.combo_remote_folders = QComboBox()
        self.combo_remote_folders.setFixedHeight(35)
        self.combo_remote_folders.setFixedWidth(150)
        self.combo_remote_folders.setStyleSheet("QComboBox { background-color: #0F172A; color: white; border: 1px solid #475569; padding-left: 5px; }")
        self.combo_remote_folders.currentTextChanged.connect(self._on_remote_folder_changed)
        selectors_layout.addWidget(self.combo_remote_folders)

        lbl_rem_file = QLabel(self.tr("Package:"))
        lbl_rem_file.setStyleSheet("color: #94A3B8; border: none; font-weight: bold; margin-left: 10px;")
        selectors_layout.addWidget(lbl_rem_file)

        self.combo_remote_files = QComboBox()
        self.combo_remote_files.setFixedHeight(35)
        self.combo_remote_files.setStyleSheet("QComboBox { background-color: #0F172A; color: white; border: 1px solid #475569; padding-left: 5px; }")
        selectors_layout.addWidget(self.combo_remote_files, stretch=1)

        btn_refresh_repo = QPushButton(self.tr("🔄 Sync"))
        btn_refresh_repo.setObjectName("SecondaryButton")
        btn_refresh_repo.setFixedSize(80, 35)
        btn_refresh_repo.clicked.connect(self._conectar_crawler_inicial)
        selectors_layout.addWidget(btn_refresh_repo)

        browser_layout.addLayout(selectors_layout)

        buttons_layout = QHBoxLayout()
        self.btn_download_official = QPushButton(self.tr("📥 Download Selected Package to Vault"))
        self.btn_download_official.setStyleSheet("background-color: #4F46E5; color: white; font-weight: bold; border-radius: 6px; border: none;")
        self.btn_download_official.setFixedHeight(35)
        self.btn_download_official.clicked.connect(self._disparar_descarga_blender)
        buttons_layout.addWidget(self.btn_download_official, stretch=1)

        browser_layout.addLayout(buttons_layout)
        main_layout.addWidget(repo_browser_frame)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background-color: #0F172A; border: none; } QProgressBar::chunk { background-color: #10B981; }")
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # -----------------------------------------------------------------------------
        # 2. EDITOR DEL MANIFIESTO DE SOFTWARE Y HERRAMIENTAS
        # -----------------------------------------------------------------------------
        manifest_frame = QFrame()
        manifest_frame.setStyleSheet("background-color: transparent;")
        manifest_layout = QVBoxLayout(manifest_frame)
        manifest_layout.setContentsMargins(0, 10, 0, 0)

        # Barra de Control de Tabla Integrada
        control_layout = QHBoxLayout()
        lbl_active_v = QLabel(self.tr("Target Context (Active Blender Version):"))
        lbl_active_v.setStyleSheet("color: #10B981; font-weight: bold; font-size: 14px;")
        control_layout.addWidget(lbl_active_v)

        self.combo_versions = QComboBox()
        self.combo_versions.setFixedHeight(35)
        self.combo_versions.setFixedWidth(120)
        self.combo_versions.setStyleSheet("QComboBox { background-color: #1E293B; color: white; border: 1px solid #475569; padding-left: 5px; font-weight: bold; }")
        self.combo_versions.currentTextChanged.connect(self._redibujar_arbol_componentes)
        control_layout.addWidget(self.combo_versions)

        control_layout.addStretch()

        self.btn_fetch_studio_tools = QPushButton(self.tr("🚀 Auto-Fetch Blender Studio Tools"))
        self.btn_fetch_studio_tools.setStyleSheet("background-color: #06B6D4; color: white; font-weight: bold; border-radius: 6px; border: none;")
        self.btn_fetch_studio_tools.setFixedSize(250, 35)
        self.btn_fetch_studio_tools.clicked.connect(self._disparar_fetch_studio_tools)
        control_layout.addWidget(self.btn_fetch_studio_tools)

        manifest_layout.addLayout(control_layout)

        # Tabla del Manifiesto interactiva
        self.tree_manifest = QTreeWidget()
        self.tree_manifest.setColumnCount(4)
        self.tree_manifest.setHeaderLabels([self.tr("Component / Addon"), self.tr("Version"), self.tr("Description"), self.tr("Mandatory")])
        self.tree_manifest.setColumnWidth(0, 220)
        self.tree_manifest.setColumnWidth(1, 80)
        self.tree_manifest.setColumnWidth(2, 350)
        self.tree_manifest.setStyleSheet("""
            QTreeWidget { background-color: #1E293B; border: 1px solid #334155; border-radius: 8px; color: #F8FAFC; }
            QHeaderView::section { background-color: #0F172A; color: #94A3B8; font-weight: bold; padding: 5px; border: 1px solid #334155; }
        """)
        self.tree_manifest.itemChanged.connect(self._on_tree_item_changed)
        manifest_layout.addWidget(self.tree_manifest, stretch=1)

        # Inyector de ZIP Locales
        inject_layout = QHBoxLayout()
        self.btn_load_local_zip = QPushButton(self.tr("📂 Add / Load Local .zip Addon"))
        self.btn_load_local_zip.setObjectName("SecondaryButton")
        self.btn_load_local_zip.setFixedHeight(35)
        self.btn_load_local_zip.clicked.connect(self._inyectar_zip_local)
        inject_layout.addWidget(self.btn_load_local_zip)
        
        inject_layout.addStretch()
        manifest_layout.addLayout(inject_layout)

        main_layout.addWidget(manifest_frame, stretch=1)

    def _on_field_modified(self):
        if not self._is_loading:
            self.modified.emit()

    # ---------------------------------------------------------
    # RENDER Y EDICIÓN INTERACTIVA DEL ÁRBOL
    # ---------------------------------------------------------

    def _redibujar_arbol_componentes(self):
        self.tree_manifest.blockSignals(True)
        self.tree_manifest.clear()
        version_activa = self.combo_versions.currentText()
        
        if not version_activa or version_activa not in self.manifest_data:
            self.tree_manifest.blockSignals(False)
            return

        bloque_categorias = self.manifest_data[version_activa]
        
        for cat_name, items in bloque_categorias.items():
            cat_item = QTreeWidgetItem(self.tree_manifest)
            cat_item.setText(0, f"{cat_name.upper()}")
            cat_item.setForeground(0, Qt.green)
            cat_item.setExpanded(True)
            
            for item_name, data in items.items():
                child = QTreeWidgetItem(cat_item)
                child.setText(0, item_name)
                child.setText(1, str(data.get("version", "1.0")))
                child.setText(2, data.get("description", ""))
                
                # Checkbox interactivo en la columna 3
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(3, Qt.Checked if data.get("mandatory", False) else Qt.Unchecked)
                
                # Guardar info en los UserRoles para poder actualizar el dict al hacer click
                child.setData(0, Qt.UserRole, cat_name)
                child.setData(1, Qt.UserRole, item_name)

        self.tree_manifest.blockSignals(False)

    def _on_tree_item_changed(self, item: QTreeWidgetItem, column: int):
        """Atrapa el click del usuario en el checkbox Mandatory y actualiza el dict en caliente."""
        if column == 3:
            cat_name = item.data(0, Qt.UserRole)
            item_name = item.data(1, Qt.UserRole)
            version_activa = self.combo_versions.currentText()
            
            if cat_name and item_name and version_activa in self.manifest_data:
                is_checked = (item.checkState(3) == Qt.Checked)
                self.manifest_data[version_activa][cat_name][item_name]["mandatory"] = is_checked
                self._on_field_modified()

    # ---------------------------------------------------------
    # OPERACIONES AUTOMATIZADAS
    # ---------------------------------------------------------

    def _conectar_crawler_inicial(self):
        self._folder_worker = RepoFolderFetcherWorker()
        self._folder_worker.folders_ready.connect(self._on_remote_folders_loaded)
        self._folder_worker.status.connect(self.status_callback)
        self._folder_worker.start()

    def _on_remote_folders_loaded(self, folder_list: list):
        self.combo_remote_folders.blockSignals(True)
        self.combo_remote_folders.clear()
        self.combo_remote_folders.addItems(folder_list)
        self.combo_remote_folders.blockSignals(False)
        
        if self._folder_worker:
            self._folder_worker.deleteLater()
            self._folder_worker = None
        
        if folder_list:
            self._on_remote_folder_changed(self.combo_remote_folders.currentText())

    def _on_remote_folder_changed(self, target_folder: str):
        if not target_folder: return
        if self._file_worker and self._file_worker.isRunning():
            self._file_worker.terminate()

        self._file_worker = RepoFileFetcherWorker(target_folder)
        self._file_worker.files_ready.connect(self._on_remote_files_loaded)
        self._file_worker.status.connect(self.status_callback)
        self._file_worker.start()

    def _on_remote_files_loaded(self, file_list: list):
        self.combo_remote_files.clear()
        self.combo_remote_files.addItems(file_list)
        if self._file_worker:
            self._file_worker.deleteLater()
            self._file_worker = None

    def _disparar_descarga_blender(self):
        folder = self.combo_remote_folders.currentText()
        filename = self.combo_remote_files.currentText()

        if not folder or not filename:
            return

        vault_root = self.vault_manager.manifest_path.parent
        blender_target_dir = vault_root / "blender_versions"

        self.btn_download_official.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self._download_worker = BlenderDirectDownloadWorker(folder, filename, blender_target_dir)
        self._download_worker.progress.connect(self.progress_bar.setValue)
        self._download_worker.status.connect(self.status_callback)
        self._download_worker.finished.connect(self._on_direct_download_finished)
        self._download_worker.start()

    def _on_direct_download_finished(self, exito: bool, filename: str):
        self.btn_download_official.setEnabled(True)
        self.progress_bar.hide()

        if exito and filename:
            match = re.search(r'blender-(\d+\.\d+\.\d+)', filename.lower())
            detected_version = match.group(1) if match else "4.2.0"
            
            if detected_version not in self.manifest_data:
                self.manifest_data[detected_version] = {"addons": {}, "templates": {}}
                self.combo_versions.blockSignals(True)
                self.combo_versions.clear()
                self.combo_versions.addItems(list(self.manifest_data.keys()))
                self.combo_versions.setCurrentText(detected_version)
                self.combo_versions.blockSignals(False)
                self._redibujar_arbol_componentes()
                self._on_field_modified()

        if self._download_worker:
            self._download_worker.deleteLater()
            self._download_worker = None

    def _disparar_fetch_studio_tools(self):
        version = self.combo_versions.currentText()
        if not version:
            return

        # Extraemos la ruta física de la Bóveda de forma dinámica pero segura
        vault_root = self.vault_manager.config_factory.get_vault_path()

        self.btn_fetch_studio_tools.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        # Usamos el worker encapsulado inyectándole la ruta y la versión. 
        self._fetch_worker = StudioToolsFetchWorker(vault_root, version)
        
        # Conectamos las señales 
        self._fetch_worker.status_update.connect(self.status_callback)
        self._fetch_worker.progress_updated.connect(self.progress_bar.setValue) 
        self._fetch_worker.finished_packing.connect(self._on_studio_tools_finished)
        self._fetch_worker.error_occurred.connect(self._on_studio_tools_error)
        
        # EL SECRETO DE QT: Usar la señal nativa 'finished' para la limpieza
        self._fetch_worker.finished.connect(self._cleanup_fetch_worker)
        
        self._fetch_worker.start()

    def _on_studio_tools_finished(self, herramientas_nuevas: dict):
        """Se ejecuta cuando el hilo de descarga e instalación termina con éxito."""
        self.btn_fetch_studio_tools.setEnabled(True)
        self.progress_bar.hide()

        version_activa = self.combo_versions.currentText()
        
        # 1. Como el Worker guardó los add-ons físicamente en el disco (NAS),
        # obligamos al VaultManager a recargar el archivo JSON para sincronizar la RAM.
        #inventario_actualizado = self.vault_manager.cargar_inventario()
        #if inventario_actualizado:
        #    self.cargar_datos(inventario_actualizado)
        
        if version_activa and version_activa in self.manifest_data:
            if "addons" not in self.manifest_data[version_activa]:
                self.manifest_data[version_activa]["addons"] = {}

            self.manifest_data[version_activa]["addons"].update(herramientas_nuevas)

        # 2. Disparamos la señal de modificación para que el Orquestador principal 
        # ilumine el botón de "Guardar Cambios" y el usuario sepa que hay data nueva.
        self._redibujar_arbol_componentes()
        self._on_field_modified()
        # NOTA: ¡Ya no destruimos el hilo aquí!

    def _on_studio_tools_error(self, error: str):
        """Se ejecuta si el worker reporta un fallo de red o validación."""
        self.btn_fetch_studio_tools.setEnabled(True)
        self.progress_bar.hide()
        self.status_callback(self.tr("Studio Tools Fetch Failed: {0}").format(error), "red")
        # NOTA: ¡Ya no destruimos el hilo aquí!

    def _cleanup_fetch_worker(self):
        """Destruye el hilo de forma segura SOLO cuando su método run() ha terminado por completo."""
        if self._fetch_worker:
            self._fetch_worker.deleteLater()
            self._fetch_worker = None

    # ---------------------------------------------------------
    # OPERACIÓN MANUAL: CARGA DE ZIP
    # ---------------------------------------------------------

    def _inyectar_zip_local(self):
        version_activa = self.combo_versions.currentText()
        if not version_activa:
            self.status_callback(self.tr("✗ Please select a Target Context (Blender Version) first."), "yellow")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Select Addon .zip"), "", "ZIP Files (*.zip)")
        if not file_path:
            return

        zip_path = Path(file_path)
        meta = AddonInspector.inspect_zip(zip_path)

        if not meta or meta["name"] == "unknown_addon":
            self.status_callback(self.tr("✗ Invalid Addon: No blender_manifest.toml or bl_info found inside ZIP."), "red")
            return

        addon_name = meta["name"]
        addon_ver = meta["version"]
        desc = meta["description"]

        # Copiar y renombrar a la Bóveda con la convención estricta {nombre}-{version}.zip
        vault_root = self.vault_manager.manifest_path.parent
        addons_dir = vault_root / "addons"
        addons_dir.mkdir(parents=True, exist_ok=True)
        
        target_zip_name = f"{addon_name}-{addon_ver}.zip"
        target_zip_path = addons_dir / target_zip_name
        
        if not target_zip_path.exists():
            shutil.copy2(zip_path, target_zip_path)
            self.status_callback(self.tr("✓ Addon '{0}' imported to Vault successfully.").format(target_zip_name), "green")
        else:
            self.status_callback(self.tr("• Addon '{0}' already exists in Vault. Cache utilized.").format(target_zip_name), "yellow")

        if "addons" not in self.manifest_data[version_activa]:
            self.manifest_data[version_activa]["addons"] = {}

        self.manifest_data[version_activa]["addons"][addon_name] = {
            "version": addon_ver,
            "description": desc[:60] + "..." if len(desc) > 60 else desc,
            "mandatory": False,
            "requires": []
        }

        self._redibujar_arbol_componentes()
        self._on_field_modified()

    # ---------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------

    def cargar_datos(self, manifest_config: dict):
        self._is_loading = True
        self.manifest_data = {}

        for key, val in manifest_config.items():
            if isinstance(val, dict):
                raw_version = val.get("blender_version") or key
                clean_version = str(raw_version).lstrip("vV ")
                
                categories_block = val.get("categories") if "categories" in val else val
                if isinstance(categories_block, dict):
                    self.manifest_data[clean_version] = categories_block

        self.combo_versions.blockSignals(True)
        self.combo_versions.clear()
        self.combo_versions.addItems(list(self.manifest_data.keys()))
        self.combo_versions.blockSignals(False)
        
        self._redibujar_arbol_componentes()
        self._is_loading = False

    def get_software_payload(self) -> dict:
        full_payload = {}
        for version, categories in self.manifest_data.items():
            full_payload[version] = {
                "blender_version": version,
                "categories": categories
            }
        return full_payload

```

--------------------------------------------------------------------------------

### Archivo: `ui/settings_tabs/tab_topography.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/settings_tabs/tab_topography.py
# Rol Arquitectónico: UI Component / Settings Tab
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0 (Extracted from widget_settings)
# =========================================================================================

"""
Sub-vista de configuración encargada de la Topografía Semántica del Proyecto (VFS).
Aísla la UI y el mapeo de los nombres de carpetas personalizados del estudio para
hacerlos compatibles con el pipeline unificado de Blender Studio.
"""

from PySide6.QtWidgets import QWidget, QLineEdit, QFormLayout, QLabel
from PySide6.QtCore import Qt, Signal


class TabTopography(QWidget):
    # Señal para notificar cambios en caliente al orquestador padre
    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_loading = True
        
        self._build_ui()
        self._conectar_senales()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lbl_desc = QLabel(self.tr("Map Blender Studio Tool's core logic to your custom naming conventions.\nThe Hub relies on VFS Keys, allowing you to use numerical prefixes safely."))
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 12px; margin-bottom: 10px;")
        layout.addRow("", lbl_desc)

        # Variables Core del VFS
        self.entry_topo_svn = self._crear_input(self.tr("e.g. 02_production (Maps to 'svn')"))
        self.entry_topo_shared = self._crear_input(self.tr("e.g. 04_shared_data (Maps to 'shared')"))
        self.entry_topo_local = self._crear_input(self.tr("e.g. 06_local_cache (Maps to 'local')"))
        self.entry_topo_pipeline = self._crear_input(self.tr("e.g. 05_studio_config (Maps to 'pipeline')"))

        layout.addRow(self._styled_label(self.tr("Active Workspace [vfs_svn]:")), self.entry_topo_svn)
        layout.addRow(self._styled_label(self.tr("NAS Cache / Refs [vfs_shared]:")), self.entry_topo_shared)
        layout.addRow(self._styled_label(self.tr("Sandbox Cache [vfs_local]:")), self.entry_topo_local)
        layout.addRow(self._styled_label(self.tr("Hub Database [vfs_pipeline]:")), self.entry_topo_pipeline)

        # Carpetas Personalizadas Adicionales (Solo NAS)
        lbl_custom = QLabel(self.tr("Additional Organization Folders (NAS Only)"))
        lbl_custom.setStyleSheet("color: #F8FAFC; font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
        layout.addRow("", lbl_custom)

        self.entry_topo_custom1 = self._crear_input(self.tr("e.g. 01_Brief_and_Refs"))
        self.entry_topo_custom2 = self._crear_input(self.tr("e.g. 03_renders"))

        layout.addRow(self._styled_label(self.tr("Custom Folder 1:")), self.entry_topo_custom1)
        layout.addRow(self._styled_label(self.tr("Custom Folder 2:")), self.entry_topo_custom2)

    def _crear_input(self, placeholder: str = "") -> QLineEdit:
        campo = QLineEdit()
        campo.setObjectName("FormInput")
        campo.setFixedHeight(35)
        campo.setPlaceholderText(placeholder)
        return campo

    def _styled_label(self, texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 13px;")
        return lbl

    def _conectar_senales(self):
        self.entry_topo_svn.textChanged.connect(self._on_field_modified)
        self.entry_topo_shared.textChanged.connect(self._on_field_modified)
        self.entry_topo_local.textChanged.connect(self._on_field_modified)
        self.entry_topo_pipeline.textChanged.connect(self._on_field_modified)
        self.entry_topo_custom1.textChanged.connect(self._on_field_modified)
        self.entry_topo_custom2.textChanged.connect(self._on_field_modified)

    def _on_field_modified(self):
        if not self._is_loading:
            self.modified.emit()

    # ---------------------------------------------------------
    # PUBLIC API (Data-Down, Actions-Up)
    # ---------------------------------------------------------

    def cargar_datos(self, topo_config: dict):
        """Hidrata los cuadros de texto con las variables semánticas guardadas."""
        self._is_loading = True
        
        self.entry_topo_svn.setText(topo_config.get("vfs_svn", "svn"))
        self.entry_topo_shared.setText(topo_config.get("vfs_shared", "shared"))
        self.entry_topo_local.setText(topo_config.get("vfs_local", "local"))
        self.entry_topo_pipeline.setText(topo_config.get("vfs_pipeline", "pipeline"))
        
        custom_dirs = topo_config.get("custom_dirs", [])
        self.entry_topo_custom1.clear()
        self.entry_topo_custom2.clear()
        
        if len(custom_dirs) > 0:
            self.entry_topo_custom1.setText(custom_dirs[0])
        if len(custom_dirs) > 1:
            self.entry_topo_custom2.setText(custom_dirs[1])
            
        self._is_loading = False

    def get_topography_payload(self) -> dict:
        """Devuelve el sub-bloque serializable para conformar el JSON global."""
        custom_dirs = []
        if self.entry_topo_custom1.text().strip():
            custom_dirs.append(self.entry_topo_custom1.text().strip())
        if self.entry_topo_custom2.text().strip():
            custom_dirs.append(self.entry_topo_custom2.text().strip())

        return {
            "project_topography": {
                "vfs_svn": self.entry_topo_svn.text().strip() or "svn",
                "vfs_shared": self.entry_topo_shared.text().strip() or "shared",
                "vfs_local": self.entry_topo_local.text().strip() or "local",
                "vfs_pipeline": self.entry_topo_pipeline.text().strip() or "pipeline",
                "custom_dirs": custom_dirs
            }
        }

```

--------------------------------------------------------------------------------

### Archivo: `ui/settings_tabs/tab_vault.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/settings_tabs/tab_vault.py
# Rol Arquitectónico: UI Component / Settings Tab
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0 (Extracted from widget_settings)
# =========================================================================================

"""
Sub-vista de configuración encargada del almacenamiento físico en el NAS.
Aísla la UI y los cuadros de diálogo del sistema operativo (QFileDialog) para
el mapeo del directorio de proyectos y la bóveda de software inmutable.
"""

from pathlib import Path
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, 
                               QLineEdit, QFormLayout, QFileDialog)
from PySide6.QtCore import Qt, QDir, Signal

class TabVault(QWidget):
    # Señal para notificar cambios en caliente al orquestador padre
    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_loading = True
        
        self._build_ui()
        self._conectar_senales()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Campo de Directorio de Proyectos
        proj_layout = QHBoxLayout()
        self.entry_projects_path = self._crear_input(self.tr("e.g. Z:/studio_projects"))
        self.entry_projects_path.setReadOnly(True)
        proj_layout.addWidget(self.entry_projects_path)

        btn_browse_proj = QPushButton(self.tr("Browse..."))
        btn_browse_proj.setObjectName("SecondaryButton")
        btn_browse_proj.setFixedSize(90, 35)
        btn_browse_proj.clicked.connect(self._seleccionar_proyectos)
        proj_layout.addWidget(btn_browse_proj)

        layout.addRow(self._styled_label(self.tr("Projects Directory:")), proj_layout)

        # Campo de Directorio de la Bóveda (Vault)
        path_layout = QHBoxLayout()
        self.entry_vault_path = self._crear_input(self.tr("e.g. Z:/studio_projects/openstudio_vault"))
        self.entry_vault_path.setReadOnly(True)
        path_layout.addWidget(self.entry_vault_path)

        btn_browse_vault = QPushButton(self.tr("Browse..."))
        btn_browse_vault.setObjectName("SecondaryButton")
        btn_browse_vault.setFixedSize(90, 35)
        btn_browse_vault.clicked.connect(self._seleccionar_boveda)
        path_layout.addWidget(btn_browse_vault)

        layout.addRow(self._styled_label(self.tr("Vault Directory:")), path_layout)

        # Texto explicativo de infraestructura
        lbl_desc = QLabel(self.tr("Physical storage paths on the NAS.\nThe Projects Directory holds live production assets, while the Vault contains immutable software components and engine templates."))
        lbl_desc.setStyleSheet("color: #64748B; font-size: 12px;")
        layout.addRow("", lbl_desc)

    def _crear_input(self, placeholder: str = "") -> QLineEdit:
        campo = QLineEdit()
        campo.setObjectName("FormInput")
        campo.setFixedHeight(35)
        campo.setPlaceholderText(placeholder)
        return campo

    def _styled_label(self, texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 13px;")
        return lbl

    def _conectar_senales(self):
        self.entry_projects_path.textChanged.connect(self._on_field_modified)
        self.entry_vault_path.textChanged.connect(self._on_field_modified)

    def _on_field_modified(self):
        if not self._is_loading:
            self.modified.emit()

    def _seleccionar_proyectos(self):
        start_dir = QDir.homePath()
        actual = self.entry_projects_path.text()
        if actual and Path(actual).exists():
            start_dir = actual
            
        dir_path = QFileDialog.getExistingDirectory(self, self.tr("Select Projects Root Directory"), start_dir)
        if dir_path:
            self.entry_projects_path.setText(dir_path)
            # Autocompletado inteligente si la bóveda está vacía
            if not self.entry_vault_path.text():
                self.entry_vault_path.setText(str(Path(dir_path) / "openstudio_vault"))

    def _seleccionar_boveda(self):
        start_dir = QDir.homePath()
        actual = self.entry_vault_path.text()
        proj_dir = self.entry_projects_path.text()
        
        if actual and Path(actual).exists():
            start_dir = str(Path(actual).parent)
        elif proj_dir and Path(proj_dir).exists():
            start_dir = proj_dir
            
        dir_path = QFileDialog.getExistingDirectory(self, self.tr("Select NAS Root (Vault)"), start_dir)
        if dir_path:
            chosen_path = Path(dir_path)
            if chosen_path.name != "openstudio_vault":
                chosen_path = chosen_path / "openstudio_vault"
                
            self.entry_vault_path.setText(str(chosen_path))

    # ---------------------------------------------------------
    # PUBLIC API (Data-Down, Actions-Up)
    # ---------------------------------------------------------

    def cargar_datos(self, projects_path: str, vault_path: str):
        """Hidrata los cuadros de texto con las rutas procesadas por el backend."""
        self._is_loading = True
        self.entry_projects_path.setText(projects_path)
        self.entry_vault_path.setText(vault_path)
        self._is_loading = False

    def get_vault_payload(self) -> dict:
        """Devuelve las variables parciales listas para la persistencia atómica."""
        return {
            "infrastructure_topology": {
                "vault_path": self.entry_vault_path.text().strip()
            },
            "vcs_engine": {
                "local_workspace_root": self.entry_projects_path.text().strip()
            }
        }

```

--------------------------------------------------------------------------------

### Archivo: `ui/settings_tabs/tab_vcs.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/settings_tabs/tab_vcs.py
# Rol Arquitectónico: UI Component / Settings Tab
# =========================================================================================

import subprocess
from PySide6.QtWidgets import (QWidget, QLineEdit, QComboBox, QCheckBox, 
                               QFormLayout, QLabel, QPushButton, QHBoxLayout,
                               QFileDialog, QMessageBox, QApplication)
from PySide6.QtCore import Qt, Signal

class TabVCS(QWidget):
    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_loading = True
        
        self._build_ui()
        self._conectar_senales()

    def _build_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # 1. MOTOR Y CONEXIÓN BASE
        lbl_section_1 = QLabel(self.tr("Engine & Target Repository"))
        lbl_section_1.setStyleSheet("color: #F8FAFC; font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        layout.addRow("", lbl_section_1)

        self.combo_vcs = QComboBox()
        self.combo_vcs.addItems(["svn", "git-lfs"])
        self.combo_vcs.setFixedHeight(35)
        self.combo_vcs.setStyleSheet("QComboBox { background-color: #0F172A; border: 1px solid #475569; color: #F8FAFC; border-radius: 6px; padding-left: 10px; }")

        self.entry_repo_url = self._crear_input(self.tr("e.g. svn://localhost"))

        layout.addRow(self._styled_label(self.tr("Active VCS Engine:")), self.combo_vcs)
        layout.addRow(self._styled_label(self.tr("Base Server URL:")), self.entry_repo_url)

        # 2. AUTENTICACIÓN (GUARDADO EN JSON)
        lbl_section_2 = QLabel(self.tr("Network Auth (Persistent Demo Mode)"))
        lbl_section_2.setStyleSheet("color: #F8FAFC; font-weight: bold; font-size: 14px; margin-top: 15px; margin-bottom: 5px;")
        layout.addRow("", lbl_section_2)

        self.entry_vcs_user = self._crear_input(self.tr("SVN Username"))
        self.entry_vcs_pwd = self._crear_input(self.tr("SVN Password"))
        self.entry_vcs_pwd.setEchoMode(QLineEdit.Password)

        layout.addRow(self._styled_label(self.tr("SVN/Git Username:")), self.entry_vcs_user)
        layout.addRow(self._styled_label(self.tr("SVN/Git Password:")), self.entry_vcs_pwd)

        # 3. OPCIONES AVANZADAS Y TESTING
        lbl_section_4 = QLabel(self.tr("Advanced & Local Deployment"))
        lbl_section_4.setStyleSheet("color: #F8FAFC; font-weight: bold; font-size: 14px; margin-top: 15px; margin-bottom: 5px;")
        layout.addRow("", lbl_section_4)

        self.chk_sparse = QCheckBox(self.tr("Enable Jailing (Vendor Sparse Checkout)"))
        self.chk_sparse.setStyleSheet("color: #94A3B8; font-weight: bold;")
        self.chk_sparse.setCursor(Qt.PointingHandCursor)
        layout.addRow("", self.chk_sparse)

        self.btn_local_docker = QPushButton(self.tr("🐳 Deploy Localhost SVN Server (Docker)"))
        self.btn_local_docker.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; border-radius: 6px; border: none;")
        self.btn_local_docker.setFixedHeight(35)
        self.btn_local_docker.setCursor(Qt.PointingHandCursor)
        self.btn_local_docker.clicked.connect(self._desplegar_svn_local)
        layout.addRow("", self.btn_local_docker)

    def _crear_input(self, placeholder: str = "") -> QLineEdit:
        campo = QLineEdit()
        campo.setObjectName("FormInput")
        campo.setFixedHeight(35)
        campo.setPlaceholderText(placeholder)
        return campo

    def _styled_label(self, texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 12px;")
        return lbl

    def _conectar_senales(self):
        self.combo_vcs.currentIndexChanged.connect(self._on_field_modified)
        self.entry_repo_url.textChanged.connect(self._on_field_modified)
        self.entry_vcs_user.textChanged.connect(self._on_field_modified)
        self.entry_vcs_pwd.textChanged.connect(self._on_field_modified)
        self.chk_sparse.stateChanged.connect(self._on_field_modified)

    def _on_field_modified(self):
        if not self._is_loading:
            self.modified.emit()

    def _desplegar_svn_local(self):
        """Lanza un contenedor Docker con SVN limpio, actuando como Servidor Global."""
        self.btn_local_docker.setEnabled(False)
        self.btn_local_docker.setText(self.tr("Encendiendo Servidor Docker..."))
        QApplication.processEvents()

        try:
            # Limpieza y Despliegue puro del servidor (Sin repositorios aún)
            subprocess.run(["docker", "rm", "-f", "openstudio_local_svn"], capture_output=True)
            subprocess.run(["docker", "run", "-d", "--name", "openstudio_local_svn", "-p", "3690:3690", "elleflorio/svn-server"], check=True)

            QMessageBox.information(
                self, "Servidor Activo", 
                "¡El servidor SVN global está corriendo en Docker!\n\n"
                "Haz clic en 'Save Local Changes' para guardar las credenciales en el sistema."
            )
            
            # Auto-completar el formulario para el usuario
            self.entry_repo_url.setText("svn://localhost")
            self.entry_vcs_user.setText("admin")
            self.entry_vcs_pwd.setText("admin123")
            self._on_field_modified()

        except FileNotFoundError:
            QMessageBox.critical(self, "Error Fatal", "Docker no está instalado.")
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(self, "Error Docker", f"Fallo en ejecución:\n{e}")
        finally:
            self.btn_local_docker.setEnabled(True)
            self.btn_local_docker.setText(self.tr("🐳 Deploy Localhost SVN Server (Docker)"))

    def cargar_datos(self, active_adapter: str, repo_url: str, enable_sparse: bool, user: str = "", pwd: str = "", ssh_key: str = "", ssh_pwd: str = ""):
        self._is_loading = True
        idx = self.combo_vcs.findText(active_adapter)
        if idx >= 0: self.combo_vcs.setCurrentIndex(idx)
        self.entry_repo_url.setText(repo_url)
        self.chk_sparse.setChecked(enable_sparse)
        self.entry_vcs_user.setText(user)
        self.entry_vcs_pwd.setText(pwd)
        self._is_loading = False

    def get_vcs_payload(self) -> dict:
        return {
            "vcs_engine": {
                "active_adapter": self.combo_vcs.currentText(),
                "repository_url": self.entry_repo_url.text().strip(),
                "enable_vendor_sparse_checkout": self.chk_sparse.isChecked(),
                "vcs_username": self.entry_vcs_user.text().strip(),
                "vcs_password": self.entry_vcs_pwd.text().strip()
            }
        }

```

--------------------------------------------------------------------------------

### Archivo: `ui/view_artist.py`

```python

# OPENSTUDIOHUB
# Módulo: ui/view_artist.py
# Rol Arquitectónico: UI View / Artist Dashboard (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.4.3 (Strict NAS Path Validation)
# =========================================================================================

"""
Main dashboard for Studio Artists.
Inherits from BaseDashboardView to enforce DRY principles and corporate UI guidelines.
Fetches assigned tasks from Kitsu (Gazu API) and renders them in a responsive grid.
Validates VFS semantic topography with strict physical path checks to prevent I/O crashes.
"""

import gazu
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel, 
                               QScrollArea, QStackedWidget, QFrame, QPushButton,
                               QHBoxLayout, QComboBox) # <-- Añadidos QHBoxLayout y QComboBox
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QResizeEvent

from core.auth_manager import AuthManager
from core.vault_manager import VaultManager
from core.config_factory import ConfigFactory

from ui.base_dashboard import BaseDashboardView
from core.local_installer import LocalInstaller

# Intenta importar el componente nativo de Tarjeta de Tarea, si existe.
try:
    from ui.components.task_card import TaskCard
except ImportError:
    TaskCard = None


class FetchArtistTasksWorker(QThread):
    """Hilo secundario asíncrono para consultar las tareas asignadas al usuario en Kitsu."""
    data_ready = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, auth_manager=None):
        super().__init__()
        self.auth = auth_manager

    def run(self):
        try:
            user = gazu.client.get_current_user()
            all_tasks = gazu.task.all_tasks_for_person(user)
            
            status_targets = ["Todo", "Work In Progress", "Waiting For Approval", "Retake", "Ready To Start"]
            tasks = [
                t for t in all_tasks 
                if (t.get("task_status_name") in status_targets or 
                    t.get("task_status", {}).get("name") in status_targets)
            ]
            
            # --- NUEVO: ENRIQUECIMIENTO DEL TASK DATA ---
            for t in tasks:
                entity_type = t.get("entity_type_name", t.get("entity_type", "")).lower()
                
                # Si la tarea pertenece a un Asset, Kitsu no nos da la subcategoría nativamente,
                # así que debemos consultarla y empaquetarla nosotros.
                if entity_type == "asset":
                    try:
                        # 1. Consultar el Asset real usando el entity_id
                        asset_completo = gazu.asset.get_asset(t["entity_id"])
                        if asset_completo:
                            # En Kitsu, el ID del 'Asset Type' se guarda como 'entity_type_id' dentro del Asset
                            t["asset_type_id"] = asset_completo.get("entity_type_id", "")
                            
                            # 2. Opcional pero vital para tu PathResolver: Traer también el nombre del tipo
                            asset_type = gazu.asset.get_asset_type(t["asset_type_id"])
                            if asset_type:
                                t["asset_type_name"] = asset_type.get("name", "")
                    except Exception as inner_e:
                        print(f"[Worker] Advertencia: Fallo al enriquecer Asset: {inner_e}")
            # --------------------------------------------

            self.data_ready.emit(tasks)
        except Exception as e:
            self.error_occurred.emit(str(e))


class InstallProjectWorker(QThread):
    """Hilo secundario asíncrono para ejecutar el motor de instalación local sin congelar la UI."""
    progress_updated = Signal(str, str)
    finished_install = Signal(bool, str)

    def __init__(self, project_root: Path, auth_manager: AuthManager, config_factory: ConfigFactory, task_data: dict):
        super().__init__()
        self.project_root = project_root
        self.auth = auth_manager
        self.config_factory = config_factory
        self.task_data = task_data

    def run(self):
        try:
            installer = LocalInstaller(self.project_root.parent, self.config_factory)
            
            vcs_user = self.auth.user_data.get("email", "artist") if self.auth.user_data else "artist"
            vcs_pwd = self.auth.get_current_token() 
            
            total_steps = 7
            current_step = 0
            
            def interceptor_progreso(mensaje: str, color: str):
                nonlocal current_step
                trigger_words = ["Reading structural", "Synchronizing", "Extracting", "Injecting", "Deploying", "Configuring", "Generating"]
                if any(word in mensaje for word in trigger_words):
                    current_step += 1
                
                pct = int((current_step / total_steps) * 100)
                if pct > 100: pct = 100
                self.progress_updated.emit(f"⏳ {pct}% - {mensaje}", "yellow")

            success, msg = installer.instalar_entorno(
                project_root=self.project_root,
                vcs_user=vcs_user,
                vcs_pwd=vcs_pwd,
                status_callback=interceptor_progreso,
                user_role="artist",
                task_metadata=self.task_data
            )
            
            self.finished_install.emit(success, msg)
        except Exception as e:
            self.finished_install.emit(False, str(e))
            
class LaunchTaskWorker(QThread):
    """Hilo secundario para ejecutar Blender sin congelar la interfaz gráfica."""
    finished_launch = Signal(bool, str)
    
    def __init__(self, kwargs_dict):
        super().__init__()
        self.kwargs = kwargs_dict
        
    def run(self):
        try:
            from core.env_launcher import lanzar_blender
            lanzar_blender(**self.kwargs)
            self.finished_launch.emit(True, "Sesión de DCC finalizada y Lock liberado.")
        except Exception as e:
            self.finished_launch.emit(False, f"Error lanzando DCC: {str(e)}")

class ViewArtist(BaseDashboardView):
    def __init__(self, parent: QWidget, auth_manager: AuthManager, nas_dir: Path, 
                 vault_manager: VaultManager, config_factory: ConfigFactory, on_logout: Callable[[], None], **kwargs):
        
        super().__init__(parent, auth_manager, config_factory, on_logout, **kwargs)
        
        self.nas_dir = nas_dir
        self.vault = vault_manager
        
        self._task_widgets = []
        self._all_fetched_tasks = []
        self._current_cols = 0
        self._install_worker = None

        self.setObjectName("ViewArtistBase")

        self.add_sidebar_button("mis_tareas", self.tr("My Tasks"), "📋", "list.svg", lambda: self._cambiar_panel("mis_tareas"), activo=True)
        self.add_sidebar_button("watchtower", self.tr("Watchtower"), "🗼", "radar.svg", lambda: self._cambiar_panel("watchtower"))

        self._build_artist_content()
        self.cargar_tareas()

    def _build_artist_content(self):
        self.stacked_content = QStackedWidget()

        self.panel_tareas = QFrame()
        layout_tareas = QVBoxLayout(self.panel_tareas)
        layout_tareas.setContentsMargins(0, 0, 0, 0)
        layout_tareas.setSpacing(20)

        # =======================================================
        # NUEVO: Header con Título y Selector de Proyecto
        # =======================================================
        header_layout = QHBoxLayout()
        
        lbl_title = QLabel(self.tr("My Assigned Tasks"))
        lbl_title.setObjectName("PageTitle")
        
        self.combo_projects = QComboBox()
        self.combo_projects.setObjectName("StandardComboBox")
        self.combo_projects.setFixedSize(250, 35)
        # Conectamos el cambio del combo a la función de filtrado
        self.combo_projects.currentIndexChanged.connect(self._aplicar_filtro_proyecto)

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(QLabel(self.tr("Project:")))
        header_layout.addWidget(self.combo_projects)

        layout_tareas.addLayout(header_layout)
        # =======================================================

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("InvisibleScrollArea")
        
        self.grid_widget = QWidget()
        self.grid_widget.setObjectName("TransparentGridContainer")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.scroll_area.setWidget(self.grid_widget)
        layout_tareas.addWidget(self.scroll_area, stretch=1)

        self.stacked_content.addWidget(self.panel_tareas)

        placeholder_wt = QLabel(self.tr("🚧 Watchtower module under construction..."))
        placeholder_wt.setAlignment(Qt.AlignCenter)
        placeholder_wt.setObjectName("PlaceholderText")
        self.stacked_content.addWidget(placeholder_wt)

        self.content_layout.addWidget(self.stacked_content, stretch=1)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._rearrange_grid()

    def _rearrange_grid(self):
        if not self._task_widgets: return

        viewport_width = self.scroll_area.viewport().width()
        card_width = 280  
        spacing = self.grid_layout.spacing()
        
        cols = max(1, (viewport_width + spacing) // (card_width + spacing))

        if getattr(self, '_current_cols', 0) == cols: return

        self._current_cols = cols
        row, col = 0, 0

        for widget in self._task_widgets:
            self.grid_layout.removeWidget(widget)
            self.grid_layout.addWidget(widget, row, col)
            
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _cambiar_panel(self, panel_id: str):
        self.set_active_sidebar_button(panel_id) 
        indices = {"mis_tareas": 0, "watchtower": 1}
        self.stacked_content.setCurrentIndex(indices.get(panel_id, 0))

    def cargar_tareas(self):
        self.actualizar_status(self.tr("Fetching your assigned tasks from Kitsu..."), "yellow")
        
        self.combo_projects.clear()
        self._all_fetched_tasks = []
        
        for widget in self._task_widgets:
            widget.hide()
            widget.deleteLater()
        self._task_widgets.clear()
        
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        self.worker = FetchArtistTasksWorker(self.auth)
        self.worker.data_ready.connect(self._procesar_nuevas_tareas)
        self.worker.error_occurred.connect(lambda e: self.actualizar_status(f"Network error: {e}", "red"))
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _procesar_nuevas_tareas(self, tasks: list):
        """Recibe las tareas de la API, extrae los proyectos y prepara la UI."""
        if not tasks:
            self.actualizar_status(self.tr("You have no pending tasks. Enjoy your coffee! ☕"), "white")
            return
            
        self.actualizar_status(self.tr("🟢 Synchronized: {0} active tasks found.").format(len(tasks)), "green")
        
        # 1. Guardar en memoria local
        self._all_fetched_tasks = tasks
        
        # 2. Extraer dinámicamente los proyectos que existen dentro de esas tareas
        self.combo_projects.blockSignals(True)
        self.combo_projects.clear()
        self.combo_projects.addItem(self.tr("All Projects"), "ALL")
        
        proyectos_unicos = {}
        for t in tasks:
            p_name = t.get('project_name') or (t.get('project') or {}).get('name', 'Unknown')
            p_id = t.get('project_id')
            if p_name and p_id and p_id not in proyectos_unicos:
                proyectos_unicos[p_id] = p_name
                
        # Insertar ordenados alfabéticamente
        for p_id, p_name in sorted(proyectos_unicos.items(), key=lambda item: item[1]):
            self.combo_projects.addItem(p_name, p_id)
            
        self.combo_projects.blockSignals(False)
        
        # 3. Disparar el primer renderizado (por defecto mostrará "All Projects")
        self._aplicar_filtro_proyecto()

    def _aplicar_filtro_proyecto(self, index=0):
        """Filtra la lista de tareas en caché y dibuja el Grid."""
        
        # 1. Limpiar Grid Actual
        for widget in self._task_widgets:
            widget.hide()
            widget.deleteLater()
        self._task_widgets.clear()
        
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # 2. Obtener el ID del proyecto a filtrar
        selected_project_id = self.combo_projects.currentData()
        
        if selected_project_id == "ALL":
            filtered_tasks = self._all_fetched_tasks
        else:
            filtered_tasks = [t for t in self._all_fetched_tasks if t.get('project_id') == selected_project_id]

        vfs_pipeline = self.config_factory.get_vfs_pipeline_name()
        nas_root = self.config_factory.get_workspace_root()
        
        # 3. Renderizar Tarjetas
        for task_data in filtered_tasks:
            if TaskCard:
                # 1. Extracción directa respaldada por nuestro dump forense
                p_name = task_data.get('project_name') or (task_data.get('project') or {}).get('name', 'Unknown')
                
                # 2. Normalización de carpeta según la convención del ProjectBuilder
                folder_name = p_name.strip().lower().replace(" ", "-")
                temp_root = nas_root / folder_name

                # === PRINTS DE DEPURACIÓN ===
                print(f"\n[DEBUG] --- TAREA ENCONTRADA ---")
                print(f"[DEBUG] Nombre extraído (p_name): '{p_name}'")
                print(f"[DEBUG] Carpeta calculada: '{folder_name}'")
                print(f"[DEBUG] Buscando ruta física en: {temp_root}")
                print(f"[DEBUG] ¿Existe la carpeta?: {temp_root.exists()}")
                print(f"----------------------------\n")
                # ============================

                # Verificación de existencia física en el NAS
                if temp_root.exists():
                    project_root = temp_root
                else:
                    project_root = None

                is_installed = False
                can_work = True
                blocked_reason = ""
                
                if project_root:
                    try:
                        is_installed = LocalInstaller(project_root.parent, self.config_factory).verificar_instalacion(project_root)
                    except Exception:
                        is_installed = False

                    if not is_installed:
                        init_json_path = project_root / vfs_pipeline / "project_init.json"
                        if not init_json_path.exists():
                            can_work = False
                            blocked_reason = self.tr("Missing NAS Setup")
                else:
                    can_work = False
                    blocked_reason = self.tr("Folder Missing on NAS")

                # 2. INYECCIÓN DEL PATH RESOLVER EN EL CALLBACK DE LAUNCH
                # 2. DELEGACIÓN AL ORQUESTADOR DCC (Env Launcher)
                def launch_cb(p_root: Path, conf_path: Path, t_data: dict):
                    #from core.env_launcher import lanzar_blender
                    
                    self.actualizar_status(self.tr("🚀 Delegando al Orquestador DCC..."), "yellow")
                    
                    if not conf_path.exists():
                        self.actualizar_status(self.tr("Config file missing. Reinstall workspace."), "red")
                        return
                        
                    # Extraer credenciales base (El env_launcher aplicará el bypass de admin en localhost)
                    #import os
                    vcs_user = "admin"
                    vcs_pwd = "admin123"

                    kitsu_user = self.vault._transient_email
                    kitsu_pwd = self.vault._transient_password

                    if not kitsu_pwd:
                        # Fallback (si la bóveda está vacía, pedimos que re-inicie sesión)
                        self.actualizar_status("Kitsu Password lost in RAM. Please log out and log in again.", "red")
                        return

                    kitsu_host = self.config_factory.get_kitsu_api_url()
                    
                    # Delegar todo el trabajo pesado, sandboxing y variables de entorno al motor central
                    # 1. BLOQUEAR EL CIERRE DEL HUB
                    main_window = self.window()
                    if hasattr(main_window, 'registrar_instancia'):
                        main_window.registrar_instancia(True) 
                        
                    # 2. PREPARAR ARGUMENTOS PARA EL WORKER
                    kwargs = {
                        "project_root": p_root,
                        "config_path": conf_path,
                        "svn_user": vcs_user,
                        "svn_pwd": vcs_pwd,
                        "kitsu_user": kitsu_user,
                        "kitsu_pwd": kitsu_pwd,
                        "kitsu_host": kitsu_host,
                        "user_role": "artist",
                        "task_data": t_data,
                        "target_file": None,
                        "status_callback": self.actualizar_status,
                        "config_factory": self.config_factory
                    }
                    
                    # 3. LANZAR EN HILO SECUNDARIO
                    self.launch_worker = LaunchTaskWorker(kwargs)
                    
                    def on_launch_finished(success, msg):
                        # 4. LIBERAR EL CIERRE DEL HUB
                        if hasattr(main_window, 'registrar_instancia'):
                            main_window.registrar_instancia(False)
                        self.actualizar_status(msg, "green" if success else "red")
                        
                    self.launch_worker.finished_launch.connect(on_launch_finished)
                    self.launch_worker.start()

                def install_cb(p_root: Path, t_data: dict):
                    self.iniciar_instalacion_fisica(p_root, t_data)

                # =========================================================
                # INSERTA ESTO: Creación de la tarjeta y guardado en la lista
                # =========================================================
                tarjeta = TaskCard(
                    parent=self.grid_widget,
                    task_data=task_data,
                    project_root=project_root,
                    is_installed=is_installed,
                    auth_manager=self.auth,
                    config_factory=self.config_factory,
                    on_launch_callback=launch_cb,
                    on_install_callback=install_cb,
                    can_work=can_work,
                    blocked_reason=blocked_reason
                )
            else:
                # Fallback por si la importación de TaskCard falla
                tarjeta = QFrame()
                tarjeta.setFixedSize(280, 220)

            # ¡Añadimos la tarjeta a la cuadrícula!
            self._task_widgets.append(tarjeta)
            # =========================================================
            
        self._current_cols = 0 
        self._rearrange_grid()

    def iniciar_instalacion_fisica(self, project_root: Path, task_data: dict):
        if not project_root:
            self.actualizar_status(self.tr("Cannot install: Project folder is missing on NAS."), "red")
            return
            
        if self._install_worker and self._install_worker.isRunning():
            self.actualizar_status(self.tr("Please wait, an installation is already running..."), "red")
            return

        self._install_worker = InstallProjectWorker(
            project_root=project_root,
            auth_manager=self.auth,
            config_factory=self.config_factory,
            task_data=task_data
        )

        self._install_worker.progress_updated.connect(self.actualizar_status)
        self._install_worker.finished_install.connect(self._on_install_finished)
        self._install_worker.start()

    def _on_install_finished(self, success: bool, message: str):
        if success:
            self.actualizar_status(self.tr("🟢 100% - {0}").format(message), "green")
            self.cargar_tareas()
        else:
            self.actualizar_status(self.tr("🔴 Install Error: {0}").format(message), "red")

```

--------------------------------------------------------------------------------

### Archivo: `ui/view_login.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/view_login.py
# Rol Arquitectónico: UI View / Authentication (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.7.1
# =========================================================================================

"""
Vista principal para el inicio de sesión del usuario.
Implementa la lógica del Día 0 (Importación de Studio Seed) y Día 1+ (Read-Only).
Oculta la destrucción de caché detrás de un QDialog modal accesible desde la Top Bar.
Utiliza internacionalización nativa de Qt (i18n) a través de self.tr().
"""

from _version import __version__

from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                               QLabel, QLineEdit, QPushButton, QFileDialog, 
                               QMessageBox, QDialog)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QPainter

class HeroImageWidget(QWidget):
    """
    Widget personalizado que dibuja una imagen de fondo comportándose como
    'object-fit: cover' en CSS. Mantiene la relación de aspecto y recorta el excedente.
    """
    def __init__(self, image_path: Path):
        super().__init__()
        self.pixmap = QPixmap(str(image_path))
        self.setObjectName("HeroPanel")

    def paintEvent(self, event):
        if self.pixmap.isNull():
            return super().paintEvent(event)
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        rect = self.rect()
        
        scaled_pixmap = self.pixmap.scaled(
            rect.size(), 
            Qt.KeepAspectRatioByExpanding, 
            Qt.SmoothTransformation
        )
        
        x_offset = (scaled_pixmap.width() - rect.width()) // 2
        y_offset = (scaled_pixmap.height() - rect.height()) // 2
        
        painter.drawPixmap(0, 0, scaled_pixmap, x_offset, y_offset, rect.width(), rect.height())


class LoginSettingsDialog(QDialog):
    """Modal de configuración avanzada para el manejo del Studio Seed local."""
    def __init__(self, parent, config_factory, on_clear_callback):
        super().__init__(parent)
        self.config_factory = config_factory
        self.on_clear_callback = on_clear_callback
        
        self.setWindowTitle(self.tr("Login Settings"))
        self.setFixedSize(320, 160)
        self.setStyleSheet("""
            QDialog { background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; }
            QLabel { color: #F8FAFC; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_title = QLabel(self.tr("Advanced Configuration"))
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(self.tr("Delete the active Studio Seed to load a new one. This action reverts the application to Day 0."))
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)
        
        layout.addStretch()
        
        btn_clear = QPushButton(self.tr("Clear Local Configuration"))
        btn_clear.setStyleSheet("background-color: #EF4444; color: white; font-weight: bold; border-radius: 4px; padding: 8px; border: none;")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self._confirm_clear)
        layout.addWidget(btn_clear)

    def _confirm_clear(self):
        reply = QMessageBox.question(
            self, 
            self.tr("Clear Configuration"), 
            self.tr("Are you sure you want to delete the local configuration?\nAll connection paths will be lost."),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            exito = self.config_factory.purgar_configuracion_local()
            self.on_clear_callback(exito)
            self.accept()


class LoginWorker(QThread):
    success = Signal()
    error = Signal(str)

    def __init__(self, auth_manager, email, password, host):
        super().__init__()
        self.auth_manager = auth_manager
        self.email = email
        self.password = password
        self.host = host

    def run(self):
        exito, mensaje = self.auth_manager.login_with_credentials(self.email, self.password, self.host)
        if exito:
            self.success.emit()
        else:
            self.error.emit(mensaje)


class ViewLogin(QWidget):
    def __init__(self, parent, auth_manager, vault_manager, config_factory, on_login_success):
        super().__init__(parent)
        
        self.auth_manager = auth_manager
        self.vault_manager = vault_manager
        self.config_factory = config_factory
        self.on_login_success = on_login_success
        
        self.setObjectName("ViewLoginBase")

        self._build_ui()
        self._refresh_config_state()

    def _set_icon_or_fallback(self, label: QLabel, icon_name: str, color_hex: str, size: int, fallback_text: str):
        """Helper para teñir SVG al vuelo en memoria RAM. Evita emojis asincronizados."""
        icon_path = Path(f"assets/icons/{icon_name}")
        if not icon_path.exists():
            label.setText(fallback_text)
            label.setStyleSheet(f"color: {color_hex};")
            return
            
        try:
            with open(icon_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            svg_content = svg_content.replace('currentColor', color_hex)
            svg_content = svg_content.replace('#000000', color_hex)
            svg_content = svg_content.replace('#000"', f'{color_hex}"')
            svg_content = svg_content.replace("#000'", f"{color_hex}'")
            
            pixmap = QPixmap()
            pixmap.loadFromData(svg_content.encode('utf-8'), "SVG")
            if not pixmap.isNull():
                label.setPixmap(pixmap.scaledToHeight(size, Qt.SmoothTransformation))
                label.setText("") 
            else:
                label.setText(fallback_text)
        except Exception:
            label.setText(fallback_text)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---------------------------------------------------------
        # BARRA SUPERIOR (BRANDING & TOP BAR)
        # ---------------------------------------------------------
        self.top_bar = QFrame(self)
        self.top_bar.setObjectName("TopBar")
        self.top_bar.setFixedHeight(65)
        
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(30, 10, 30, 10)
        top_layout.setSpacing(15)
        
        self.logo_icon = QLabel()
        logo_path = Path("assets/logo_topbar.png")
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            self.logo_icon.setPixmap(pixmap.scaledToHeight(40, Qt.SmoothTransformation))
        top_layout.addWidget(self.logo_icon)
        
        self.top_separator = QFrame()
        self.top_separator.setObjectName("TopSeparator")
        self.top_separator.setFixedSize(2, 24)
        top_layout.addWidget(self.top_separator)
        
        self.lbl_title = QLabel("OpenStudioHub")
        self.lbl_title.setObjectName("H1Title")
        top_layout.addWidget(self.lbl_title)

        top_layout.addStretch()

        # self.avatar_icon = QLabel()
        # self._set_icon_or_fallback(self.avatar_icon, "user.svg", "#94A3B8", 20, "👤")
        # self.avatar_icon.setObjectName("AvatarIcon")
        # self.avatar_icon.setAlignment(Qt.AlignCenter)
        # self.avatar_icon.setFixedSize(35, 35)
        # top_layout.addWidget(self.avatar_icon)

        # Reemplazo de la campana por Configuración (Engranaje)
        self.settings_icon = QLabel()
        self._set_icon_or_fallback(self.settings_icon, "settings.svg", "#64748B", 22, "⚙️")
        self.settings_icon.setContentsMargins(10, 0, 15, 0)
        self.settings_icon.setCursor(Qt.PointingHandCursor)
        self.settings_icon.mousePressEvent = self._abrir_modal_settings
        top_layout.addWidget(self.settings_icon)

        # self.conn_icon = QLabel()
        # self._set_icon_or_fallback(self.conn_icon, "server.svg", "#3B82F6", 14, "🔵")
        # top_layout.addWidget(self.conn_icon)

        # self.lbl_connected = QLabel(self.tr("Connected"))
        # self.lbl_connected.setStyleSheet("color: #3B82F6; font-size: 13px; font-weight: bold;")
        # top_layout.addWidget(self.lbl_connected)

        main_layout.addWidget(self.top_bar)

        # ---------------------------------------------------------
        # ÁREA CENTRAL: SPLIT SCREEN
        # ---------------------------------------------------------
        self.split_area = QFrame(self)
        split_layout = QHBoxLayout(self.split_area)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(0)
        
        # --- PANEL IZQUIERDO (FORMULARIO DE LOGIN) ---
        self.left_panel = QFrame()
        self.left_panel.setObjectName("LoginPanel")
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setAlignment(Qt.AlignCenter)
        left_layout.setContentsMargins(40, 20, 40, 20)
        
        self.form_container = QFrame(self.left_panel)
        self.form_container.setMaximumWidth(400)
        form_layout = QVBoxLayout(self.form_container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(8)
        
        self.lbl_card_title = QLabel(self.tr("Welcome to OpenStudioHub"))
        self.lbl_card_title.setObjectName("CardTitle")
        self.lbl_card_title.setStyleSheet("margin-bottom: 30px;")
        form_layout.addWidget(self.lbl_card_title)

        # Campos de entrada limpios (Sin el botón destructivo)
        lbl_host = QLabel(self.tr("Server URL"))
        lbl_host.setObjectName("InputLabel")
        form_layout.addWidget(lbl_host)
        
        self.entry_host = QLineEdit()
        self.entry_host.setPlaceholderText(self.tr("e.g., https://kitsu.studio.com"))
        self.entry_host.setObjectName("FormInput")
        self.entry_host.setFixedHeight(45)
        form_layout.addWidget(self.entry_host)
        
        form_layout.addSpacing(10)

        lbl_email = QLabel(self.tr("Email Address"))
        lbl_email.setObjectName("InputLabel")
        form_layout.addWidget(lbl_email)
        
        self.entry_email = QLineEdit()
        self.entry_email.setPlaceholderText(self.tr("Email Address"))
        self.entry_email.setObjectName("FormInput")
        self.entry_email.setFixedHeight(45)
        form_layout.addWidget(self.entry_email)

        form_layout.addSpacing(10)

        lbl_pwd = QLabel(self.tr("Password"))
        lbl_pwd.setObjectName("InputLabel")
        form_layout.addWidget(lbl_pwd)
        
        self.entry_password = QLineEdit()
        self.entry_password.setPlaceholderText(self.tr("Password"))
        self.entry_password.setObjectName("FormInput")
        self.entry_password.setEchoMode(QLineEdit.Password)
        self.entry_password.setFixedHeight(45)
        form_layout.addWidget(self.entry_password)

        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("ErrorLabel")
        self.lbl_error.hide()
        form_layout.addWidget(self.lbl_error)

        form_layout.addSpacing(20)

        # Botones de Acción
        self.btn_login = QPushButton(self.tr("Log In"))
        self.btn_login.setObjectName("PrimaryButton")
        self.btn_login.setFixedHeight(50)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self.ejecutar_login)
        form_layout.addWidget(self.btn_login)

        self.btn_import_seed = QPushButton(self.tr("Import Studio Seed (.seed)"))
        self.btn_import_seed.setObjectName("SecondaryButton")
        self.btn_import_seed.setFixedHeight(40)
        self.btn_import_seed.setCursor(Qt.PointingHandCursor)
        self.btn_import_seed.clicked.connect(self._importar_semilla)
        form_layout.addWidget(self.btn_import_seed)

        # Links secundarios
        links_layout = QHBoxLayout()
        links_layout.setContentsMargins(0, 15, 0, 0)
        
        self.btn_forgot = QPushButton(self.tr("Forgot Password?"))
        self.btn_forgot.setObjectName("LinkButton")
        self.btn_forgot.setCursor(Qt.PointingHandCursor)
        self.btn_forgot.setFlat(True)
        links_layout.addWidget(self.btn_forgot, alignment=Qt.AlignLeft)
        
        lbl_version = QLabel(f"Version {__version__}")
        lbl_version.setStyleSheet("color: #64748B; font-size: 11px;")
        links_layout.addWidget(lbl_version, alignment=Qt.AlignRight)
        
        form_layout.addLayout(links_layout)
        left_layout.addWidget(self.form_container)
        
        split_layout.addWidget(self.left_panel, stretch=1)

        # --- PANEL DERECHO ---
        hero_path = Path("assets/login_hero.png")
        if not hero_path.exists():
            hero_path = Path("assets/login_hero.jpg")
            
        self.right_panel = HeroImageWidget(hero_path)
        split_layout.addWidget(self.right_panel, stretch=1)

        main_layout.addWidget(self.split_area, stretch=1)

        # ---------------------------------------------------------
        # BARRA DE ESTADO
        # ---------------------------------------------------------
        self.status_bar = QFrame(self)
        self.status_bar.setObjectName("StatusBar")
        self.status_bar.setFixedHeight(25)
        
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(15, 0, 15, 0)

        self.status_icon = QLabel()
        self._set_icon_or_fallback(self.status_icon, "server.svg", "#10B981", 12, "🟢")
        status_layout.addWidget(self.status_icon)

        self.lbl_status = QLabel(self.tr("SYSTEM: ONLINE   |   WAITING FOR CREDENTIALS"))
        self.lbl_status.setObjectName("StatusText")
        status_layout.addWidget(self.lbl_status)
        
        status_layout.addStretch()

        main_layout.addWidget(self.status_bar)

    # ---------------------------------------------------------
    # STUDIO SEED LOGIC (DÍA 0 vs DÍA 1+)
    # ---------------------------------------------------------
    def _refresh_config_state(self):
        kitsu_url = self.config_factory.get_kitsu_api_url()
        has_config = bool(kitsu_url)

        if has_config:
            self.entry_host.setText(kitsu_url)
            self.entry_host.setReadOnly(True)
            self.entry_host.setStyleSheet("background-color: #0F172A; color: #64748B; border: 1px solid #1E293B;")
            self.btn_import_seed.hide()
            self.settings_icon.show()
        else:
            self.entry_host.clear()
            self.entry_host.setReadOnly(False)
            self.entry_host.setStyleSheet("")
            self.btn_import_seed.show()
            self.settings_icon.hide()

    def _abrir_modal_settings(self, event):
        dialog = LoginSettingsDialog(self, self.config_factory, self._on_config_cleared)
        dialog.exec()

    def _on_config_cleared(self, exito: bool):
        self._refresh_config_state()
        if exito:
            self._on_login_error(self.tr("✓ Local configuration cleared."))
            self.lbl_error.setStyleSheet("color: #10B981;")
        else:
            self._on_login_error(self.tr("✗ Could not delete configuration file."))
            self.lbl_error.setStyleSheet("color: #EF4444;")

    def _importar_semilla(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select Studio Seed File"), "", self.tr("Seed Files (*.seed);;All Files (*)")
        )
        if file_path:
            exito = self.config_factory.importar_semilla(Path(file_path))
            if exito:
                self._refresh_config_state()
                self._on_login_error(self.tr("✓ Configuration imported successfully. You can now log in."))
                self.lbl_error.setStyleSheet("color: #10B981;")
            else:
                self._on_login_error(self.tr("✗ Failed to load the Seed. The file might be corrupted."))
                self.lbl_error.setStyleSheet("color: #EF4444;")

    # ---------------------------------------------------------
    # AUTHENTICATION
    # ---------------------------------------------------------
    def ejecutar_login(self):
        email = self.entry_email.text().strip()
        password = self.entry_password.text().strip()
        host = self.entry_host.text().strip()

        self.lbl_error.hide()
        self.lbl_error.setStyleSheet("color: #EF4444;")
        
        if not email or not password or not host:
            self.lbl_error.setText(self.tr("Please fill all the required fields."))
            self.lbl_error.show()
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText(self.tr("Connecting to Server..."))
        
        self._set_icon_or_fallback(self.status_icon, "server.svg", "#F59E0B", 12, "🟠")
        self.lbl_status.setText(self.tr("SYSTEM: AUTHENTICATING... PLEASE WAIT."))

        self._temp_email = email
        self._temp_password = password

        self.worker = LoginWorker(self.auth_manager, email, password, host)
        self.worker.success.connect(self._on_login_success)
        self.worker.error.connect(self._on_login_error)
        self.worker.finished.connect(self.worker.deleteLater) 
        self.worker.start()

    def _on_login_success(self):
        self.vault_manager.save_kitsu_credentials(self._temp_email, self._temp_password)
        self.on_login_success()

    def _on_login_error(self, mensaje):
        self.lbl_error.setText(mensaje)
        self.lbl_error.show()
        
        self.btn_login.setEnabled(True)
        self.btn_login.setText(self.tr("Log In"))
        
        self._set_icon_or_fallback(self.status_icon, "server.svg", "#EF4444", 12, "🔴")
        self.lbl_status.setText(self.tr("SYSTEM: AUTHENTICATION FAILED."))

```

--------------------------------------------------------------------------------

### Archivo: `ui/view_pm.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/view_pm.py
# Rol Arquitectónico: UI Component / Production Manager Dashboard
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 2.1.0 (Widget Extraction / Routing Only)
# =========================================================================================

from PySide6.QtWidgets import QStackedWidget, QLabel
from PySide6.QtCore import Qt

from core import vault_manager
from ui.base_dashboard import BaseDashboardView
from ui.widget_blend_builder import WidgetBlendBuilder

# Importaremos el widget unificado (actualmente el del TD, que unificaremos en el siguiente paso)
from ui.widget_project_list import ProjectListWidget

class ViewPM(BaseDashboardView):
    def __init__(self, parent, auth_manager, config_factory, on_logout, vault_manager=None, **kwargs):
        self.vault_manager = vault_manager
        super().__init__(parent, auth_manager, config_factory, on_logout, **kwargs)
        
        self.setObjectName("ViewPMBase")

        # 1. Configurar Navegación Lateral
        self.add_sidebar_button("btn_projects", self.tr("Projects"), "📁", "folder.svg", lambda: self._cambiar_panel("btn_projects"), activo=True)
        # Espacio preparado para futuros paneles del PM
        self.add_sidebar_button("btn_batch", self.tr("Batch Creation"), "📦", "box.svg", lambda: self._cambiar_panel("btn_batch"))

        # 2. Construir el Contenido Central
        self._build_pm_content()

    def _build_pm_content(self):
        """Prepara el StackedWidget e inyecta los widgets de trabajo modulares."""
        self.stacked_content = QStackedWidget()

        # Index 0: Lista de Proyectos (Unificada)
        # Le pasamos un callback para que la tarjeta sepa qué hacer al hacer clic en "Open Wizard"
        self.project_list = ProjectListWidget(
            parent=self.stacked_content,
            nas_dir=self.config_factory.get_workspace_root(),
            auth_manager=self.auth,
            vault_manager=None, # El PM delega esto al config_factory en la nueva arquitectura
            config_factory=self.config_factory,
            status_callback=self.actualizar_status,
            on_open_wizard_callback=self._abrir_wizard_para_proyecto # <--- NUEVO HOOK
        )
        self.stacked_content.addWidget(self.project_list)

        # Index 0: Batch Entity Genesis Tool
        self.widget_builder = WidgetBlendBuilder(
            parent=self.stacked_content,
            auth_manager=self.auth,
            config_factory=self.config_factory,
            status_callback=self.actualizar_status,
            vault_manager=self.vault_manager
        )
        self.stacked_content.addWidget(self.widget_builder)

        # Inyectar el stack completo en el contenedor de la clase padre
        self.content_layout.addWidget(self.stacked_content, stretch=1)

    def _cambiar_panel(self, panel_id: str):
        """Visual Router: Actualiza el sidebar y cambia la vista del stack."""
        self.set_active_sidebar_button(panel_id)
        indices = {"btn_projects": 0, "btn_batch": 1}
        self.stacked_content.setCurrentIndex(indices.get(panel_id, 0))
        
        # Auto-recargar proyectos al entrar a la vista
        if panel_id == "btn_projects":
            self.project_list.cargar_proyectos()

    def _abrir_wizard_para_proyecto(self, project_name: str):
        """Hook que recibe la señal de la tarjeta y transiciona al Wizard."""
        self._cambiar_panel("btn_batch")
        # Forzar al combo box del Wizard a seleccionar el proyecto en el que hicimos clic
        index = self.widget_builder.combo_projects.findText(project_name)
        if index >= 0:
            self.widget_builder.combo_projects.setCurrentIndex(index)

```

--------------------------------------------------------------------------------

### Archivo: `ui/view_td.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/view_td.py
# Rol Arquitectónico: UI View / Command Center Dashboard (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.0.0 (MasterLayout Inheritance)
# =========================================================================================

"""
Advanced control panel for the Technical Director (TD) and Supervisors.
Inherits from BaseDashboardView to enforce DRY principles and corporate UI guidelines.
Uses QStackedWidget to dynamically switch between Infrastructure, Settings, and Projects.
"""

from PySide6.QtWidgets import QStackedWidget, QLabel
from PySide6.QtCore import Qt
from pathlib import Path
from typing import Callable

from core.auth_manager import AuthManager
from core.vault_manager import VaultManager
from core.config_factory import ConfigFactory

from ui.base_dashboard import BaseDashboardView
from ui.widget_project_list import ProjectListWidget
from ui.widget_infrastructure import InfrastructureWidget
from ui.widget_settings import SettingsWidget


class ViewTD(BaseDashboardView):
    def __init__(self, parent, auth_manager: AuthManager, nas_dir: Path, 
                 vault_manager: VaultManager, config_factory: ConfigFactory, on_logout: Callable[[], None], **kwargs):
        
        # Inicializa el cascarón maestro (TopBar, Sidebar, StatusBar)
        super().__init__(parent, auth_manager, config_factory, on_logout, **kwargs)
        
        self.nas_dir = nas_dir
        self.vault = vault_manager

        self.setObjectName("ViewTDBase")

        # 1. Configurar Navegación Lateral (Inyectada al Master Layout)
        self.add_sidebar_button("proyectos", self.tr("Projects"), "🗂️", "folder.svg", lambda: self._cambiar_panel("proyectos"), activo=True)
        self.add_sidebar_button("watchtower", self.tr("Watchtower"), "🗼", "radar.svg", lambda: self._cambiar_panel("watchtower"))
        self.add_sidebar_button("infra", self.tr("Infrastructure"), "⚙️", "server.svg", lambda: self._cambiar_panel("infra"))
        self.add_sidebar_button("settings", self.tr("Settings"), "🔧", "settings.svg", lambda: self._cambiar_panel("settings"))

        # 2. Construir el Contenido Central
        self._build_td_content()
        
        # 3. Inicializar Datos
        self.vista_proyectos.cargar_proyectos()

    def _build_td_content(self):
        """Construye los paneles de configuración y los inyecta en el layout central."""
        
        self.stacked_content = QStackedWidget()

        # Index 0: Project Management List
        self.vista_proyectos = ProjectListWidget(
            parent=self.stacked_content,
            nas_dir=self.nas_dir,
            auth_manager=self.auth,
            vault_manager=self.vault,
            config_factory=self.config_factory,
            status_callback=self.actualizar_status  # Método heredado
        )
        self.stacked_content.addWidget(self.vista_proyectos)

        # Index 1: Watchtower Hub Window (Placeholder)
        placeholder_wt = QLabel(self.tr("🚧 Watchtower module under construction..."))
        placeholder_wt.setAlignment(Qt.AlignCenter)
        placeholder_wt.setObjectName("PlaceholderText")
        self.stacked_content.addWidget(placeholder_wt)
        
        # Index 2: Infrastructure Configuration Panel
        self.vista_infra = InfrastructureWidget(
            parent=self.stacked_content,
            config_factory=self.config_factory,
            status_callback=self.actualizar_status
        )
        self.stacked_content.addWidget(self.vista_infra)

        # Index 3: Global System Settings 
        self.vista_configuraciones = SettingsWidget(
            parent=self.stacked_content,
            config_factory=self.config_factory,
            auth_manager=self.auth,
            status_callback=self.actualizar_status
        )
        self.stacked_content.addWidget(self.vista_configuraciones)

        # Inyectar el stack completo en el contenedor de la clase padre
        self.content_layout.addWidget(self.stacked_content, stretch=1)

    def _cambiar_panel(self, panel_id: str):
        """Visual Router: Actualiza el sidebar y cambia la vista del stack."""
        self.set_active_sidebar_button(panel_id) # Método heredado
        
        indices = {"proyectos": 0, "watchtower": 1, "infra": 2, "settings": 3}
        self.stacked_content.setCurrentIndex(indices.get(panel_id, 0))

```

--------------------------------------------------------------------------------

### Archivo: `ui/web_context_view.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/web_context_view.py
# Rol Arquitectónico: UI View / Immersive Web Context (Kitsu / Watchtower)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.1.0
# =========================================================================================

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices

# Módulos específicos del navegador web embebido
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript, QWebEngineSettings

class CustomWebPage(QWebEnginePage):
    """
    Página web personalizada para interceptar la navegación.
    Evita que el usuario salga del contexto de Kitsu/Watchtower haciendo
    clic en enlaces externos (como Google Drive, YouTube, etc).
    """
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.allowed_hosts = []

    def set_allowed_hosts(self, hosts: list):
        self.allowed_hosts = hosts

    def acceptNavigationRequest(self, url: QUrl, _type: QWebEnginePage.NavigationType, isMainFrame: bool) -> bool:
        # Si el usuario hace clic explícitamente en un enlace
        if _type == QWebEnginePage.NavigationTypeLinkClicked:
            host = url.host()
            # Validamos si el host del link está en nuestra lista blanca
            if not any(allowed in host for allowed in self.allowed_hosts):
                print(f"[WebContext] Redirigiendo enlace externo al SO: {url.toString()}")
                QDesktopServices.openUrl(url)
                return False # Bloqueamos que se abra dentro de nuestro Hub
                
        return super().acceptNavigationRequest(url, _type, isMainFrame)


class WebContextView(QFrame):
    # Señal que avisará al Orquestador (OpenStudioHub) que debe cambiar de capa
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WebContextView")
        self.setStyleSheet("background-color: #0F172A;") # Fondo base del Hub

        # --- Control de estado para SSO ---
        #self.sso_token = None
        #self._token_injected = False
        
        
        self._build_ui()

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ---------------------------------------------------------
        # 1. TOP BAR (Controles de Navegación)
        # ---------------------------------------------------------
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(50)
        self.top_bar.setStyleSheet("background-color: #1E293B; border-bottom: 1px solid #141820;")
        
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(15, 0, 15, 0)
        top_layout.setSpacing(15)

        # Botón Volver
        self.btn_back = QPushButton("⬅  Return to Hub")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6; color: white; border-radius: 6px;
                padding: 6px 15px; font-weight: bold; font-size: 13px; border: none;
            }
            QPushButton:hover { background-color: #2563EB; }
        """)
        self.btn_back.clicked.connect(self._on_back_clicked)
        top_layout.addWidget(self.btn_back)

        # Indicador de estado/Título
        self.lbl_title = QLabel("Initializing...")
        self.lbl_title.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 13px; border: none;")
        top_layout.addWidget(self.lbl_title)
        
        top_layout.addStretch()
        self.main_layout.addWidget(self.top_bar)

        # ---------------------------------------------------------
        # 2. WEB ENGINE (El navegador incrustado)
        # ---------------------------------------------------------
        self.web_view = QWebEngineView()
        
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

        # Inyectamos nuestra página personalizada con lógica de enlaces
        # Usamos el perfil por defecto (o podríamos crear uno aislado si queremos modo incógnito)
        self.custom_page = CustomWebPage(self.web_view.page().profile(), self.web_view)
        self.web_view.setPage(self.custom_page)
        
        self.main_layout.addWidget(self.web_view, stretch=1)

        # Conectar señales de estado del navegador
        self.web_view.loadStarted.connect(lambda: self.lbl_title.setText("Loading..."))
        self.web_view.loadFinished.connect(self._on_load_finished)

    def load_context(self, url_str: str, context_name: str, allowed_hosts: list, sso_token: str = None):
        """
        Inicia la carga de la vista web.
        Ejemplo: load_context("http://localhost:8080", "Kitsu", ["localhost", "kitsu.midominio.com"])
        """
        self.lbl_title.setText(f"Connecting to {context_name}...")
        self.custom_page.set_allowed_hosts(allowed_hosts)

        scripts = self.web_view.page().scripts()
        for script in scripts.toList():
            if script.name() == "Kitsu_SSO_Injector":
                scripts.remove(script)

        if sso_token:
            sso_script = QWebEngineScript()
            sso_script.setName("Kitsu_SSO_Injetor")

            sso_script.setSourceCode(f"""
                (function() {{
                    
                    if (window.location.protocol === 'about:' || window.location.protocol === 'data:') {{
                        return;
                    }}

                    try {{
                        window.localStorage.setItem('access_token', '{sso_token}');
                        window.localStorage.setItem('refresh_token', '{sso_token}');
                        window.localStorage.setItem('token', '{sso_token}');
                    }} catch (e) {{
                        console.error('Error inyectando SSO token nativo:', e);
                    }}
                }})();
            """)

            sso_script.setInjectionPoint(QWebEngineScript.DocumentCreation)
            sso_script.setWorldId(QWebEngineScript.MainWorld)
            sso_script.setRunsOnSubFrames(False)

            scripts.insert(sso_script)

        self.web_view.setUrl(QUrl(url_str))

    def inject_javascript(self, js_code: str):
        """Método de utilidad para inyectar tokens o cookies (Problema de Doble Login)."""
        self.web_view.page().runJavaScript(js_code)

    def _on_load_finished(self, success: bool):
        if success:
            # Tomamos el título real de la página web (Ej: "Kitsu - My Project")
            self.lbl_title.setText(self.web_view.title())

        else:
            self.lbl_title.setText("Connection failed. Please check network.")

    def _on_back_clicked(self):
        """Se ejecuta al intentar volver. Limpia procesos y notifica al Orquestador."""
        self.lbl_title.setText("Closing...")
        self.web_view.stop()
        
        # Navegamos a about:blank para purgar el DOM, destruir iframes y detener videos/scripts
        self.web_view.setUrl(QUrl("about:blank"))
        
        # Le decimos al Orquestador que quite esta capa
        self.back_requested.emit()

```

--------------------------------------------------------------------------------

### Archivo: `ui/widget_blend_builder.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_blend_builder.py
# Rol Arquitectónico: UI Component / Batch Entity Genesis Tool
# =========================================================================================

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QWidget, QAbstractItemView,
                               QComboBox, QMessageBox, QStackedWidget,
                               QListWidget, QListWidgetItem, QLineEdit)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QColor

from core.production_manager import ProductionManager
from ui.components.pipeline_wizard import PipelineWizardWidget
from ui.components.progress_dialog import SpawningProgressDialog
from ui.workers.api_queries import FetchProjectsWorker, FetchEntitiesWorker, FetchSequencesWorker, FetchEditStatusWorker, FetchAssetsWorker, FetchShotsWorker, sanitize_kitsu_name
from ui.workers.blender_spawners import BatchCreationWorker, MasterSpawningWorker, StoryboardBatchWorker

class WidgetBlendBuilder(QFrame):
    def __init__(self, parent, auth_manager, config_factory, status_callback, vault_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.auth = auth_manager
        self.config_factory = config_factory
        self.status_callback = status_callback
        self.vault_manager = vault_manager
        
        self.pm_core = ProductionManager(self.auth, self.config_factory)
        self.current_project_id = None
        self.project_map = {}

        self.setObjectName("TransparentGridContainer")
        self._build_ui()
        
        self._load_projects_from_kitsu()
        self._load_templates_from_vault()

    def _inyectar_credenciales_ram(self):
        """Extrae la contraseña de la RAM y la expone efímeramente para el subproceso Headless."""
        if self.vault_manager:
            import os
            #v_data = self.vault_manager.obtener_datos_locales()
            os.environ["OPENSTUDIO_KITSU_USER"] = self.vault_manager._transient_email
            os.environ["OPENSTUDIO_KITSU_PWD"] = self.vault_manager._transient_password

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # --- 1. SELECTOR DE PROYECTO ---
        project_layout = QHBoxLayout()
        lbl_proj = QLabel(self.tr("Active Project:"))
        lbl_proj.setObjectName("InputLabel")
        
        self.combo_projects = QComboBox()
        self.combo_projects.setObjectName("StandardComboBox")
        self.combo_projects.setFixedSize(250, 35)
        self.combo_projects.currentIndexChanged.connect(self._on_project_changed)
        
        project_layout.addWidget(lbl_proj)
        project_layout.addWidget(self.combo_projects)
        project_layout.addStretch()
        main_layout.addLayout(project_layout)

        # --- 2. PIPELINE WIZARD (Top Section) ---
        self.wizard = PipelineWizardWidget(self)
        self.wizard.action_requested.connect(self._ejecutar_fase_pipeline)
        self.wizard.step_changed.connect(self.change_step)
        main_layout.addWidget(self.wizard)

        # --- 3. STACKED WIDGET (Panel Dinámico Inferior) ---
        self.stack = QStackedWidget()
        
        # PÁGINA 0: BREAKDOWN MANUAL DE STORYBOARD
        self.page_storyboard = QWidget()
        sb_layout = QVBoxLayout(self.page_storyboard)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_sb_desc = QLabel(self.tr("Enter the sequences (e.g. SQ010) identified during the script breakdown. This will register them in Kitsu and spawn their physical .blend files."))
        lbl_sb_desc.setObjectName("PageDescription")
        lbl_sb_desc.setWordWrap(True)
        sb_layout.addWidget(lbl_sb_desc)

        input_layout = QHBoxLayout()
        self.input_seq = QLineEdit()
        self.input_seq.setObjectName("FormInput")
        self.input_seq.setPlaceholderText(self.tr("Enter Sequence Name (e.g. SQ010) and press Enter"))
        self.input_seq.setFixedSize(300, 35)
        self.input_seq.returnPressed.connect(self._add_sequence_to_list)
        
        self.btn_add_seq = QPushButton(self.tr("Add"))
        self.btn_add_seq.setObjectName("SecondaryButton")
        self.btn_add_seq.setFixedSize(80, 35)
        self.btn_add_seq.clicked.connect(self._add_sequence_to_list)
        
        input_layout.addWidget(self.input_seq)
        input_layout.addWidget(self.btn_add_seq)
        input_layout.addStretch()
        sb_layout.addLayout(input_layout)
        
        self.list_sequences = QListWidget()
        self.list_sequences.setObjectName("FormInput") 
        sb_layout.addWidget(self.list_sequences)
        
        self.btn_clear_seq = QPushButton(self.tr("Clear List"))
        self.btn_clear_seq.setObjectName("LinkButton")
        self.btn_clear_seq.setCursor(Qt.PointingHandCursor)
        self.btn_clear_seq.clicked.connect(self.list_sequences.clear)
        sb_layout.addWidget(self.btn_clear_seq, alignment=Qt.AlignRight)
        
        self.stack.addWidget(self.page_storyboard)

        # --- NUEVO: PÁGINA 1: RADIOGRAFÍA EDITORIAL ---
        self.page_editorial = QWidget()
        edit_layout = QVBoxLayout(self.page_editorial)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_edit_desc = QLabel(self.tr("Editorial Master configuration and assignment."))
        lbl_edit_desc.setObjectName("PageDescription")
        edit_layout.addWidget(lbl_edit_desc)

        # Tarjeta visual para los datos
        frame_edit = QFrame()
        frame_edit.setObjectName("CardFrame") # O el estilo que uses para tarjetas
        flayout = QVBoxLayout(frame_edit)
        flayout.setSpacing(10)
        
        self.lbl_edit_filename = QLabel(self.tr("File: Scanning..."))
        self.lbl_edit_version = QLabel(self.tr("Version: --"))
        self.lbl_edit_editor = QLabel(self.tr("Assigned to: --"))
        self.lbl_edit_status = QLabel(self.tr("Status: --"))
        
        # Aplicamos estilos de texto corporativo
        for lbl in [self.lbl_edit_filename, self.lbl_edit_version, self.lbl_edit_editor, self.lbl_edit_status]:
            lbl.setObjectName("FormInput") 
            flayout.addWidget(lbl)
            
        edit_layout.addWidget(frame_edit)
        edit_layout.addStretch()
        
        self.stack.addWidget(self.page_editorial)

        # PÁGINA 1: TABLA KANBAN (Edición, Assets, Shots)
        self.page_entities = QWidget()
        ent_layout = QVBoxLayout(self.page_entities)
        ent_layout.setContentsMargins(0, 0, 0, 0)
        
        controls_layout = QHBoxLayout()
        self.lbl_kpi_total = self._create_kpi_label(self.tr("Total Entries: 0"))
        self.lbl_kpi_shots = self._create_kpi_label(self.tr("Shots: 0"))
        self.lbl_kpi_assets = self._create_kpi_label(self.tr("Assets: 0"))

        controls_layout.addWidget(self.lbl_kpi_total)
        controls_layout.addWidget(self.lbl_kpi_shots)
        controls_layout.addWidget(self.lbl_kpi_assets)
        controls_layout.addStretch()
        
        # self.combo_templates = QComboBox()
        # self.combo_templates.setObjectName("StandardComboBox")
        # self.combo_templates.setFixedSize(200, 35)
        # controls_layout.addWidget(self.combo_templates)

        # --- NUEVO: BOTÓN GLOBAL DE ASIGNACIÓN EN KITSU ---
        self.btn_open_kitsu_assets = QPushButton(self.tr("Assign Artists in Kitsu"))
        self.btn_open_kitsu_assets.setObjectName("SecondaryButton")
        self.btn_open_kitsu_assets.setCursor(Qt.PointingHandCursor)
        self.btn_open_kitsu_assets.clicked.connect(self._open_kitsu_assets_view)
        self.btn_open_kitsu_assets.hide() # Oculto por defecto (solo se muestra en paso 3)
        controls_layout.addWidget(self.btn_open_kitsu_assets)

        ent_layout.addLayout(controls_layout)

        # --- NUEVO: PANEL DE CHECKBOXES DE TAREAS (Oculto por defecto) ---
        self.panel_tasks = QWidget()
        self.layout_tasks = QHBoxLayout(self.panel_tasks)
        self.layout_tasks.setContentsMargins(0, 10, 0, 10)
        
        lbl_tasks = QLabel(self.tr("Select Tasks to Spawn:"))
        lbl_tasks.setObjectName("InputLabel")
        self.layout_tasks.addWidget(lbl_tasks)
        
        self.layout_checkboxes = QHBoxLayout()
        self.layout_tasks.addLayout(self.layout_checkboxes)
        self.layout_tasks.addStretch()
        
        self.task_checkboxes = {} # Diccionario para rastrear qué se marcó
        
        ent_layout.addWidget(self.panel_tasks)
        # -----------------------------------------------------------------

        self.table = QTableWidget(0, 6)
        self.table.setObjectName("DataGrid")
        self.table.setHorizontalHeaderLabels(["", self.tr("Entity Name"), self.tr("Type"), self.tr("Parent Sequence"), self.tr("Frame Range"), self.tr("Kitsu Status")])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 40)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        ent_layout.addWidget(self.table, stretch=1)
        self.stack.addWidget(self.page_entities)
        
        main_layout.addWidget(self.stack, stretch=1)

    # --- UI HELPERS ---
    def _create_kpi_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("KPILabel")
        return lbl

    def _create_pill_label(self, text: str, color_hex: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setObjectName("PillLabel")
        lbl.setStyleSheet(f"background-color: {color_hex};")
        layout.addWidget(lbl)
        return widget

    def _open_kitsu_assets_view(self):
        """Abre el navegador en la vista de Assets del proyecto actual."""
        if not self.current_project_id: return
        kitsu_url = self.config_factory.get_kitsu_api_url().replace("/api", "")
        # Construimos la URL paramétrica exacta
        url = f"{kitsu_url}/productions/{self.current_project_id}/assets?search="
        
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))

    def change_step(self, step_number: int):
        if not self.current_project_id: return

        self.wizard.set_step(step_number)
        # self.stack.setCurrentIndex(0 if step_number == 1 else 1)

        if step_number == 1:
            self.stack.setCurrentIndex(0)
        elif step_number == 2:
            self.stack.setCurrentIndex(1)
            self.load_editorial_status()
        elif step_number == 3:
            self.stack.setCurrentIndex(2)
            self.load_assets_from_kitsu()
        elif step_number == 4:
            self.stack.setCurrentIndex(2)
            self.load_shots_from_kitsu() # Para los shots luego
        #else:
            #self.stack.setCurrentIndex(2) # Pasos 3 y 4 van a la tabla Kanban
        
        # if step_number == 2:
        #     self.load_editorial_status()


    def _add_sequence_to_list(self):
        raw_seq_name = self.input_seq.text().strip().upper()
        if not raw_seq_name: return

        seq_name = sanitize_kitsu_name(raw_seq_name)

        for i in range(self.list_sequences.count()):
            item = self.list_sequences.item(i)
            if item.data(Qt.UserRole + 1) == seq_name:
                self.input_seq.clear()
                return

        # Añadir como nueva entidad pendiente
        item = QListWidgetItem(f"{seq_name} (New Entry)")
        item.setData(Qt.UserRole, False) # Aún no tiene archivo físico
        item.setData(Qt.UserRole + 1, seq_name)
        item.setForeground(QColor("#3B82F6")) # Azul
        
        self.list_sequences.addItem(item)
        self.input_seq.clear()
        self.input_seq.setFocus()

    # --- NETWORK / I/O LOGIC ---
    def _load_projects_from_kitsu(self):
        self.combo_projects.blockSignals(True)
        self.combo_projects.addItem(self.tr("Loading projects..."))
        
        self.worker_projects = FetchProjectsWorker()
        self.worker_projects.data_ready.connect(self._on_projects_loaded)
        self.worker_projects.error_occurred.connect(lambda e: self.status_callback(f"Project fetch error: {e}", "red"))
        self.worker_projects.start()

    def _on_projects_loaded(self, projects: list):
        self.combo_projects.clear()
        self.project_map.clear()
        if not projects:
            self.combo_projects.addItem(self.tr("No open projects found"))
            self.combo_projects.blockSignals(False)
            return

        for p in projects:
            self.project_map[p.get("name", "Unknown")] = p.get("id")
            self.combo_projects.addItem(p.get("name", "Unknown"))
        self.combo_projects.blockSignals(False)
        self._on_project_changed()

    def _load_templates_from_vault(self):
        return
        #self.combo_templates.clear()
        # try:
        #     if self.pm_core.vault_templates_dir.exists():
        #         templates = [d.name for d in self.pm_core.vault_templates_dir.iterdir() if d.is_dir() or d.name.endswith(".blend")]
        #         if templates: self.combo_templates.addItems(templates)
        #         else: self.combo_templates.addItem(self.tr("-- No templates --"))
        # except Exception:
        #     self.combo_templates.addItem(self.tr("-- Error reading Vault --"))

    def load_editorial_status(self):
        """Dispara la auditoría del archivo maestro de edición."""
        if not self.current_project_id: return
        
        self.status_callback(self.tr("Auditing Editorial Master..."), "yellow")
        
        # Bloquear el botón temporalmente para evitar clics dobles
        self.wizard.btn_batch_create.setEnabled(False)
        self.wizard.btn_batch_create.setText(self.tr("Scanning..."))
        
        nas_root = self.config_factory.get_workspace_root()
        vfs_svn = self.config_factory.get_vfs_svn_name()
        project_name = self.combo_projects.currentText()
        folder_name = project_name.strip().lower().replace(" ", "-")
        project_root = nas_root / folder_name
        
        self.worker_edit = FetchEditStatusWorker(self.current_project_id, project_name, project_root, vfs_svn)
        self.worker_edit.data_ready.connect(self._render_editorial_status)
        self.worker_edit.error_occurred.connect(lambda e: self.status_callback(f"Edit fetch error: {e}", "red"))
        self.worker_edit.start()

    def load_assets_from_kitsu(self):
        """Dispara la auditoría de todos los assets del proyecto."""
        if not self.current_project_id: return
        self.status_callback(self.tr("Auditing assets from Kitsu and SVN..."), "yellow")
        self.table.setRowCount(0)
        self.btn_open_kitsu_assets.show() # Mostramos el botón en este paso
        
        nas_root = self.config_factory.get_workspace_root()
        vfs_svn = self.config_factory.get_vfs_svn_name()
        project_name = self.combo_projects.currentText()
        folder_name = project_name.strip().lower().replace(" ", "-")
        project_root = nas_root / folder_name
        
        self.worker_assets = FetchAssetsWorker(self.current_project_id, project_root, vfs_svn)
        self.worker_assets.data_ready.connect(self._render_assets)
        self.worker_assets.error_occurred.connect(lambda e: self.status_callback(f"Asset fetch error: {e}", "red"))
        self.worker_assets.start()

    def _render_assets(self, assets: list):
        """Pinta los assets en la tabla Kanban."""
        self.table.setRowCount(len(assets))
        
        for row, asset in enumerate(assets):
            chk_item = QTableWidgetItem()
            
            # Si el archivo ya existe, desmarcamos y bloqueamos el checkbox
            if asset["has_file"]:
                chk_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                chk_item.setCheckState(Qt.Unchecked)
            else:
                chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                chk_item.setCheckState(Qt.Checked) # Autoseleccionar los pendientes
                
            chk_item.setData(Qt.UserRole, asset["raw_data"])
            self.table.setItem(row, 0, chk_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(asset["name"]))
            self.table.setCellWidget(row, 2, self._create_pill_label("Asset", "#8B5CF6"))
            self.table.setItem(row, 3, QTableWidgetItem("N/A"))
            self.table.setItem(row, 4, QTableWidgetItem("N/A"))
            
            # Estado físico visual
            status_text = "✓ File Exists" if asset["has_file"] else "Pending Spawn"
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor("#10B981") if asset["has_file"] else QColor("#F59E0B"))
            self.table.setItem(row, 5, status_item)

        self.lbl_kpi_total.setText(self.tr(f"Total Entries: {len(assets)}"))
        self.lbl_kpi_shots.setText(self.tr("Shots: 0"))
        self.lbl_kpi_assets.setText(self.tr(f"Assets: {len(assets)}"))
        self.status_callback(self.tr("✓ Assets loaded."), "green")

    def _render_editorial_status(self, edit_data: dict):
        """Pinta los resultados en pantalla y muta el CTA del Wizard."""
        self.status_callback(self.tr("Editorial audit complete."), "green")
        

        # AQUÍ puedes actualizar el layout secundario del QStackedWidget para mostrar el dict edit_data
        self.lbl_edit_filename.setText(self.tr(f"File Name: {edit_data['file_name']}"))
        self.lbl_edit_version.setText(self.tr(f"Version: {edit_data['version']}"))
        self.lbl_edit_editor.setText(self.tr(f"Assigned Editor: {edit_data['assignees']}"))
        self.lbl_edit_status.setText(self.tr(f"Task Status: {edit_data['status']}"))

        self.wizard.btn_batch_create.setEnabled(True)
        
        if edit_data["has_file"]:
            self.wizard.btn_batch_create.setText(self.tr("Assign Editor in Kitsu"))
            self.wizard.btn_batch_create.setObjectName("SecondaryButton")
            self.edit_action_mode = "ASSIGN" 
        else:
            self.wizard.btn_batch_create.setText(self.tr("Spawn Edit Master"))
            self.wizard.btn_batch_create.setObjectName("OrangeCTA")
            self.edit_action_mode = "SPAWN"
        
        self.wizard.btn_batch_create.style().polish(self.wizard.btn_batch_create)

    def _on_project_changed(self):
        project_name = self.combo_projects.currentText()
        if project_name in self.project_map:
            self.current_project_id = self.project_map[project_name]
            self.change_step(1) # Forzar paso 1 al cambiar de proyecto
            self.load_shots_from_kitsu()
            self.load_sequences_from_kitsu()

    def load_shots_from_kitsu(self):
        if not self.current_project_id: return
        self.status_callback(self.tr("Fetching pending shots from Kitsu..."), "yellow")
        self.table.setRowCount(0)
        
        nas_root = self.config_factory.get_workspace_root()
        vfs_svn = self.config_factory.get_vfs_svn_name()
        project_name = self.combo_projects.currentText()
        folder_name = project_name.strip().lower().replace(" ", "-")
        project_root = nas_root / folder_name

        self.worker_entities = FetchShotsWorker(self.current_project_id, project_root, vfs_svn)
        self.worker_entities.data_ready.connect(self._render_shots)
        self.worker_entities.error_occurred.connect(lambda e: self.status_callback(f"Shot fetch error: {e}", "red"))
        self.worker_entities.start()

    def _render_shots(self, shots: list, task_types: list):
        # 1. Preparar las columnas dinámicas
        base_headers = ["", self.tr("Shot Name"), self.tr("Sequence"), self.tr("Frames")]
        all_headers = base_headers + task_types
        
        self.table.setColumnCount(len(all_headers))
        self.table.setHorizontalHeaderLabels(all_headers)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 40)
        for i in range(1, len(base_headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        for i in range(len(base_headers), len(all_headers)):
            header.setSectionResizeMode(i, QHeaderView.Stretch) # Expandir columnas de tareas

        self.table.setRowCount(len(shots))
        shots_count = len(shots)
        
        # 2. Reconstruir los checkboxes globales
        self.panel_tasks.show()
        # Limpiar checkboxes anteriores
        while self.layout_checkboxes.count():
            child = self.layout_checkboxes.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        self.task_checkboxes.clear()
        for tt_name in task_types:
            from PySide6.QtWidgets import QCheckBox
            chk = QCheckBox(tt_name)
            chk.setChecked(True) # Marcados por defecto
            self.task_checkboxes[tt_name] = chk
            self.layout_checkboxes.addWidget(chk)
        
        # 3. Llenar la Matriz
        for row, entity in enumerate(shots):
            chk_item = QTableWidgetItem()
            has_all_files = entity.get("has_file", False)
            
            if has_all_files:
                chk_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                chk_item.setCheckState(Qt.Unchecked)
            else:
                chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                chk_item.setCheckState(Qt.Checked)
                
            chk_item.setData(Qt.UserRole, entity) # Guardamos TODO el diccionario de la entidad
            self.table.setItem(row, 0, chk_item)
            
            self.table.setItem(row, 1, QTableWidgetItem(entity.get("name", "Unknown")))
            self.table.setItem(row, 2, QTableWidgetItem(entity.get("parent", "Unknown")))
            self.table.setItem(row, 3, QTableWidgetItem(str(entity.get("frame_in", 0))))
            
            # Pintar las celdas de tareas
            tasks_data = entity.get("tasks", {})
            for col_idx, tt_name in enumerate(task_types):
                table_col = len(base_headers) + col_idx
                
                if tt_name in tasks_data:
                    task_info = tasks_data[tt_name]
                    if task_info["has_file"]:
                        self.table.setCellWidget(row, table_col, self._create_pill_label("✓ Ready", "#10B981"))
                    else:
                        self.table.setCellWidget(row, table_col, self._create_pill_label("Pending", "#F59E0B"))
                else:
                    self.table.setCellWidget(row, table_col, self._create_pill_label("N/A", "#4B5563")) # Gris oscuro si no aplica

        self.lbl_kpi_total.setText(self.tr(f"Total Entries: {shots_count}"))
        self.lbl_kpi_shots.setText(self.tr(f"Shots: {shots_count}"))
        self.lbl_kpi_assets.setText(self.tr("Assets: 0"))
        
        self.status_callback(self.tr("✓ Shots matrix loaded."), "green")
    
    def load_sequences_from_kitsu(self):
        if not self.current_project_id: return
        self.list_sequences.clear()
        self.list_sequences.addItem(self.tr("Auditing sequences from Kitsu and SVN..."))
        
        # Calcular rutas físicas usando tu ConfigFactory
        nas_root = self.config_factory.get_workspace_root()
        vfs_svn = self.config_factory.get_vfs_svn_name()
        project_name = self.combo_projects.currentText()
        folder_name = project_name.strip().lower().replace(" ", "-")
        project_root = nas_root / folder_name
        
        self.worker_seqs = FetchSequencesWorker(self.current_project_id, project_root, vfs_svn)
        self.worker_seqs.data_ready.connect(self._render_sequences)
        self.worker_seqs.error_occurred.connect(lambda e: self.status_callback(f"Seq fetch error: {e}", "red"))
        self.worker_seqs.start()

    def _render_sequences(self, sequences: list):
        self.list_sequences.clear()
        
        for seq in sequences:
            name = seq["name"]
            has_file = seq["has_file"]
            
            # Feedback visual de estado
            label = f"{name} (✓ File Exists)" if has_file else f"{name} (Pending Spawn)"
            item = QListWidgetItem(label)
            
            # INYECCIÓN CLAVE: Guardamos el estado y el nombre limpio de forma invisible
            item.setData(Qt.UserRole, has_file)
            item.setData(Qt.UserRole + 1, name)
            
            # Colorear según el estado físico (Verdad SVN)
            if has_file:
                item.setForeground(QColor("#10B981")) # Verde (Listo)
            else:
                item.setForeground(QColor("#F59E0B")) # Naranja (Pendiente)
                
            self.list_sequences.addItem(item)
    
    # --- ENRUTADOR PRINCIPAL ---

    def _ejecutar_fase_pipeline(self, step_id: int):
        if not self.current_project_id:
            self.status_callback(self.tr("Please select a project first."), "yellow")
            return

        if step_id == 1:
            if self.input_seq.text().strip():
                self._add_sequence_to_list()
                
            # 1. Filtrar SOLO las secuencias pendientes
            pending_sequences = []
            for i in range(self.list_sequences.count()):
                item = self.list_sequences.item(i)
                has_file = item.data(Qt.UserRole)
                if not has_file: # Si no tiene archivo físico
                    clean_name = item.data(Qt.UserRole + 1)
                    pending_sequences.append(clean_name)
                    
            if not pending_sequences:
                QMessageBox.information(self, self.tr("System Checked"), self.tr("All listed sequences already have physical files. Nothing to spawn."))
                return
                
            # 2. Preparar UI y Modal
            self.status_callback(self.tr("Spawning Storyboard sequences..."), "yellow")
            project_name = self.combo_projects.currentText()
            self.progress_modal = SpawningProgressDialog(self, self.tr("Batch Spawning Storyboards"))
            self.progress_modal.show()
            
            self._inyectar_credenciales_ram()
            # 3. Lanzar Worker SOLO con las pendientes
            self.spawn_worker = StoryboardBatchWorker(self.pm_core, self.config_factory, self.current_project_id, project_name, pending_sequences)
            self.spawn_worker.progress_updated.connect(self.progress_modal.update_progress)
            self.spawn_worker.log_stream.connect(self.progress_modal.append_log)
            
            def open_kitsu():
                kitsu_url = self.config_factory.get_kitsu_api_url().replace("/api", "")
                url = f"{kitsu_url}/productions/{self.current_project_id}/shots"
                from PySide6.QtGui import QDesktopServices
                from PySide6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl(url))
                self.progress_modal.accept()

            def on_sb_finished(success, msg):
                if success:
                    self.status_callback(self.tr(f"✓ {msg}"), "green")
                    self.change_step(2)
                    self.progress_modal.finalize(True, self.tr("Success: Storyboards spawned."), "Assign Artists in Kitsu", open_kitsu)
                    # RECARGA AUTOMÁTICA para pintar de verde
                    self.load_sequences_from_kitsu() 
                else:
                    self.status_callback(self.tr(f"✗ Error: {msg}"), "red")
                    self.progress_modal.finalize(False, self.tr("Process completed with errors. Check logs."))

            self.spawn_worker.finished_batch.connect(on_sb_finished)
            self.spawn_worker.start()
            
        elif step_id == 2:
            if getattr(self, "edit_action_mode", "SPAWN") == "ASSIGN":
                # Abrimos Kitsu en el navegador para la asignación manual
                kitsu_url = self.config_factory.get_kitsu_api_url().replace("/api", "")
                url = f"{kitsu_url}/productions/{self.current_project_id}/edits"
                
                QDesktopServices.openUrl(QUrl(url))
                self.status_callback(self.tr("Opened Kitsu for assignment."), "white")
                return

            project_name = self.combo_projects.currentText()
            self.progress_modal = SpawningProgressDialog(self, self.tr("Spawning EDIT Master"))
            self.progress_modal.show()

            self.spawn_worker = MasterSpawningWorker(
                self.config_factory, project_name, "EDIT", self.current_project_id
            )
            
            self.spawn_worker.progress_updated.connect(self.progress_modal.update_progress)
            self.spawn_worker.log_stream.connect(self.progress_modal.append_log)
            
            def on_finished(success, msg):
                if success:
                    self.status_callback(self.tr(f"✓ {msg}"), "green")
                    self.change_step(3)
                    self.progress_modal.finalize(True, self.tr("Success: EDIT Master forged."))
                else:
                    self.status_callback(self.tr(f"✗ Error: {msg}"), "red")
                    self.progress_modal.finalize(False, self.tr("Process completed with errors. Check logs."))
                    
            self.spawn_worker.finished_spawn.connect(on_finished)
            self.spawn_worker.start()

        elif step_id in [3, 4]:

            #self.status_callback(self.tr("Batch Creating shots..."), "yellow")
            self._trigger_batch_creation(step_id)

    def _trigger_batch_creation(self, step_id: int):
        selected_entities = [self.table.item(r, 0).data(Qt.UserRole) for r in range(self.table.rowCount()) if self.table.item(r, 0).checkState() == Qt.Checked]
        if not selected_entities:
            QMessageBox.information(self, self.tr("System Checked"), self.tr("No pending entities selected to spawn."))
            return
            
        # --- NUEVO: RECOLECTAR TAREAS SELECCIONADAS ---
        selected_tasks = []
        if step_id == 4: # Solo aplicamos la matriz a los Shots
            selected_tasks = [name for name, chk in self.task_checkboxes.items() if chk.isChecked()]
            if not selected_tasks:
                QMessageBox.warning(self, self.tr("Missing Tasks"), self.tr("Please select at least one task type to spawn."))
                return
        else:
            # Tareas por defecto para Assets
            selected_tasks = ["Modeling", "Rigging", "Shading", "Concept"]
        # ----------------------------------------------

        # Levantar ventana de log modal
        self.progress_modal = SpawningProgressDialog(self, self.tr("Batch Spawning Production Files"))
        self.progress_modal.show()
        
        # Interceptor: Redirigimos el callback del worker hacia el log visual
        def intercept_log(msg: str, color: str = "white"):
            self.progress_modal.append_log(msg)
            self.progress_modal.update_progress(50, self.tr("Forging..."))
            
        self._inyectar_credenciales_ram()
        self.worker_batch = BatchCreationWorker(
            pm_core=self.pm_core,
            config_factory=self.config_factory,
            project_id=self.current_project_id,
            project_name=self.combo_projects.currentText(),
            entities=selected_entities,
            task_types=selected_tasks, # Tareas comunes de Assets
            #status_cb=intercept_log # <-- Inyección del interceptor
        )

        # Conectar las señales directamente al modal flotante
        self.worker_batch.progress_updated.connect(self.progress_modal.update_progress)
        self.worker_batch.log_stream.connect(self.progress_modal.append_log)

        def on_batch_finished(success: bool, message: str):
            if success:
                self.progress_modal.update_progress(100, self.tr("Done!"))
                self.progress_modal.finalize(True, self.tr("Success: Files Spawned."), "Assign in Kitsu", self._open_kitsu_assets_view)
                if step_id == 3:
                    self.load_assets_from_kitsu() # Recargar la lista de Assets
                elif step_id == 4:
                    self.load_shots_from_kitsu()
            else:
                self.progress_modal.finalize(False, self.tr("Process completed with errors. Check logs."))
                QMessageBox.critical(self, self.tr("Batch Creation Failed"), message)
                
        self.worker_batch.finished_batch.connect(on_batch_finished)
        self.worker_batch.start()

```

--------------------------------------------------------------------------------

### Archivo: `ui/widget_infrastructure.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_infrastructure.py
# Rol Arquitectónico: UI Component / Infrastructure Controller
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.1.0 (Database Seeders & Healthchecks)
# =========================================================================================

"""
Panel de control de infraestructura del estudio.
Permite aprovisionar, iniciar y detener servidores locales (SVN, Kitsu) 
utilizando contenedores Docker efímeros para pruebas y desarrollo.
Incluye comandos automatizados para inyectar datos de prueba en la BD local.
"""

import os
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QWidget, QMessageBox, QGridLayout)
from PySide6.QtCore import Qt, QThread, Signal

from core.kitsu_manager import KitsuManager

class DockerWorker(QThread):
    """Hilo secundario para no congelar la UI mientras Docker descarga y levanta contenedores."""
    finished_signal = Signal(bool, str)
    
    def __init__(self, command: list, cwd: Path = None):
        super().__init__()
        self.command = command
        self.cwd = cwd

    def run(self):
        try:
            result = subprocess.run(
                self.command, 
                cwd=self.cwd,
                check=True, 
                capture_output=True, 
                text=True
            )
            self.finished_signal.emit(True, "Operación completada exitosamente.")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            self.finished_signal.emit(False, f"Fallo en Docker: {error_msg}")
        except Exception as e:
            self.finished_signal.emit(False, f"Error del sistema: {str(e)}")


class KitsuSeederWorker(QThread):
    """Hilo dedicado a interactuar con la base de datos de Kitsu vía Gazu y línea de comandos."""
    finished_signal = Signal(bool, str)

    def __init__(self, action: str):
        super().__init__()
        self.action = action

    def run(self):
        try:
            if self.action == "admin":
                # 1. Creamos al admin vía CLI de Zou en Docker para bypassear la falta inicial de sesión
                # La contraseña debe tener al menos 8 caracteres para no fallar la validación interna
                pwd = "entrando1"
                cmd = [
                    "docker", "exec", "kitsu_local-zou-app", "zou", 
                    "create-admin", "admin@example.com", "--password", pwd
                ]
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                self.finished_signal.emit(True, "Admin Creado: admin@example.com / entrando1")

            elif self.action == "dummy":
                # 2. Inyectamos a los usuarios Dummy consumiendo el Manager
                kitsu_mgr = KitsuManager()
                # Sobrescribimos temporalmente el host para apuntar al entorno de prueba local (Docker)
                import gazu
                gazu.set_host('http://localhost:8080/api')
                
                success, msg = kitsu_mgr.seed_test_database(
                    admin_email="admin@example.com", 
                    admin_pwd="entrando1"
                )
                self.finished_signal.emit(success, msg)
                
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            self.finished_signal.emit(False, f"Error del Contenedor: {error_msg}")
        except Exception as e:
            self.finished_signal.emit(False, f"Fallo en Seeder: {str(e)}")


class InfrastructureWidget(QFrame):
    def __init__(self, parent, config_factory, status_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.config_factory = config_factory
        self.status_callback = status_callback
        
        self.infra_dir = self.config_factory.get_workspace_root() / ".openstudio_infra"
        self.infra_dir.mkdir(parents=True, exist_ok=True)
        
        self.setObjectName("InfrastructureBase")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # ---------------------------------------------------------
        # HEADER
        # ---------------------------------------------------------
        header = QLabel(self.tr("Studio Infrastructure (Zero-Config Environments)"))
        header.setStyleSheet("color: #F8FAFC; font-size: 20px; font-weight: bold;")
        layout.addWidget(header)
        
        desc = QLabel(self.tr("Deploy local instances of Subversion and Kitsu for testing and development. Requires Docker installed and running."))
        desc.setStyleSheet("color: #94A3B8; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ---------------------------------------------------------
        # GRID CARDS
        # ---------------------------------------------------------
        grid = QGridLayout()
        grid.setSpacing(20)

        # TARJETA 1: SVN SERVER
        svn_card = self._build_service_card(
            title="Local VCS Server (SVN)",
            desc=self.tr("Centralized version control system for binary assets and scenes."),
            port="3690",
            start_callback=self._deploy_svn,
            stop_callback=self._stop_svn
        )
        grid.addWidget(svn_card, 0, 0)

        # TARJETA 2: KITSU TRACKER (CON BOTONES EXTRA)
        kitsu_card = self._build_kitsu_service_card()
        grid.addWidget(kitsu_card, 0, 1)

        layout.addLayout(grid)
        layout.addStretch()

    def _build_service_card(self, title: str, desc: str, port: str, start_callback, stop_callback) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame { background-color: #1E293B; border-radius: 12px; border: 1px solid #334155; }
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: bold; border: none;")
        c_layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 12px; border: none;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)
        
        lbl_port = QLabel(f"Port: {port}")
        lbl_port.setStyleSheet("color: #3B82F6; font-size: 11px; font-weight: bold; border: none;")
        c_layout.addWidget(lbl_port)
        
        c_layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_start = QPushButton(self.tr("Deploy & Start"))
        btn_start.setStyleSheet("""
            QPushButton { background-color: #10B981; color: white; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_start.clicked.connect(start_callback)
        
        btn_stop = QPushButton(self.tr("Stop & Destroy"))
        btn_stop.setStyleSheet("""
            QPushButton { background-color: #EF4444; color: white; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #DC2626; }
        """)
        btn_stop.clicked.connect(stop_callback)
        
        btn_layout.addWidget(btn_start)
        btn_layout.addWidget(btn_stop)
        
        c_layout.addLayout(btn_layout)
        return card

    def _build_kitsu_service_card(self) -> QFrame:
        """Constructor especializado para Kitsu que incluye los botones de sembrado de base de datos."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame { background-color: #1E293B; border-radius: 12px; border: 1px solid #334155; }
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 20, 20, 20)
        c_layout.setSpacing(10)
        
        lbl_title = QLabel("Production Tracker (Kitsu 1.0+)")
        lbl_title.setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: bold; border: none;")
        c_layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(self.tr("Database, API, and Web Frontend for Shot and Asset management."))
        lbl_desc.setStyleSheet("color: #94A3B8; font-size: 12px; border: none;")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)
        
        lbl_port = QLabel(f"Port: 8080")
        lbl_port.setStyleSheet("color: #3B82F6; font-size: 11px; font-weight: bold; border: none;")
        c_layout.addWidget(lbl_port)
        
        c_layout.addStretch()
        
        # Fila 1 de Botones: Control de Ciclo de Vida
        btn_layout1 = QHBoxLayout()
        btn_start = QPushButton(self.tr("Deploy & Start"))
        btn_start.setStyleSheet("""
            QPushButton { background-color: #10B981; color: white; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_start.clicked.connect(self._deploy_kitsu)
        
        btn_stop = QPushButton(self.tr("Stop & Destroy"))
        btn_stop.setStyleSheet("""
            QPushButton { background-color: #EF4444; color: white; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #DC2626; }
        """)
        btn_stop.clicked.connect(self._stop_kitsu)
        btn_layout1.addWidget(btn_start)
        btn_layout1.addWidget(btn_stop)
        
        # Fila 2 de Botones: Base de Datos & Sembrado
        btn_layout2 = QHBoxLayout()
        btn_seed_admin = QPushButton(self.tr("1. Create Admin Account"))
        btn_seed_admin.setToolTip("Ejecuta 'zou create-admin' dentro del contenedor.")
        btn_seed_admin.setStyleSheet("""
            QPushButton { background-color: #334155; color: white; border-radius: 6px; padding: 8px; font-weight: bold; font-size: 11px; }
            QPushButton:hover { background-color: #475569; }
        """)
        btn_seed_admin.clicked.connect(lambda: self._ejecutar_seeder("admin"))
        
        btn_seed_dummy = QPushButton(self.tr("2. Seed Dummy Team"))
        btn_seed_dummy.setToolTip("Inyecta a PM, TD y Artist vía Gazu API.")
        btn_seed_dummy.setStyleSheet("""
            QPushButton { background-color: #334155; color: white; border-radius: 6px; padding: 8px; font-weight: bold; font-size: 11px; }
            QPushButton:hover { background-color: #475569; }
        """)
        btn_seed_dummy.clicked.connect(lambda: self._ejecutar_seeder("dummy"))
        btn_layout2.addWidget(btn_seed_admin)
        btn_layout2.addWidget(btn_seed_dummy)

        c_layout.addLayout(btn_layout1)
        c_layout.addLayout(btn_layout2)
        
        return card

    # ---------------------------------------------------------
    # SVN CONTROLLERS
    # ---------------------------------------------------------
    def _deploy_svn(self):
        self.status_callback(self.tr("Deploying Local SVN Server. Please wait..."), "yellow")
        command = [
            "docker", "run", "-d", 
            "--name", "openstudio_local_svn", 
            "-p", "3690:3690", 
            "elleflorio/svn-server"
        ]
        self._run_docker_worker(command)

    def _stop_svn(self):
        self.status_callback(self.tr("Destroying SVN Server..."), "yellow")
        subprocess.run(["docker", "stop", "openstudio_local_svn"], capture_output=True)
        subprocess.run(["docker", "rm", "openstudio_local_svn"], capture_output=True)
        self.status_callback(self.tr("SVN Server destroyed."), "green")

    # ---------------------------------------------------------
    # KITSU CONTROLLERS
    # ---------------------------------------------------------
    def _deploy_kitsu(self):
        self.status_callback(self.tr("Generando nueva arquitectura Docker Compose para Kitsu. Espere por favor..."), "yellow")
        
        # 1. Preparar archivos locales requeridos por los volúmenes
        db_dir = self.infra_dir / "db"
        db_dir.mkdir(exist_ok=True)
        pg_ctl = db_dir / "pg_ctl.conf"
        if not pg_ctl.exists():
            pg_ctl.write_text("# Autogenerado por la Infraestructura de Open Studio Hub\n")

        # 2. Generar archivo 'env'
        env_content = """COMPOSE_PROJECT_NAME=kitsu_local
ENV_FILE=env
KITSU_VERSION=latest
ZOU_VERSION=latest
KV_HOST=redis
KV_PORT=6379
DB_HOST=db
DB_VERSION=18
DB_USERNAME=postgres
DB_PASSWORD=Un53cur3Pa55w0rd
DB_DATABASE=zoudb
DB_DATA_PATH=/var/lib/data
ENABLE_JOB_QUEUE=True
PREVIEW_FOLDER=/opt/zou/previews
TMP_DIR=/tmp/zou
EVENT_STREAM_HOST=zou-event
PORT=80
INDEXER_VERSION=v1.31
INDEXER_KEY=Un53cur3Ma55t3rK3y
INDEXER_HOST=indexer
INDEXER_PORT=7700
USER_LIMIT=200
SECRET_KEY=Op3nStud1oHubZ0uS3cr3tK3y2026V3ryS3cur3
"""
        with open(self.infra_dir / "env", "w") as f:
            f.write(env_content)

        # 3. Generar Docker Compose con inicialización inteligente (healthchecks y comandos pre-boot)
        compose_content = r"""x-base: &base
    restart: always
    networks:
        - internal

x-env: &env
    env_file:
        - ${ENV_FILE:-./env}

x-backend-volumes: &backend_volumes
    volumes:
        - 'previews:${PREVIEW_FOLDER:?}'
        - 'tmp:${TMP_DIR:-/tmp/zou}'

services:
    kitsu:
        <<: [*base, *env]
        container_name: ${COMPOSE_PROJECT_NAME:?}-frontend
        image: registry.gitlab.com/mathbou/docker-cgwire/kitsu:${KITSU_VERSION:-latest}
        ports:
            - "8080:80"
        depends_on:
            zou-app:
                condition: service_healthy
            zou-event:
                condition: service_started
            zou-jobs:
                condition: service_started

    zou-app:
        <<: [*base,*env, *backend_volumes]
        container_name: ${COMPOSE_PROJECT_NAME:?}-zou-app
        image: registry.gitlab.com/mathbou/docker-cgwire/zou:${ZOU_VERSION:-latest}
        depends_on:
            db:
                condition: service_healthy
            indexer:
                condition: service_healthy
        command: >
            sh -c "zou init-db || true &&
                   zou upgrade-db || true &&
                   zou init-data || true &&
                   gunicorn --error-logfile - --access-logfile - -w 3 -k gevent -b :5000 zou.app:app"
        healthcheck:
            test: "curl -s -f http://localhost:5000 | grep -q '\"api\":\"Zou\"'"

    zou-event:
        <<: [*base, *env]
        container_name: ${COMPOSE_PROJECT_NAME:?}-zou-event
        image: registry.gitlab.com/mathbou/docker-cgwire/zou:${ZOU_VERSION:-latest}
        depends_on:
            redis:
                condition: service_started
            zou-app:
                condition: service_healthy
        command: "gunicorn --error-logfile - --access-logfile - -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -b :5001 zou.event_stream:app"
        healthcheck:
            test: "curl -s -f http://localhost:5001 | grep -q '\"api\":\"Zou\"'"

    zou-jobs:
        <<: [*base, *env, *backend_volumes]
        container_name: ${COMPOSE_PROJECT_NAME:?}-zou-jobs
        image: registry.gitlab.com/mathbou/docker-cgwire/zou:${ZOU_VERSION:-latest}
        depends_on:
            zou-app:
                condition: service_healthy
        command: "rq worker -c zou.job_settings"
        healthcheck:
            test: "rq info -u redis://${KV_HOST:?}:${KV_PORT:-6379}/3 -W | grep -v -q '0 workers'"

    db:
        <<: *base
        container_name: ${COMPOSE_PROJECT_NAME:?}-db-${DB_VERSION:?}
        image: postgres:${DB_VERSION:?}-alpine
        volumes:
            - 'db:${DB_DATA_PATH:?}'
            - ./db/pg_ctl.conf:/etc/postgresql/${DB_VERSION:?}/main/pg_ctl.conf:ro
        environment:
            - POSTGRES_PASSWORD=${DB_PASSWORD:?}
            - POSTGRES_DB=zoudb
        healthcheck:
            test: "pg_isready -d zoudb -U postgres"

    redis:
        <<: *base
        container_name: ${COMPOSE_PROJECT_NAME:?}-redis
        image: redis:alpine
        volumes:
            - 'redis:/data'
    
    indexer:
        <<: *base
        container_name: ${COMPOSE_PROJECT_NAME:?}-indexer-${INDEXER_VERSION:?}
        image: getmeili/meilisearch:${INDEXER_VERSION:?}
        volumes:
            - 'indexer:/meili_data'
        environment:
            - MEILI_MASTER_KEY=${INDEXER_KEY:?}
        healthcheck:
            test: "curl -s -f http://localhost:${INDEXER_PORT:-7700}/health | grep -q '{\"status\":\"available\"}'"

volumes:
    db:
        name: ${COMPOSE_PROJECT_NAME:?}-db-${DB_VERSION:?}
    redis:
        name: ${COMPOSE_PROJECT_NAME:?}-redis
    previews:
        name: ${COMPOSE_PROJECT_NAME:?}-previews
    tmp:
        name: ${COMPOSE_PROJECT_NAME:?}-tmp
    indexer:
        name: ${COMPOSE_PROJECT_NAME:?}-indexer-${INDEXER_VERSION:?}
        
networks:
    internal:
        name: ${COMPOSE_PROJECT_NAME:?}-internal
"""
        compose_path = self.infra_dir / "docker-compose.yml"
        with open(compose_path, "w") as f:
            f.write(compose_content)

        # 4. Levantar Contenedores asíncronamente
        command = ["docker", "compose", "--env-file", "env", "up", "-d"]
        self._run_docker_worker(command, cwd=self.infra_dir)

    def _stop_kitsu(self):
        self.status_callback(self.tr("Tearing down Kitsu Stack..."), "yellow")
        command = ["docker", "compose", "down", "-v"] 
        self._run_docker_worker(command, cwd=self.infra_dir)

    # ---------------------------------------------------------
    # SEEDER DISPATCHER
    # ---------------------------------------------------------
    def _ejecutar_seeder(self, action: str):
        self.status_callback(self.tr("Ejecutando Seeder en la Base de Datos..."), "yellow")
        self.seeder_worker = KitsuSeederWorker(action)
        self.seeder_worker.finished_signal.connect(self._on_worker_finished)
        self.seeder_worker.finished.connect(self.seeder_worker.deleteLater)
        self.seeder_worker.start()

    # ---------------------------------------------------------
    # WORKER CALLBACK
    # ---------------------------------------------------------
    def _run_docker_worker(self, command: list, cwd: Path = None):
        self.worker = DockerWorker(command, cwd)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _on_worker_finished(self, success: bool, message: str):
        color = "green" if success else "red"
        self.status_callback(message, color)
        if not success:
            QMessageBox.critical(self, self.tr("Error de Infraestructura"), message)

```

--------------------------------------------------------------------------------

### Archivo: `ui/widget_project_list.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_project_list.py
# Rol Arquitectónico: UI Component / TD Project Grid (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.3.0 (Auto-Refresh & Reload Hooks)
# =========================================================================================

"""
Componente independiente para la Lista de Proyectos del TD.
Encapsula la lógica de cuadrícula responsiva, extracción de datos vía Kitsu
y el botón de creación de nuevos proyectos.
Integra ganchos (hooks) de auto-recarga tras operaciones destructivas.
"""

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, 
                               QLabel, QPushButton, QScrollArea, QWidget)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QResizeEvent
from pathlib import Path

from ui.window_new_project import NewProjectWindow
from ui.components.project_card import ProjectCard

class ProjectGridWorker(QThread):
    """Hilo secundario para extraer los proyectos abiertos del estudio desde Kitsu."""
    data_ready = Signal(list)

    def __init__(self, auth_manager):
        super().__init__()
        self.auth = auth_manager

    def run(self):
        import gazu
        try:
            proyectos = gazu.project.all_open_projects()
            self.data_ready.emit(proyectos)
        except Exception as e:
            print(f"[ProjectList] Error obteniendo proyectos: {e}")
            self.data_ready.emit([])


class ProjectListWidget(QFrame):
    def __init__(self, parent, nas_dir: Path, auth_manager, vault_manager, config_factory, 
                 status_callback, on_open_wizard_callback=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.nas_dir = nas_dir
        self.auth = auth_manager
        self.vault = vault_manager
        self.config_factory = config_factory
        self.status_callback = status_callback
        self.on_open_wizard_callback = on_open_wizard_callback
        
        self.user_role = self.auth.get_user_role() if hasattr(self.auth, 'get_user_role') else "user"
        
        self._project_widgets = []
        self._current_cols = 0
        
        self.setObjectName("ProjectListWidgetBase")
        self.setStyleSheet("background: transparent;")
        
        self._build_ui()

    def _build_ui(self):
        content_layout = QVBoxLayout(self)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # ---------------------------------------------------------
        # HERO ACTION (Botones de Cabecera)
        # ---------------------------------------------------------
        hero_layout = QHBoxLayout()
        hero_layout.setContentsMargins(0, 0, 0, 0)
        
        if self.user_role != "td":
            lbl_title = QLabel(self.tr("My Assigned Projects"))
            lbl_title.setObjectName("H2Title")
            hero_layout.addWidget(lbl_title)
            
        hero_layout.addStretch()
        
        self.btn_refrescar = QPushButton(self.tr("🔄 Refresh List"))
        self.btn_refrescar.setObjectName("SecondaryButton")
        self.btn_refrescar.setFixedSize(150, 40)
        self.btn_refrescar.setCursor(Qt.PointingHandCursor)
        self.btn_refrescar.clicked.connect(self.cargar_proyectos)
        hero_layout.addWidget(self.btn_refrescar)

        # breakpoint()
        
        if self.user_role == "td":
            self.btn_nuevo_proy = QPushButton(self.tr("+ Create New Project"))
            self.btn_nuevo_proy.setObjectName("PrimaryButton") 
            self.btn_nuevo_proy.setFixedSize(220, 40)
            self.btn_nuevo_proy.setCursor(Qt.PointingHandCursor)
            self.btn_nuevo_proy.clicked.connect(self.abrir_wizard_proyecto)
            hero_layout.addWidget(self.btn_nuevo_proy)
        
        content_layout.addLayout(hero_layout)

        # ---------------------------------------------------------
        # CONTENEDOR GRID CON SCROLL
        # ---------------------------------------------------------
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("InvisibleScrollArea")
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.grid_widget = QWidget()
        self.grid_widget.setObjectName("TransparentGridContainer")
        self.grid_widget.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)  
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.scroll_area.setWidget(self.grid_widget)
        content_layout.addWidget(self.scroll_area, stretch=1)

    # ---------------------------------------------------------
    # RESPONSIVE GRID LOGIC
    # ---------------------------------------------------------

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._rearrange_grid()

    def _rearrange_grid(self):
        if not self._project_widgets: return
        viewport_width = self.scroll_area.viewport().width()
        card_width = 340 if self.user_role != "td" else 320 
        spacing = self.grid_layout.spacing()
        cols = max(1, (viewport_width + spacing) // (card_width + spacing))

        if getattr(self, '_current_cols', 0) == cols: return
        self._current_cols = cols
        row, col = 0, 0

        for widget in self._project_widgets:
            self.grid_layout.removeWidget(widget)
            self.grid_layout.addWidget(widget, row, col)
            
            col += 1
            if col >= cols:
                col = 0
                row += 1

    # ---------------------------------------------------------
    # LÓGICA DE DATOS
    # ---------------------------------------------------------

    def _emit_status(self, mensaje: str, color: str = "white"):
        if self.status_callback: self.status_callback(mensaje, color)

    def cargar_proyectos(self):
        self._emit_status(self.tr("Syncing projects catalog..."), "yellow")
        self.btn_refrescar.setEnabled(False)
        
        for widget in self._project_widgets:
            widget.hide()
            widget.deleteLater()
        self._project_widgets.clear()
        
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
                
        self.worker = ProjectGridWorker(self.auth)
        self.worker.data_ready.connect(self._renderizar_proyectos)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _renderizar_proyectos(self, proyectos: list):
        self.btn_refrescar.setEnabled(True)
        if not proyectos:
            self._emit_status(self.tr("No active projects found."), "yellow")
            return
            
        self._emit_status(self.tr("🟢 Synchronized: {0} active projects.").format(len(proyectos)), "green")
        
        for project_data in proyectos:
            tarjeta = ProjectCard(
                parent=self.grid_widget,
                project_data=project_data,
                auth_manager=self.auth,
                nas_dir=self.nas_dir,
                config_factory=self.config_factory,
                vault_manager=self.vault,
                on_rebuild_callback=self.cargar_proyectos,
                on_open_wizard_callback=self.on_open_wizard_callback,
                status_callback=self.status_callback
            )

            self._project_widgets.append(tarjeta)
            
        self._current_cols = 0 
        self._rearrange_grid()

    def abrir_wizard_proyecto(self):
        self.wizard_window = NewProjectWindow(
            parent=self.window(),
            config_factory=self.config_factory,
            on_success_callback=self.cargar_proyectos
        )
        self.wizard_window.show()

```

--------------------------------------------------------------------------------

### Archivo: `ui/widget_settings.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_settings.py
# Rol Arquitectónico: UI Orchestrator / Global Settings Container (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.6.2 (Strict Dependency Injection Overhaul)
# =========================================================================================

"""
Global Configuration Panel for the Technical Director.
Groups decoupled molecular sub-tabs (Identity, Vault, VCS, Topography, Software).
Coordinates atomic payload assembly and routes data via ConfigFactory and VaultManager.
"""

import shutil
from pathlib import Path
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTabWidget, QFileDialog)
from PySide6.QtCore import Qt, QDir

# Importación de sub-pestañas modulares moleculares
from ui.settings_tabs.tab_identity import TabIdentity
from ui.settings_tabs.tab_vault import TabVault
from ui.settings_tabs.tab_vcs import TabVCS
from ui.settings_tabs.tab_topography import TabTopography
from ui.settings_tabs.tab_software import TabSoftware

# Importación del gestor de servicios del dominio
from core.vault_manager import VaultManager


class SettingsWidget(QFrame):
    def __init__(self, parent, config_factory, auth_manager, status_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.config_factory = config_factory
        self.auth_manager = auth_manager
        self.status_callback = status_callback
        
        # Canal unificado de servicios para el inventario de software
        self.vault_manager = VaultManager(self.config_factory)
        
        self.setObjectName("SettingsWidgetBase")
        self.setStyleSheet("background: transparent;")
        
        self._build_ui()
        self._conectar_senales_cambio()
        self._cargar_datos_actuales()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # HEADER CON ALERTA VISUAL INTEGRADA
        header_layout = QHBoxLayout()
        lbl_title = QLabel(self.tr("Global Studio Settings"))
        lbl_title.setObjectName("H2Title")
        header_layout.addWidget(lbl_title)
        
        self.lbl_unsaved_warning = QLabel("")
        header_layout.addWidget(self.lbl_unsaved_warning)
        
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # TAB SYSTEM
        self.tabs = QTabWidget()
        self.tabs.setObjectName("SettingsTabs")
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #334155; border-radius: 8px; background: #1E293B; }
            QTabBar::tab { background: #0F172A; color: #94A3B8; padding: 10px 20px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px; }
            QTabBar::tab:selected { background: #1E293B; color: #F8FAFC; font-weight: bold; border: 1px solid #334155; border-bottom: none; }
        """)

        # Instanciación de Sub-Vistas Moleculares (Asignación limpia de responsabilidades)
        self.tab_identidad = TabIdentity(self.auth_manager, self.status_callback, parent=self.tabs)
        self.tab_boveda = TabVault(parent=self.tabs)
        self.tab_vcs = TabVCS(parent=self.tabs)
        self.tab_topo = TabTopography(parent=self.tabs)
        
        # CORRECCIÓN DE INYECCIÓN DE DEPENDENCIAS
        self.tab_software = TabSoftware(
            parent=self.tabs,
            vault_manager=self.vault_manager,
            status_callback=self.status_callback
        )

        # Enlace de pestañas al Tab Container
        self.tabs.addTab(self.tab_identidad, self.tr("Identity & API"))
        self.tabs.addTab(self.tab_boveda, self.tr("Vault Storage"))
        self.tabs.addTab(self.tab_vcs, self.tr("Pipeline & VCS"))
        self.tabs.addTab(self.tab_topo, self.tr("Project Topography"))
        self.tabs.addTab(self.tab_software, self.tr("Software & Manifest"))

        main_layout.addWidget(self.tabs, stretch=1)

        # FOOTER / MASTER ACTIONS
        footer_layout = QHBoxLayout()
        
        self.btn_guardar = QPushButton(self.tr("Save Local Changes"))
        self.btn_guardar.setObjectName("SecondaryButton")
        self.btn_guardar.setFixedSize(180, 40)
        self.btn_guardar.setCursor(Qt.PointingHandCursor)
        self.btn_guardar.clicked.connect(self._guardar_configuracion)
        footer_layout.addWidget(self.btn_guardar)

        footer_layout.addStretch()

        self.btn_exportar_semilla = QPushButton(self.tr("Export Studio Seed (.seed)"))
        self.btn_exportar_semilla.setStyleSheet("background-color: #4F46E5; color: white; font-weight: bold; border-radius: 6px; font-size: 13px; border: none;")
        self.btn_exportar_semilla.setFixedSize(240, 40)
        self.btn_exportar_semilla.setCursor(Qt.PointingHandCursor)
        self.btn_exportar_semilla.clicked.connect(self._exportar_semilla_estudio)
        footer_layout.addWidget(self.btn_exportar_semilla)

        main_layout.addLayout(footer_layout)

    def _conectar_senales_cambio(self):
        """Mapea las señales reactivas de las pestañas hijas hacia la alerta visual del Orquestador."""
        self.tab_identidad.modified.connect(self._on_field_modified)
        self.tab_boveda.modified.connect(self._on_field_modified)
        self.tab_vcs.modified.connect(self._on_field_modified)
        self.tab_topo.modified.connect(self._on_field_modified)
        self.tab_software.modified.connect(self._on_field_modified)

    def _on_field_modified(self):
        self.lbl_unsaved_warning.setText(self.tr("● Unsaved Changes"))
        self.lbl_unsaved_warning.setStyleSheet("color: #F59E0B; font-weight: bold; font-size: 13px; margin-left: 15px;")

    # ---------------------------------------------------------
    # ORCHESTRATION LOGIC (Data-Down, Actions-Up)
    # ---------------------------------------------------------

    def _cargar_datos_actuales(self):
        """Pide datos a los Singletons de Dominio y los distribuye hacia abajo (Data-Down)."""
        raw = self.config_factory.get_raw_config()
        vcs = raw.get("vcs_engine", {})
        topo = raw.get("project_topography", {})
        
        # 1. Hidratar Identidad y API
        self.tab_identidad.cargar_datos(raw)
        
        # 2. Hidratar Almacenamiento y Rutas
        projects_path = vcs.get("local_workspace_root", {}).get(self.config_factory._get_current_os(), "")
        if not projects_path:
            projects_path = str(self.config_factory.get_workspace_root())
            
        vault_path = str(self.config_factory.get_vault_path())
        self.tab_boveda.cargar_datos(projects_path, vault_path)

        # 3. Hidratar Control de Versiones (VCS) con Credenciales Override
        active_adapter = vcs.get("active_adapter", "svn")
        repo_url = vcs.get("repository_url", "")
        enable_sparse = vcs.get("enable_vendor_sparse_checkout", True)
        vcs_user = vcs.get("vcs_username", "")
        vcs_pwd = vcs.get("vcs_password", "")
        
        self.tab_vcs.cargar_datos(active_adapter, repo_url, enable_sparse, vcs_user, vcs_pwd)

        # 4. Hidratar Topografía Semántica
        self.tab_topo.cargar_datos(topo)
        
        # 5. Hidratar Catálogo de Software Compartido
        manifest_data = self.vault_manager.cargar_inventario()
        self.tab_software.cargar_datos(manifest_data)
        
        self.lbl_unsaved_warning.setText("")

    def _recopilar_payload(self) -> dict:
        """Solicita a cada subcomponente su diccionario y empaqueta un JSON unificado."""
        payload = {}
        
        # Fusionar diccionarios de las sub-vistas
        payload.update(self.tab_identidad.get_identity_payload())
        payload.update(self.tab_vcs.get_vcs_payload())
        payload.update(self.tab_topo.get_topography_payload())
        
        # Procesar almacenamiento e inyectar mapeo Multi-OS compatible
        vault_data = self.tab_boveda.get_vault_payload()
        projects_dir = vault_data.get("vcs_engine", {}).get("local_workspace_root", "")
        
        payload["infrastructure_topology"] = vault_data.get("infrastructure_topology", {})
        payload["vcs_engine"].update({
            "local_workspace_root": {
                "windows": projects_dir,
                "linux": projects_dir,
                "macos": projects_dir
            }
        })
        
        return payload

    def _guardar_configuracion(self):
        # 1. Aplicar Hero Image si existe una ruta pendiente en el componente de identidad
        if self.tab_identidad.pending_hero_image_path and self.tab_identidad.pending_hero_image_path.exists():
            try:
                dest_path = Path("assets/login_hero.png")
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.tab_identidad.pending_hero_image_path, dest_path)
                self.tab_identidad.entry_hero_image.clear()
                self.tab_identidad.pending_hero_image_path = None
            except Exception as e:
                self.status_callback(self.tr("⚠️ Settings saved, but failed to apply Hero Image: {0}").format(e), "yellow")

        # 2. Persistir payload de configuración local (settings.json)
        payload = self._recopilar_payload()
        exito_config = self.config_factory.guardar_configuracion(payload)
        
        # 3. Persistir payload del manifiesto del software compartido en el NAS (vault_manifest.json)
        software_payload = self.tab_software.get_software_payload()
        exito_vault = self.vault_manager.guardar_inventario(software_payload)
        
        if exito_config and exito_vault:
            self.lbl_unsaved_warning.setText("")
            self.status_callback(self.tr("✓ Local settings and Network Manifest saved successfully."), "green")
            self._cargar_datos_actuales()
        else:
            if not exito_config:
                self.status_callback(self.tr("✗ Critical error writing settings.json to local disk."), "red")
            if not exito_vault:
                self.status_callback(self.tr("✗ Network write error: Could not publish vault_manifest.json to the NAS."), "red")

    def _exportar_semilla_estudio(self):
        payload = self._recopilar_payload()
        dest_dir = QFileDialog.getExistingDirectory(self, self.tr("Select Destination Directory for Seed File"), QDir.homePath())
        
        if dest_dir:
            self.status_callback(self.tr("Encrypting and exporting Studio Seed..."), "yellow")
            exito, mensaje = self.config_factory.exportar_semilla(payload, Path(dest_dir))
            
            if exito:
                self.status_callback(self.tr("✓ Seed exported successfully: {0}").format(mensaje), "green")
            else:
                self.status_callback(self.tr("✗ Export failed: {0}").format(mensaje), "red")

```

--------------------------------------------------------------------------------

### Archivo: `ui/widget_software.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_software.py
# Rol Arquitectónico: UI Component / Software Provisioning & Manifest Wizard
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.2.0
# =========================================================================================

"""
Software Provisioning Tab for the Global Settings.
Integrates the asynchronous Blender index web scraper and the Vault Manifest Wizard.
Connects with AddonParser to natively inspect and validate add-on compatibility.
Features the Blender Studio Tools Auto-Fetcher, which downloads, repackages, 
and bulk-registers upstream studio dependencies on the fly.
"""

import re
import requests
# import zipfile
# import tempfile
# import shutil
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QScrollArea, QFrame, QLineEdit, 
                               QFileDialog, QCheckBox, QProgressBar, QComboBox,
                               QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal

from core.file_downloader import FileDownloaderWorker
from core.manifest_manager import ManifestManager
from core.addon_parser import AddonParser

# from core.git_packager import StudioToolsPackagerWorker

# Importa el nuevo Worker encapsulado
from core.provisioning_workers import StudioToolsFetchWorker

MACUARE_LTS_VERSIONS = ("2.83", "2.93", "3.3", "3.6", "4.2", "4.5", "5.2")

class BlenderBaseScraper(QThread):
    data_ready = Signal(list)
    error_occurred = Signal(str)

    def run(self):
        url = "https://download.blender.org/release/"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            matches = re.findall(r'href="Blender([0-9a-zA-Z.-]+)/"', response.text)
            versiones = sorted(list(set(matches)), reverse=True)
            self.data_ready.emit(versiones)
        except Exception as e:
            self.error_occurred.emit(f"Base connection failed: {str(e)}")

class SubversionScraper(QThread):
    data_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, base_version: str):
        super().__init__()
        self.base_version = base_version

    def run(self):
        url = f"https://download.blender.org/release/Blender{self.base_version}/"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            archivos = re.findall(r'href="([^"]+\.(?:zip|tar\.xz|dmg|tar\.bz2))"', response.text)
            sub_versions = {}
            
            for f in archivos:
                fl = f.lower()
                if "linux" in fl: os_type = "linux"
                elif "win" in fl: os_type = "windows"
                elif "mac" in fl or "darwin" in fl: os_type = "macos"
                else: continue
                
                v_match = re.search(r'blender-([0-9]+\.[0-9]+\.[0-9a-zA-Z.-]+)-', fl)
                if not v_match: continue
                    
                v_num = v_match.group(1)
                if v_num not in sub_versions:
                    sub_versions[v_num] = {}
                sub_versions[v_num][os_type] = url + f
                
            self.data_ready.emit(sub_versions)
        except Exception as e:
            self.error_occurred.emit(f"Sub-version parsing failed: {str(e)}")

class SoftwareProvisioningWidget(QWidget):
    def __init__(self, parent, config_factory, status_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.config_factory = config_factory
        self.status_callback = status_callback
        
        vault_root = self.config_factory.get_workspace_root() / "openstudio_vault"
        self.manifest_manager = ManifestManager(vault_root)
        self.boveda_blender = self.manifest_manager.software_dir / "blender_versions"
        
        self.download_queue = []
        self.current_downloader = None
        self.studio_downloader = None
        
        self.setObjectName("SoftwareProvisioningWidgetBase")
        self._build_ui()
        self._refresh_manifest_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        split_layout = QHBoxLayout()
        split_layout.setSpacing(20)

        # --- LEFT PANEL: Blender Scraper ---
        scraper_frame = QFrame(self)
        scraper_frame.setObjectName("FloatingCard")
        scraper_frame.setStyleSheet("QFrame#FloatingCard { border: 1px solid #334155; border-radius: 8px; background: #0F172A; }")
        scraper_layout = QVBoxLayout(scraper_frame)
        
        remote_header = QHBoxLayout()
        lbl_remote = QLabel(self.tr("Remote Index (Blender.org)"))
        lbl_remote.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: bold;")
        remote_header.addWidget(lbl_remote)
        remote_header.addStretch()
        
        self.btn_fetch = QPushButton(self.tr("Sync Index"))
        self.btn_fetch.setObjectName("SecondaryButton")
        self.btn_fetch.setFixedSize(100, 28)
        self.btn_fetch.clicked.connect(self._obtener_versiones_base)
        remote_header.addWidget(self.btn_fetch)
        scraper_layout.addLayout(remote_header)

        os_layout = QHBoxLayout()
        lbl_os = QLabel(self.tr("Target OS:"))
        lbl_os.setStyleSheet("color: #64748B; font-weight: bold; font-size: 12px;")
        os_layout.addWidget(lbl_os)
        
        self.chk_win = QCheckBox("Win")
        self.chk_win.setChecked(True)
        self.chk_lin = QCheckBox("Lin")
        self.chk_mac = QCheckBox("Mac")
        
        for chk in [self.chk_win, self.chk_lin, self.chk_mac]:
            chk.setStyleSheet("color: #94A3B8; font-size: 12px; margin-left: 5px;")
            os_layout.addWidget(chk)
        os_layout.addStretch()
        scraper_layout.addLayout(os_layout)

        self.remote_scroll = QScrollArea()
        self.remote_scroll.setWidgetResizable(True)
        self.remote_scroll.setStyleSheet("border: none; background: transparent; margin-top: 10px;")
        
        self.remote_widget = QWidget()
        self.remote_list_layout = QVBoxLayout(self.remote_widget)
        self.remote_list_layout.setAlignment(Qt.AlignTop)
        self.remote_scroll.setWidget(self.remote_widget)
        
        scraper_layout.addWidget(self.remote_scroll)
        split_layout.addWidget(scraper_frame, stretch=1)

        # --- RIGHT PANEL: Manifest Wizard ---
        wizard_frame = QFrame(self)
        wizard_frame.setObjectName("FloatingCard")
        wizard_frame.setStyleSheet("QFrame#FloatingCard { border: 1px solid #334155; border-radius: 8px; background: #0F172A; }")
        wizard_layout = QVBoxLayout(wizard_frame)

        lbl_wizard = QLabel(self.tr("Vault Manifest Wizard"))
        lbl_wizard.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: bold;")
        wizard_layout.addWidget(lbl_wizard)
        
        lbl_desc = QLabel(self.tr("Map required add-ons to local Blender binaries."))
        lbl_desc.setStyleSheet("color: #64748B; font-size: 11px; margin-bottom: 10px;")
        wizard_layout.addWidget(lbl_desc)

        # Version Selector
        select_layout = QHBoxLayout()
        lbl_sel = QLabel(self.tr("Blender Version:"))
        lbl_sel.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 12px;")
        select_layout.addWidget(lbl_sel)
        
        self.combo_versions = QComboBox()
        self.combo_versions.setFixedHeight(30)
        self.combo_versions.setStyleSheet("background-color: #1E293B; border: 1px solid #475569; color: white; border-radius: 4px;")
        self.combo_versions.currentIndexChanged.connect(self._render_mapped_addons)
        select_layout.addWidget(self.combo_versions, stretch=1)
        
        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setFixedSize(30, 30)
        self.btn_refresh.setStyleSheet("background-color: #334155; color: white; border-radius: 4px;")
        self.btn_refresh.clicked.connect(self._refresh_manifest_ui)
        select_layout.addWidget(self.btn_refresh)
        wizard_layout.addLayout(select_layout)

        # Add-on List
        self.addons_scroll = QScrollArea()
        self.addons_scroll.setWidgetResizable(True)
        self.addons_scroll.setStyleSheet("border: 1px solid #1E293B; border-radius: 4px; background: #0F172A; margin-top: 10px;")
        
        self.addons_widget = QWidget()
        self.addons_layout = QVBoxLayout(self.addons_widget)
        self.addons_layout.setAlignment(Qt.AlignTop)
        self.addons_scroll.setWidget(self.addons_widget)
        wizard_layout.addWidget(self.addons_scroll, stretch=1)

        # Registration Forms
        form_layout = QHBoxLayout()
        self.btn_register_addon = QPushButton(self.tr("+ Link New (.zip)"))
        self.btn_register_addon.setObjectName("PrimaryButton")
        self.btn_register_addon.setFixedHeight(35)
        self.btn_register_addon.setCursor(Qt.PointingHandCursor)
        self.btn_register_addon.clicked.connect(self._trigger_addon_registration)
        form_layout.addWidget(self.btn_register_addon)
        
        self.btn_fetch_studio = QPushButton(self.tr("🌐 Auto-Fetch Studio Tools"))
        self.btn_fetch_studio.setObjectName("SecondaryButton")
        self.btn_fetch_studio.setFixedHeight(35)
        self.btn_fetch_studio.setCursor(Qt.PointingHandCursor)
        self.btn_fetch_studio.clicked.connect(self._trigger_studio_tools_fetch)
        form_layout.addWidget(self.btn_fetch_studio)

        wizard_layout.addLayout(form_layout)
        split_layout.addWidget(wizard_frame, stretch=1)
        main_layout.addLayout(split_layout, stretch=1)

        # PROGRESS BAR
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: none; background-color: #1E293B; border-radius: 3px; }
            QProgressBar::chunk { background-color: #10B981; border-radius: 3px; }
        """)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

    def _limpiar_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

    # --- SCRAPER LOGIC ---

    def _obtener_versiones_base(self):
        self._limpiar_layout(self.remote_list_layout)
        self.btn_fetch.setEnabled(False)
        self.scraper_base = BlenderBaseScraper()
        self.scraper_base.data_ready.connect(self._renderizar_versiones_base)
        self.scraper_base.start()

    def _renderizar_versiones_base(self, versiones: list):
        self._limpiar_layout(self.remote_list_layout)
        self.btn_fetch.setEnabled(True)
        for v in versiones:
            row = QHBoxLayout()
            lbl = QLabel(f"Blender {v}")
            lbl.setStyleSheet("color: #F8FAFC; font-weight: bold; font-size: 13px;")
            row.addWidget(lbl)
            
            if v in MACUARE_LTS_VERSIONS:
                lts = QLabel("LTS")
                lts.setStyleSheet("background-color: #3B82F6; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: bold;")
                row.addWidget(lts)
            
            row.addStretch()
            btn = QPushButton(self.tr("Inspect"))
            btn.setObjectName("SecondaryButton")
            btn.setFixedSize(70, 24)
            btn.clicked.connect(lambda _, version=v: self._obtener_subversiones(version))
            row.addWidget(btn)
            
            self.remote_list_layout.addWidget(self._wrap_in_frame(row))

    def _obtener_subversiones(self, base_version: str):
        self._limpiar_layout(self.remote_list_layout)
        lbl_loading = QLabel(self.tr("Scanning packages for v{0}...").format(base_version))
        lbl_loading.setStyleSheet("color: #F59E0B; font-style: italic;")
        self.remote_list_layout.addWidget(lbl_loading)
        
        self.scraper_sub = SubversionScraper(base_version)
        self.scraper_sub.data_ready.connect(lambda data: self._renderizar_subversiones(base_version, data))
        self.scraper_sub.start()

    def _renderizar_subversiones(self, base_version: str, data: dict):
        self._limpiar_layout(self.remote_list_layout)
        btn_back = QPushButton(self.tr("← Back to Index"))
        btn_back.setObjectName("LinkButton")
        btn_back.clicked.connect(self._obtener_versiones_base)
        self.remote_list_layout.addWidget(btn_back, alignment=Qt.AlignLeft)
        
        for sub_v in sorted(data.keys(), reverse=True):
            row = QHBoxLayout()
            lbl = QLabel(f"v{sub_v}")
            lbl.setStyleSheet("color: #F8FAFC; font-weight: bold; font-size: 12px;")
            row.addWidget(lbl)
            
            os_map = data[sub_v]
            os_visuals = []
            for os_type, url in os_map.items():
                file_name = url.split('/')[-1]
                if (self.boveda_blender / file_name).exists():
                    os_visuals.append(f"<span style='color: #10B981;'>{os_type} ✓</span>")
                else:
                    os_visuals.append(f"<span style='color: #64748B;'>{os_type}</span>")
                    
            lbl_av = QLabel(f"[{' | '.join(os_visuals)}]")
            lbl_av.setTextFormat(Qt.RichText)
            row.addWidget(lbl_av)
            row.addStretch()
            
            btn = QPushButton(self.tr("↓ Queue"))
            btn.setStyleSheet("background-color: #4F46E5; color: white; border-radius: 4px; font-size: 11px; padding: 4px 8px;")
            btn.clicked.connect(lambda _, v=sub_v, om=os_map: self._procesar_descarga(om))
            row.addWidget(btn)
            
            self.remote_list_layout.addWidget(self._wrap_in_frame(row))

    def _wrap_in_frame(self, layout):
        frame = QFrame()
        frame.setStyleSheet("background-color: #1E293B; border-radius: 6px; padding: 2px;")
        frame.setLayout(layout)
        return frame

    def _procesar_descarga(self, os_map: dict):
        urls = []
        if self.chk_win.isChecked() and "windows" in os_map: urls.append(os_map["windows"])
        if self.chk_lin.isChecked() and "linux" in os_map: urls.append(os_map["linux"])
        if self.chk_mac.isChecked() and "macos" in os_map: urls.append(os_map["macos"])
        
        if not urls:
            self.status_callback(self.tr("Warning: No packages for selected OS."), "yellow")
            return
            
        encolados, omitidos = 0, 0
        self.boveda_blender.mkdir(parents=True, exist_ok=True)
        
        for url in urls:
            dest = self.boveda_blender / url.split('/')[-1]
            if dest.exists(): omitidos += 1
            else:
                self.download_queue.append((url, dest))
                encolados += 1
                
        if encolados > 0:
            self.status_callback(self.tr("Queued {0} packages.").format(encolados), "green")
            self._procesar_siguiente_descarga()
        elif omitidos > 0:
            self.status_callback(self.tr("Skipped. Binaries already exist in Vault."), "green")

    def _procesar_siguiente_descarga(self):
        if self.current_downloader and self.current_downloader.isRunning(): return
            
        if not self.download_queue:
            self.progress_bar.hide()
            self._refresh_manifest_ui()
            self.status_callback(self.tr("All downloads completed."), "green")
            return
            
        url, dest = self.download_queue.pop(0)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        
        self.current_downloader = FileDownloaderWorker(url, dest)
        self.current_downloader.progress_updated.connect(self.progress_bar.setValue)
        self.current_downloader.status_update.connect(self.status_callback)
        self.current_downloader.download_completed.connect(self._descarga_finalizada)
        self.current_downloader.error_occurred.connect(self._descarga_fallida)
        self.current_downloader.start()

    def _descarga_finalizada(self, path: Path):
        self.current_downloader.deleteLater()
        self.current_downloader = None
        self._procesar_siguiente_descarga()

    def _descarga_fallida(self, error: str):
        self.status_callback(self.tr("Download failed: {0}").format(error), "red")
        self.current_downloader.deleteLater()
        self.current_downloader = None
        self._procesar_siguiente_descarga()

    # --- MANIFEST WIZARD LOGIC ---

    def _refresh_manifest_ui(self):
        self.combo_versions.blockSignals(True)
        self.combo_versions.clear()
        
        versions = self.manifest_manager.scan_local_blender_binaries()
        if versions:
            self.combo_versions.addItems(versions)
            self.btn_register_addon.setEnabled(True)
            self.btn_fetch_studio.setEnabled(True)
        else:
            self.combo_versions.addItem(self.tr("-- No Binaries Found --"))
            self.btn_register_addon.setEnabled(False)
            self.btn_fetch_studio.setEnabled(False)
            
        self.combo_versions.blockSignals(False)
        self._render_mapped_addons()

    def _render_mapped_addons(self):
        self._limpiar_layout(self.addons_layout)
        current_version = self.combo_versions.currentText()
        
        if not current_version or current_version.startswith("--"):
            return
            
        addons = self.manifest_manager.get_addons_for_version(current_version)
        if not addons:
            lbl = QLabel(self.tr("No add-ons registered for this version."))
            lbl.setStyleSheet("color: #64748B; font-style: italic;")
            self.addons_layout.addWidget(lbl)
            return
            
        for addon in addons:
            row = QHBoxLayout()
            lbl_n = QLabel(f"📦 {addon.get('name', 'Unknown')}")
            lbl_n.setStyleSheet("color: #10B981; font-weight: bold; font-size: 13px;")
            row.addWidget(lbl_n)
            
            lbl_v = QLabel(f"v{addon.get('version', '?.?')}")
            lbl_v.setStyleSheet("color: #94A3B8; font-size: 11px;")
            row.addWidget(lbl_v)
            row.addStretch()
            
            self.addons_layout.addWidget(self._wrap_in_frame(row))

    def _trigger_addon_registration(self):
        current_version = self.combo_versions.currentText()
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select Add-on Package"), "", self.tr("Zip Archives (*.zip)")
        )
        if not file_path: return
            
        zip_path = Path(file_path)
        self.status_callback(self.tr("Inspecting add-on metadata..."), "yellow")
        parsed_data = AddonParser.parse_zip(zip_path)
        
        if not parsed_data["is_valid"]:
            reply = QMessageBox.warning(
                self, 
                self.tr("Invalid or Missing Metadata"),
                self.tr("Could not find a valid blender_manifest.toml or bl_info in __init__.py.\n\nDo you want to force installation anyway?"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                self.status_callback(self.tr("Add-on registration cancelled."), "gray")
                return

        addon_name = parsed_data["name"]
        addon_version = parsed_data["version"]
        min_blender = parsed_data["min_blender_version"]

        if not AddonParser.is_compatible(min_blender, current_version):
            reply = QMessageBox.warning(
                self,
                self.tr("Compatibility Warning"),
                self.tr(f"This add-on requires Blender {min_blender} or higher.\nYou are linking it to Blender {current_version}.\n\nProceed at your own risk. Force link?"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                self.status_callback(self.tr("Add-on registration cancelled."), "gray")
                return

        exito, msg = self.manifest_manager.register_addon(
            blender_version=current_version,
            addon_name=addon_name,
            addon_version=addon_version,
            source_zip=zip_path
        )
        
        if exito:
            self.status_callback(self.tr("✓ Add-on successfully linked: {0} v{1}").format(addon_name, addon_version), "green")
            self._render_mapped_addons()
        else:
            self.status_callback(self.tr("✗ Registration failed: {0}").format(msg), "red")

    def _trigger_studio_tools_fetch(self):
        current_version = self.combo_versions.currentText()
        if not current_version or current_version.startswith("--"):
            self.status_callback(self.tr("Select a valid Blender version first."), "yellow")
            return
            
        self.btn_fetch_studio.setEnabled(False)
        self.btn_register_addon.setEnabled(False)
        
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        
        # Obtenemos la ruta absoluta de la bóveda de forma directa
        vault_root = self.config_factory.get_workspace_root() / "openstudio_vault"
        
        # Le entregamos al Worker puramente la ruta física
        self.studio_fetch_worker = StudioToolsFetchWorker(vault_root, current_version)
        self.studio_fetch_worker.progress_updated.connect(self.progress_bar.setValue)
        self.studio_fetch_worker.status_update.connect(self.status_callback)
        self.studio_fetch_worker.finished_packing.connect(self._on_studio_tools_packaged)
        self.studio_fetch_worker.error_occurred.connect(self._on_studio_tools_error)
        self.studio_fetch_worker.start()

    def _on_studio_tools_packaged(self):
        if hasattr(self, 'studio_fetch_worker') and self.studio_fetch_worker:
            self.studio_fetch_worker.deleteLater()
            self.studio_fetch_worker = None
        
        self.btn_fetch_studio.setEnabled(True)
        self.btn_register_addon.setEnabled(True)
        self.progress_bar.hide()
        self._refresh_manifest_ui()

    def _on_studio_tools_error(self, error: str):
        if hasattr(self, 'studio_fetch_worker') and self.studio_fetch_worker: 
            self.studio_fetch_worker.deleteLater()
            self.studio_fetch_worker = None
        
        self.btn_fetch_studio.setEnabled(True)
        self.btn_register_addon.setEnabled(True)
        self.progress_bar.hide()
        self.status_callback(self.tr("Studio Tools Fetch Failed: {0}").format(error), "red")

```

--------------------------------------------------------------------------------

### Archivo: `ui/widget_task_list.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_task_list.py
# Rol Arquitectónico: UI Component / JIT Interceptor / Artist Dashboard (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 1.1.0
# =========================================================================================

"""
Task Grid Component (Task List).
Refactored to apply Separation of Concerns (SoC) and native i18n.
Emits the project tree to the main view for lateral routing.
Adapted to the new VFS topology (local, shared, svn).
"""

import json
import time
from pathlib import Path

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QScrollArea, QWidget)
from PySide6.QtCore import Qt, QThread, Signal, QTimer

from core.env_launcher import lanzar_blender
from core.local_installer import LocalInstaller
from core.vcs_router import VCSRouter
from core.path_resolver import PathResolver

from ui.window_svn_login import SVNLoginWindow
from ui.components.task_card import TaskCard


class DataWorker(QThread):
    data_ready = Signal(list, dict, dict)
    status_update = Signal(str, str)

    def __init__(self, auth_manager, nextcloud_dir, config_factory):
        super().__init__()
        self.auth_manager = auth_manager
        self.nextcloud_dir = nextcloud_dir
        self.config_factory = config_factory

    def run(self):
        kitsu_projects_map = self.auth_manager.obtener_proyectos_activos()
        tasks = self.auth_manager.get_assigned_tasks()
        
        local_projects_map = {}
        prod_folder = self.config_factory.get_production_folder_name()

        if self.nextcloud_dir.exists():
            for carpeta in self.nextcloud_dir.iterdir():
                if carpeta.is_dir():
                    # Nueva ruta B2B alineada con Blender Studio Tools
                    init_path = carpeta / prod_folder / "pipeline" / "project_init.json"
                    if init_path.exists():
                        try:
                            with open(init_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            nombre = data.get("project_name", carpeta.name).lower()
                            
                            if nombre in kitsu_projects_map:
                                local_projects_map[nombre] = carpeta
                        except Exception:
                            pass
                            
        self.data_ready.emit(tasks, local_projects_map, kitsu_projects_map)


class InstallWorker(QThread):
    status_update = Signal(str, str)
    finished_install = Signal(bool)

    def __init__(self, installer, project_root, svn_user, svn_pwd, user_role, task_metadata):
        super().__init__()
        self.installer = installer
        self.project_root = project_root
        self.svn_user = svn_user
        self.svn_pwd = svn_pwd
        self.user_role = user_role
        self.task_metadata = task_metadata

    def run(self):
        def safe_callback(msg, color="white"):
            self.status_update.emit(msg, color)

        exito, mensaje = self.installer.instalar_entorno(
            self.project_root, self.svn_user, self.svn_pwd, safe_callback,
            user_role=self.user_role, task_metadata=self.task_metadata
        )
        
        color_msg = "green" if exito else "red"
        self.status_update.emit(mensaje, color_msg)
        self.finished_install.emit(exito)


class LaunchWorker(QThread):
    status_update = Signal(str, str)
    process_finished = Signal()

    def __init__(self, project_root, config_path, svn_user, svn_pwd, kitsu_user, kitsu_pwd, 
                 kitsu_host, user_role, task_data, target_file, prod_folder, config_factory, auth_manager):
        super().__init__()
        self.project_root = project_root
        self.config_path = config_path
        self.svn_user = svn_user
        self.svn_pwd = svn_pwd
        self.kitsu_user = kitsu_user
        self.kitsu_pwd = kitsu_pwd
        self.kitsu_host = kitsu_host
        self.user_role = user_role
        self.task_data = task_data
        self.target_file = target_file
        self.prod_folder = prod_folder
        self.config_factory = config_factory
        self.auth_manager = auth_manager

    def run(self):
        def safe_callback(msg, color="white"):
            self.status_update.emit(msg, color)

        print(f"\n[LaunchWorker DEBUG] Orchestrating process for target_file: {self.target_file}")

        task_type = self.task_data.get("task_type_name", "unknown")
        adapter = None
        ruta_bloqueo = "edit/master_edit.blend"
        
        try:
            vcs_type = self.config_factory.get_vcs_adapter_type()
            base_url = self.config_factory.get_vcs_repository_url()
            repo_url = f"{base_url}/{self.project_root.name}/{self.prod_folder}"
            workspace = self.project_root / self.prod_folder
            
            router = VCSRouter(vcs_type=vcs_type, repo_url=repo_url, workspace_dir=workspace)
            adapter = router.get_adapter()
            adapter.cleanup()
        except Exception as e:
            print(f"[CLEANUP WARNING] Could not execute automatic workspace cleanup: {e}")

        requiere_bloqueo = task_type.lower() in ["edit", "editorial", "montaje"]
        cargo_usuario = self.auth_manager.get_user_position()
        
        cargos_autorizados = ["editor", "director", "lead"]
        roles_autorizados = ["td", "supervisor", "lead", "manager"]
        esta_autorizado = (self.user_role in roles_autorizados) or (cargo_usuario in cargos_autorizados)
        
        if requiere_bloqueo:
            if esta_autorizado:
                try:
                    adapter.lock(path=ruta_bloqueo, username=self.svn_user, password=self.svn_pwd)
                except Exception as e:
                    err_msg = str(e).lower()
                    if not ("already locked" in err_msg or "was not found" in err_msg or "e155010" in err_msg or "unversioned" in err_msg):
                        safe_callback("Access Denied: The file is currently in use by another artist.", "red")
                        self.process_finished.emit()
                        return
        
        try:
            print(f"[LaunchWorker DEBUG] Executing lanzar_blender with file: {self.target_file}")
            lanzar_blender(
                self.project_root, self.config_path, self.svn_user, self.svn_pwd, 
                self.kitsu_user, self.kitsu_pwd, self.kitsu_host, self.user_role, 
                self.task_data, self.target_file, safe_callback, 
                production_folder=self.prod_folder
            )
        except Exception as e:
            safe_callback(f"Critical error launching Blender: {str(e)}", "red")

        if adapter and requiere_bloqueo and esta_autorizado:
            try:
                adapter.unlock(path=ruta_bloqueo, username=self.svn_user, password=self.svn_pwd)
            except Exception:
                pass
                    
        self.process_finished.emit()


class TaskListWidget(QFrame):
    
    projects_discovered = Signal(dict) 

    def __init__(self, parent, nextcloud_dir: Path, auth_manager, vault_manager, config_factory, status_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.nextcloud_dir = nextcloud_dir
        self.auth_manager = auth_manager
        self.vault = vault_manager
        self.config_factory = config_factory
        self.status_callback = status_callback
        self.installer = LocalInstaller(nextcloud_dir, config_factory)
        self.all_tasks = []
        self.local_projects_map = {}
        self.active_kitsu_projects = {}
        self.current_filter = "All"
        self._last_refresh_time = 0
        
        self.setObjectName("TaskListWidgetBase")
        self.setStyleSheet("background: transparent;")
        
        self._build_ui()
        self.cargar_proyectos()

    def _build_ui(self):
        content_layout = QVBoxLayout(self)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        self.header_frame = QFrame(self)
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        self.header_label = QLabel(self.tr("All Your Tasks"))
        self.header_label.setObjectName("H1Title")
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton(self.tr("↻ Refresh"))
        self.refresh_btn.setObjectName("SecondaryButton")
        self.refresh_btn.setFixedSize(100, 28)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._forzar_recarga)
        header_layout.addWidget(self.refresh_btn)
        content_layout.addWidget(self.header_frame)
        
        self.cards_scroll = QScrollArea(self)
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.cards_widget = QWidget()
        self.cards_widget.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setAlignment(Qt.AlignTop)
        
        self.cards_scroll.setWidget(self.cards_widget)
        content_layout.addWidget(self.cards_scroll, stretch=1)

    def aplicar_filtro(self, nombre_proyecto: str):
        self.current_filter = nombre_proyecto
        if nombre_proyecto == "All":
            self.header_label.setText(self.tr("All Your Tasks"))
        else:
            self.header_label.setText(self.tr("Tasks in: {0}").format(nombre_proyecto))
        self._render_tasks()

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _emit_status(self, msg: str, color: str = "white"):
        if self.status_callback:
            self.status_callback(msg, color)

    def _forzar_recarga(self):
        now = time.time()
        if now - self._last_refresh_time < 3:
            self._emit_status(self.tr("Please wait a few seconds before refreshing again..."), "yellow")
            return
        self._last_refresh_time = now
        self._emit_status(self.tr("Manual synchronization forced."), "white")
        self.cargar_proyectos()

    def cargar_proyectos(self):
        self._clear_layout(self.cards_layout)
        self.loading_label = QLabel(self.tr("Syncing tasks with database..."))
        self.loading_label.setStyleSheet("color: #94A3B8; font-style: italic;")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.cards_layout.addWidget(self.loading_label)
        
        self.worker_data = DataWorker(self.auth_manager, self.nextcloud_dir, self.config_factory)
        self.worker_data.data_ready.connect(self._almacenar_y_renderizar)
        self.worker_data.finished.connect(self.worker_data.deleteLater)
        self.worker_data.start()

    def _almacenar_y_renderizar(self, tasks: list, local_projects_map: dict, kitsu_projects_map: dict):
        if hasattr(self, 'loading_label'):
            self.loading_label.hide()
            self.loading_label.deleteLater()
            
        self.all_tasks = tasks
        self.local_projects_map = local_projects_map
        self.active_kitsu_projects = kitsu_projects_map
        
        project_counts = {}
        for t in self.all_tasks:
            p_name = t.get("project_name", "Unknown Project")
            project_counts[p_name] = project_counts.get(p_name, 0) + 1
            
        self.projects_discovered.emit(project_counts)

        active_projects = {t.get("project_name", "Unknown Project") for t in tasks}
        if self.current_filter != "All" and self.current_filter not in active_projects:
            self.current_filter = "All"
            self.header_label.setText(self.tr("All Your Tasks"))

        self._render_tasks()

    def _render_tasks(self):
        self._clear_layout(self.cards_layout)

        if not self.all_tasks:
            msg = QLabel(self.tr("You have no pending tasks (TODO/WIP). Great job!"))
            msg.setStyleSheet("color: #10B981; font-size: 14px;")
            msg.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(msg)
            return

        filtered_tasks = [t for t in self.all_tasks if self.current_filter == "All" or t.get("project_name") == self.current_filter]

        resolver = PathResolver()
        user_role = self.auth_manager.get_user_role()
        is_admin = user_role in ["lead", "supervisor", "td", "manager"]
        prod_folder = self.config_factory.get_production_folder_name()

        for task in filtered_tasks:
            proyecto_nombre = task["project_name"].lower()
            project_root = self.local_projects_map.get(proyecto_nombre)
            
            if proyecto_nombre in self.active_kitsu_projects:
                task["project_id"] = self.active_kitsu_projects[proyecto_nombre]
            
            esta_instalado = False
            can_work = True
            blocked_reason = ""

            if project_root:
                esta_instalado = self.installer.verificar_instalacion(project_root)
                if esta_instalado:
                    try:
                        relative_target = resolver.resolve(task)
                        if relative_target:
                            target_file = project_root / prod_folder / "pro" / relative_target
                            if not target_file.exists() and not is_admin:
                                can_work = False
                                blocked_reason = self.tr("File missing (Setup Required)")
                    except Exception as e:
                        print(f"[DEBUG _render_tasks] PathResolver Exception: {e}")
            else:
                can_work = False
                blocked_reason = self.tr("Project Desynced / Archived")
                
            tarjeta = TaskCard(
                parent=self.cards_widget,
                task_data=task,
                project_root=project_root,
                is_installed=esta_instalado,
                auth_manager=self.auth_manager,
                on_launch_callback=self.iniciar_proyecto_hilo,
                on_install_callback=self.ejecutar_instalacion_hilo,
                can_work=can_work,
                blocked_reason=blocked_reason
            )
            self.cards_layout.addWidget(tarjeta)

    def iniciar_proyecto_hilo(self, project_root: Path, config_path: Path, task_data: dict):
        if not self.vault.has_svn_credentials():
            self._emit_status(self.tr("Waiting for repository credentials..."), "yellow")
            self.modal_login = SVNLoginWindow(
                parent=self.window(),
                vault_manager=self.vault,
                on_success_callback=lambda: self.iniciar_proyecto_hilo(project_root, config_path, task_data)
            )
            self.modal_login.show()
            return

        user_role = self.auth_manager.get_user_role()
        prod_folder = self.config_factory.get_production_folder_name()
        target_file = None
        
        try:
            resolver = PathResolver()
            relative_target = resolver.resolve(task_data)
            
            if relative_target:
                target_file = project_root / prod_folder / "pro" / relative_target
                
                if user_role not in ["lead", "supervisor", "td", "manager"]:
                    if not target_file.exists():
                        self._emit_status(self.tr("❌ File not found. Please request Lead to create the shot."), "red")
                        return
        except Exception as e:
            self._emit_status(self.tr("Internal error resolving path: {0}").format(str(e)), "red")
            return

        svn_user, svn_pwd = self.vault.get_svn_credentials()
        kitsu_user, kitsu_pwd = self.vault.get_kitsu_credentials()
        kitsu_host = self.auth_manager.kitsu_host

        app_root = self.window()
        if hasattr(app_root, "registrar_instancia"):
            app_root.registrar_instancia(activa=True)

        self.worker_launch = LaunchWorker(
            project_root, config_path, svn_user, svn_pwd, kitsu_user, kitsu_pwd, kitsu_host, 
            user_role, task_data, target_file, prod_folder, self.config_factory, self.auth_manager
        )
        self.worker_launch.status_update.connect(self._emit_status)
        
        def on_launch_finished():
            if hasattr(app_root, "registrar_instancia"):
                app_root.registrar_instancia(activa=False)
            self.worker_launch.deleteLater()
            
        self.worker_launch.process_finished.connect(on_launch_finished)
        self.worker_launch.start()

    def ejecutar_instalacion_hilo(self, project_root: Path, task_data: dict):
        if not self.vault.has_svn_credentials():
            self._emit_status(self.tr("Waiting for repository credentials..."), "yellow")
            self.modal_login_install = SVNLoginWindow(
                parent=self.window(),
                vault_manager=self.vault,
                on_success_callback=lambda: self.ejecutar_instalacion_hilo(project_root, task_data)
            )
            self.modal_login_install.show()
            return
            
        user_role = self.auth_manager.get_user_role()
        svn_user, svn_pwd = self.vault.get_svn_credentials()
        
        task_metadata = None
        if user_role == "vendor":
            task_id = task_data.get("task_id")
            if task_id:
                task_metadata = self.auth_manager.get_task_metadata(task_id)
        
        self.worker_install = InstallWorker(
            self.installer, project_root, svn_user, svn_pwd, user_role, task_metadata
        )
        self.worker_install.status_update.connect(self._emit_status)
        
        def on_install_finished(exito):
            if exito:
                QTimer.singleShot(500, self.cargar_proyectos)
            else:
                self.vault.clear()
            self.worker_install.deleteLater()
            
        self.worker_install.finished_install.connect(on_install_finished)
        self.worker_install.start()

```

--------------------------------------------------------------------------------

### Archivo: `ui/window_new_project.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/window_new_project.py
# Rol Arquitectónico: UI View / Modal Dialog (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.9.0 (Ephemeral VCS Auth UI Injection)
# =========================================================================================

"""
Asistente modal para la creación de nuevos proyectos (TD Wizard).
Implementa validaciones estrictas de plantillas y campos de autenticación 
VCS efímeros en la UI para sobreescribir el SSO sin persistencia en disco.
"""

from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QComboBox, QCheckBox, QRadioButton, 
                               QButtonGroup, QPushButton, QScrollArea, QWidget, 
                               QFileDialog)
from PySide6.QtCore import Qt, QThread, Signal

from core.project_builder import ProjectBuilder
from core.vault_manager import VaultManager
from core.kitsu_manager import KitsuManager

class FetchKitsuTemplatesWorker(QThread):
    data_ready = Signal(list)
    def run(self):
        try:
            manager = KitsuManager()
            self.data_ready.emit(manager.get_all_templates())
        except Exception as e:
            print(f"[FetchKitsuTemplatesWorker] Error de red: {e}")
            self.data_ready.emit([])

class ProjectCreationWorker(QThread):
    """Hilo trabajador para ejecutar la I/O pesada del ProjectBuilder sin congelar la modal."""
    result = Signal(bool, str)

    def __init__(self, builder: ProjectBuilder, nombre: str, version: str, 
                 dependencias: dict, template: str, splash: str, vcs_user: str, vcs_pwd: str):
        super().__init__()
        self.builder = builder
        self.nombre = nombre
        self.version = version
        self.dependencias = dependencias
        self.template = template
        self.splash = splash
        self.vcs_user = vcs_user
        self.vcs_pwd = vcs_pwd

    def run(self):
        exito, mensaje = self.builder.create_project(
            project_name=self.nombre, 
            blender_version=self.version, 
            dependencies=self.dependencias, 
            project_template=self.template, 
            splash_image_path=self.splash,
            vcs_user=self.vcs_user,
            vcs_pwd=self.vcs_pwd
        )
        self.result.emit(exito, mensaje)

class NewProjectWindow(QDialog):
    def __init__(self, parent: QWidget, config_factory, on_success_callback):
        super().__init__(parent)
        self.setWindowTitle("Nuevo Proyecto")
        self.setFixedSize(500, 700) # Más compacta sin los campos de Auth
        self.setModal(True)
        self.ruta_splash = ""
        self.config_factory = config_factory
        self.on_success = on_success_callback
        self.builder = ProjectBuilder(self.config_factory)
        self.vault_manager = VaultManager(self.config_factory)
        self.vault_data = self.vault_manager.cargar_inventario()
        self.checkboxes_herramientas = {}
        self.template_group = None
        self.setObjectName("ViewLoginBase")
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(15)

        lbl_titulo = QLabel("Configuración Inicial")
        lbl_titulo.setObjectName("CardTitle")
        lbl_titulo.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(lbl_titulo)
        
        main_layout.addSpacing(10)

        self.entry_nombre = QLineEdit()
        self.entry_nombre.setObjectName("FormInput")
        self.entry_nombre.setPlaceholderText("Nombre (ej. p0004-nuevo-proyecto)")
        self.entry_nombre.setFixedHeight(45)
        main_layout.addWidget(self.entry_nombre)

        # Dropdown de Plantilla Kitsu
        lbl_kitsu_template = QLabel("Plantilla de Kitsu:")
        lbl_kitsu_template.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(lbl_kitsu_template)
        
        self.combo_kitsu_template = QComboBox()
        self.combo_kitsu_template.setFixedHeight(40)
        self.combo_kitsu_template.setStyleSheet("QComboBox { background-color: #0F172A; border: 1px solid #475569; border-radius: 8px; color: #F8FAFC; padding: 5px; }")
        self.combo_kitsu_template.addItem("Cargando plantillas...")
        self.combo_kitsu_template.setEnabled(False)
        main_layout.addWidget(self.combo_kitsu_template)
        
        self.worker_kitsu_templates = FetchKitsuTemplatesWorker()
        self.worker_kitsu_templates.data_ready.connect(self._on_kitsu_templates_loaded)
        self.worker_kitsu_templates.start()

        lbl_version = QLabel("Versión de Blender Objetivo:")
        lbl_version.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(lbl_version)
        
        versiones = list(self.vault_data.keys()) if self.vault_data else []
        self.combo_version = QComboBox()
        self.combo_version.addItems(versiones)
        self.combo_version.setFixedHeight(40)
        self.combo_version.setStyleSheet("QComboBox { background-color: #0F172A; border: 1px solid #475569; border-radius: 8px; color: #F8FAFC; padding: 5px; }")
        self.combo_version.currentTextChanged.connect(self.dibujar_dependencias_dinamicas)
        main_layout.addWidget(self.combo_version)

        lbl_addons = QLabel("Componentes de Bóveda (vault_manifest.json):")
        lbl_addons.setStyleSheet("font-weight: bold; margin-top: 15px;")
        main_layout.addWidget(lbl_addons)
        
        self.scroll_addons = QScrollArea()
        self.scroll_addons.setWidgetResizable(True)
        self.scroll_addons.setStyleSheet("QScrollArea { border: 1px solid #334155; border-radius: 8px; background-color: #1E293B; }")
        
        self.addons_widget = QWidget()
        self.addons_widget.setStyleSheet("background: transparent;")
        self.addons_layout = QVBoxLayout(self.addons_widget)
        self.addons_layout.setAlignment(Qt.AlignTop)
        self.scroll_addons.setWidget(self.addons_widget)
        main_layout.addWidget(self.scroll_addons, stretch=1)

        if versiones:
            self.dibujar_dependencias_dinamicas(self.combo_version.currentText())

        lbl_splash = QLabel("Splash Screen Personalizado (1000x500px):")
        lbl_splash.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(lbl_splash)

        splash_layout = QHBoxLayout()
        splash_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_splash = QPushButton("Buscar PNG")
        self.btn_splash.setObjectName("SecondaryButton")
        self.btn_splash.setFixedSize(120, 35)
        self.btn_splash.setCursor(Qt.PointingHandCursor)
        self.btn_splash.clicked.connect(self.seleccionar_splash)
        splash_layout.addWidget(self.btn_splash)

        self.lbl_splash_name = QLabel("Ninguna imagen")
        self.lbl_splash_name.setStyleSheet("color: #64748B; padding-left: 10px;")
        splash_layout.addWidget(self.lbl_splash_name, stretch=1)
        main_layout.addLayout(splash_layout)

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.hide()
        main_layout.addWidget(self.lbl_status)

        self.btn_crear = QPushButton("Generar Proyecto")
        self.btn_crear.setObjectName("PrimaryButton")
        self.btn_crear.setFixedHeight(50)
        self.btn_crear.setCursor(Qt.PointingHandCursor)
        self.btn_crear.clicked.connect(self.ejecutar_creacion)
        main_layout.addWidget(self.btn_crear)

        if not self.vault_data:
            self.lbl_status.setText("⚠️ OPERACIÓN BLOQUEADA: Bóveda no inicializada.")
            self.lbl_status.setStyleSheet("color: #EF4444; font-weight: bold; padding: 12px; background-color: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 6px;")
            self.lbl_status.show()
            self.entry_nombre.setEnabled(False)
            self.combo_version.setEnabled(False)
            self.btn_splash.setEnabled(False)
            self.btn_crear.setEnabled(False)

    def _on_kitsu_templates_loaded(self, templates: list):
        self.combo_kitsu_template.clear()
        if not templates:
            self.combo_kitsu_template.addItem("standard-3d-production")
        else:
            for t in templates:
                self.combo_kitsu_template.addItem(t["name"])
        self.combo_kitsu_template.setEnabled(True)

    def seleccionar_splash(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar Splash Screen", "", "Imágenes PNG (*.png)")
        if ruta:
            self.ruta_splash = ruta
            self.lbl_splash_name.setText(Path(ruta).name)
            self.lbl_splash_name.setStyleSheet("color: #F8FAFC; padding-left: 10px;")

    def _clear_addons_layout(self):
        while self.addons_layout.count():
            child = self.addons_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

    def dibujar_dependencias_dinamicas(self, version_seleccionada: str):
        self._clear_addons_layout()
        self.checkboxes_herramientas.clear()
        self.template_group = QButtonGroup(self)
        if not version_seleccionada: return

        categorias_disponibles = self.vault_data.get(version_seleccionada, {})
        if not categorias_disponibles: return

        for categoria, items in categorias_disponibles.items():
            lbl_cat = QLabel(f"[{categoria.upper()}]")
            lbl_cat.setStyleSheet("color: #10B981; font-weight: bold; margin-top: 10px;")
            self.addons_layout.addWidget(lbl_cat)
            self.checkboxes_herramientas[categoria] = {}

            for nombre_item, datos in items.items():
                version_item = datos.get("version", "1.0")
                es_obligatorio = datos.get("mandatory", False)
                texto_label = f"{nombre_item} v{version_item} - {datos.get('description', '')}"
                
                if categoria == "templates":
                    cb = QRadioButton(texto_label)
                    cb.setStyleSheet("QRadioButton { color: #F8FAFC; padding: 5px; }")
                    self.template_group.addButton(cb)
                else:
                    cb = QCheckBox(texto_label)
                    cb.setStyleSheet("QCheckBox { color: #F8FAFC; padding: 5px; }")
                
                cb.toggled.connect(lambda checked, c=categoria, n=nombre_item, r=datos.get("requires", []): self._resolver_subdependencias(checked, c, n, r))
                self.addons_layout.addWidget(cb)

                if es_obligatorio:
                    cb.setChecked(True)
                    cb.setEnabled(False)

                self.checkboxes_herramientas[categoria][nombre_item] = {'checkbox': cb, 'version': version_item}

    def _resolver_subdependencias(self, checked: bool, categoria_padre: str, nombre_padre: str, requires: list):
        for req in requires:
            partes = req.split("/")
            if len(partes) != 2: continue
            cat_req, nom_req = partes[0], partes[1]
            if cat_req in self.checkboxes_herramientas and nom_req in self.checkboxes_herramientas[cat_req]:
                cb_sub = self.checkboxes_herramientas[cat_req][nom_req]['checkbox']
                cb_sub.setChecked(checked)
                cb_sub.setEnabled(not checked)

    def ejecutar_creacion(self):
        nombre = self.entry_nombre.text().strip()
        version_blender = self.combo_version.currentText().strip()
        kitsu_template = self.combo_kitsu_template.currentText().strip()

        if not nombre or not nombre.replace("-", "").replace("_", "").isalnum():
            self.lbl_status.setText("Nombre inválido.")
            self.lbl_status.show()
            return

        dependencias_finales, template_principal = {}, None
        for categoria, items in self.checkboxes_herramientas.items():
            dependencias_finales[categoria] = {}
            for nombre_item, data in items.items():
                if data['checkbox'].isChecked():
                    dependencias_finales[categoria][nombre_item] = data['version']
                    if categoria == "templates": template_principal = nombre_item

        if not template_principal: template_principal = "Macuare_Estudio"

        # RESOLUCIÓN DESDE EL JSON (Sin interfaz gráfica que estorbe)
        vcs_config = self.config_factory.get_raw_config().get("vcs_engine", {})
        user_vcs = vcs_config.get("vcs_username", "admin")
        pwd_vcs = vcs_config.get("vcs_password", "admin123")

        self.btn_crear.setEnabled(False)
        self.btn_crear.setText("Creando...")
        self.lbl_status.setText("Forjando estructura y conectando repositorios...")
        self.lbl_status.setStyleSheet("color: #F59E0B; font-weight: bold;")
        self.lbl_status.show()

        # Inyectar plantilla seleccionada en el Builder (IMPORTANTE)
        self.builder.kitsu_active_template = kitsu_template

        self.worker = ProjectCreationWorker(
            self.builder, nombre, version_blender, dependencias_finales, 
            template_principal, self.ruta_splash, user_vcs, pwd_vcs
        )
        self.worker.result.connect(self._on_creation_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _on_creation_finished(self, exito: bool, mensaje: str):
        if exito:
            self.lbl_status.setText(mensaje)
            self.lbl_status.setStyleSheet("color: #10B981; font-weight: bold;")
            self.on_success() 
            self.close()
        else:
            self.btn_crear.setEnabled(True)
            self.btn_crear.setText("Generar Proyecto")
            self.lbl_status.setText(mensaje)
            self.lbl_status.setStyleSheet("color: #EF4444; font-weight: bold;")

```

--------------------------------------------------------------------------------

### Archivo: `ui/window_svn_login.py`

```python
# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/window_svn_login.py
# Rol Arquitectónico: UI View / Modal Dialog (PySide6)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.6.1
# =========================================================================================

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QWidget
from PySide6.QtCore import Qt
from typing import Callable
from core.vault_manager import VaultManager

class SVNLoginWindow(QDialog):
    def __init__(self, parent: QWidget, vault_manager: VaultManager, on_success_callback: Callable[[], None]):
        """Ventana modal Just-In-Time para solicitar credenciales del Repositorio VCS."""
        super().__init__(parent)
        
        self.setWindowTitle("Autenticación de Repositorio (VCS)")
        self.setFixedSize(350, 250)
        
        # Modal constraints (Forzar foco para bloquear la UI principal)
        self.setModal(True)

        self.vault_manager = vault_manager
        self.on_success_callback = on_success_callback
        
        self.setObjectName("ViewLoginBase") # Reusar el fondo oscuro corporativo del QSS

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)

        self.lbl_info = QLabel("Se requieren credenciales del Repositorio\npara sincronizar el entorno.")
        self.lbl_info.setAlignment(Qt.AlignCenter)
        self.lbl_info.setStyleSheet("color: #F59E0B;") # Ámbar de advertencia
        layout.addWidget(self.lbl_info)

        self.entry_user = QLineEdit()
        self.entry_user.setObjectName("FormInput")
        self.entry_user.setPlaceholderText("Usuario (VCS)")
        self.entry_user.setFixedHeight(40)
        layout.addWidget(self.entry_user)

        self.entry_pwd = QLineEdit()
        self.entry_pwd.setObjectName("FormInput")
        self.entry_pwd.setPlaceholderText("Contraseña")
        self.entry_pwd.setEchoMode(QLineEdit.Password)
        self.entry_pwd.setFixedHeight(40)
        layout.addWidget(self.entry_pwd)

        self.btn_login = QPushButton("Continuar Sincronización")
        self.btn_login.setObjectName("PrimaryButton")
        self.btn_login.setFixedHeight(45)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self.ejecutar_login)
        layout.addWidget(self.btn_login)

    def ejecutar_login(self) -> None:
        """Valida los campos, guarda en la bóveda RAM y reanuda el proceso en pausa."""
        user = self.entry_user.text().strip()
        pwd = self.entry_pwd.text()

        if not user or not pwd:
            self.lbl_info.setText("Ambos campos son obligatorios.")
            self.lbl_info.setStyleSheet("color: #EF4444; font-weight: bold;")
            return

        # Zero-Disk Passwords: Guardar estrictamente en RAM
        self.vault_manager.save_svn_credentials(user, pwd)
        
        self.close()
        # Retomamos el hilo o la función que había invocado esta modal
        self.on_success_callback()

```

--------------------------------------------------------------------------------

### Archivo: `ui/workers/api_queries.py`

```python
import gazu
import glob
import re
from pathlib import Path
from PySide6.QtCore import QThread, Signal

def sanitize_kitsu_name(raw_name: str) -> str:
    if not raw_name:
        return ""
    clean_name = raw_name.lower().replace(" ", "_")
    clean_name = re.sub(r'[^a-z0-9_\-]', '', clean_name)
    return re.sub(r'_+', '_', clean_name)

class FetchProjectsWorker(QThread):
    data_ready = Signal(list)
    error_occurred = Signal(str)

    def run(self):
        try:
            self.data_ready.emit(gazu.project.all_projects())
        except Exception as e:
            self.error_occurred.emit(str(e))

class FetchShotsWorker(QThread):
    """Consulta Kitsu y el disco físico para auditar el estado de los Shots."""
    data_ready = Signal(list, list)
    error_occurred = Signal(str)

    def __init__(self, project_id: str, project_root: Path, vfs_svn: str):
        super().__init__()
        self.project_id = project_id
        self.project_root = project_root
        self.vfs_svn = vfs_svn

    def run(self):
        try:
            import gazu
            # 1. Traemos TODOS los shots y TODAS las secuencias (para mapeo rápido)
            shots = gazu.shot.all_shots_for_project(self.project_id)
            sequences = gazu.shot.all_sequences_for_project(self.project_id)
            all_tasks = gazu.task.all_tasks_for_project(self.project_id)
            task_types = gazu.task.all_task_types()
            
            # Mapa ultra-rápido para no consultar Kitsu por cada shot
            seq_map = {seq["id"]: seq["name"] for seq in sequences}
            tt_map = {tt["id"]: tt["name"] for tt in task_types}
            
            tasks_by_entity = {}
            for task in all_tasks:
                eid = task.get("entity_id")
                if eid not in tasks_by_entity:
                    tasks_by_entity[eid] = []
                tasks_by_entity[eid].append(task)

            result = []
            project_task_types = set()

            for shot in shots:
                shot_id = shot["id"]
                name = shot.get("name", "Unknown")
                seq_name = seq_map.get(shot.get("parent_id"), "Unknow")

                shot_tasks_data = {}
                shot_tasks = tasks_by_entity.get(shot_id, [])

                shot_has_all_files = True
                if not shot_tasks: shot_has_all_files = False

                for task in shot_tasks:
                    tt_name = tt_map.get(task["task_type_id"], "Unknown")
                    project_task_types.add(tt_name)

                    has_file = False
                    
                    task_data = task.get("data")
                    if not task_data:
                        task_data = {}

                    # AHORA AUDITAMOS EL FILEPATH DE LA TAREA, NO DEL SHOT
                    kitsu_filepath = task_data.get("filepath")
                    
                    if kitsu_filepath:
                        physical_path = self.project_root / self.vfs_svn / kitsu_filepath
                        if physical_path.exists():
                            has_file = True

                    shot_tasks_data[tt_name] = {
                        "task_id": task["id"],
                        "has_file": has_file,
                        "raw_task": task
                    }
                    
                    if not has_file:
                        shot_has_all_files = False
                
                # # Obtener el nombre de la secuencia a la que pertenece
                # parent_id = shot.get("parent_id")
                # seq_name = seq_map.get(parent_id, "Unknown")
                #
                # # Inyectamos la secuencia en la data cruda (útil para el render o spawners)
                # shot["sequence_name"] = seq_name
                #
                # # Auditoría usando metadatos de filepath
                # shot_data = shot.get("data")
                # if not shot_data:
                #     shot_data = {}
                #
                # kitsu_filepath = shot_data.get("filepath")
                #
                # if kitsu_filepath:
                #     physical_path = self.project_root / self.vfs_svn / kitsu_filepath
                #     if physical_path.exists():
                #         has_file = True
                #     else:
                #         print(f"[AUDITORIA SHOTS] ⚠️ Ruta registrada en Kitsu, pero no existe: {physical_path}")
                #

                result.append({
                    "id": shot_id,
                    "name": name,
                    "type": "Shot",
                    "parent": seq_name,
                    "frame_in": shot.get("nb_frames", 0),
                    "tasks": shot_tasks_data, # Diccionario con el estado de cada tarea
                    "has_file": shot_has_all_files, # Para bloquear el checkbox principal
                    "raw_data": shot
                })
                
            self.data_ready.emit(result, list(project_task_types))
        except Exception as e:
            self.error_occurred.emit(str(e))

class FetchEntitiesWorker(QThread):
    data_ready = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, pm_core, project_id):
        super().__init__()
        self.pm_core = pm_core
        self.project_id = project_id

    def run(self):
        try:
            self.data_ready.emit(self.pm_core.get_pending_entities(self.project_id))
        except Exception as e:
            self.error_occurred.emit(str(e))

class FetchSequencesWorker(QThread):
    """Consulta las secuencias de Kitsu y verifica su existencia física en el SVN."""
    data_ready = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, project_id: str, project_root: Path, vfs_svn: str):
        super().__init__()
        self.project_id = project_id
        self.project_root = project_root
        self.vfs_svn = vfs_svn

    def run(self):
        try:
            # 1. Traer todas las secuencias del proyecto en Kitsu
            sequences = gazu.shot.all_sequences_for_project(self.project_id)
            
            result = []
            for seq in sequences:
                name = seq.get("name", "").upper()
                
                # 2. Verificar existencia física del .blend
                file_path = self.project_root / self.vfs_svn / "edit" / "storyboards" / f"{name.lower()}-storyboard.blend"
                has_file = file_path.exists()
                
                result.append({
                    "name": name,
                    "has_file": has_file
                })
                
            self.data_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))

class FetchAssetsWorker(QThread):
    """Consulta Kitsu y el disco físico para auditar el estado de los Assets."""
    data_ready = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, project_id: str, project_root: Path, vfs_svn: str):
        super().__init__()
        self.project_id = project_id
        self.project_root = project_root
        self.vfs_svn = vfs_svn

    def run(self):
        try:
            import gazu
            # Extraer todos los assets del proyecto desde la base de datos
            assets = gazu.asset.all_assets_for_project(self.project_id)
            
            # --- Traer todos los Asset Types de Kitsu para mapearlos ---
            all_asset_types = gazu.asset.all_asset_types()
            asset_types_map = {at["id"]: at for at in all_asset_types}
            # ------------------------------------------------------------------

            result = []
            asset_dir = self.project_root / self.vfs_svn / "assets"
            
            for asset in assets:
                raw_name = asset.get("name", "Unknown")
                clean_name= sanitize_kitsu_name(raw_name)

                has_file = False

                asset_data = asset.get("data")
                if not asset_data:
                    asset_data = {}

                kitsu_filepath = asset_data.get("filepath")

                if kitsu_filepath:
                    physical_path = self.project_root / self.vfs_svn / kitsu_filepath

                    if physical_path.exists():
                        has_file = True
                    else:
                        print(f"[AUDITORIA ASSETS] ⚠️ Ruta registrada en Kitsu, pero no existe en disco: {physical_path}")
                else:
                    pass


                # --- Inyectar el Asset Type en la metadata cruda ---
                type_id = asset.get("entity_type_id")
                if type_id and type_id in asset_types_map:
                    asset["asset_type_id"] = type_id
                    asset["asset_type_name"] = asset_types_map[type_id].get("name", "")
                else:
                    asset["asset_type_id"] = ""
                    asset["asset_type_name"] = ""
                # ----------------------------------------------------------

                # if asset_dir.exists():
                #     found = list(asset_dir.rglob(f"*{clean_name}*.blend"))
                #     found = [f for f in found if "blend1" not in str(f)]
                #     if found:
                #         has_file = True

                final_name=raw_name

                if not has_file and raw_name != clean_name:
                    try:
                        # Corregimos el nombre permanentemente en la base de datos de Kitsu
                        asset["name"] = clean_name
                        gazu.asset.update_asset(asset)
                        final_name = clean_name
                    except Exception as e:
                        print(f"⚠️ Error actualizando nombre en Kitsu para {raw_name}: {e}")

                
                asset["name"] = final_name

                result.append({
                    "id": asset["id"],
                    "name": final_name,
                    "type": asset["asset_type_name"],
                    "has_file": has_file,
                    "raw_data": asset # Guardamos la data cruda para el Spawning
                })
                
            self.data_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))

class FetchEditStatusWorker(QThread):
    """Consulta Kitsu y el disco físico para auditar el estado del Master de Edición."""
    data_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, project_id: str, project_name: str, project_root: Path, vfs_svn: str):
        super().__init__()
        self.project_id = project_id
        self.project_name = project_name
        self.project_root = project_root
        self.vfs_svn = vfs_svn

    def run(self):
        try:
            
            # 1. Buscar la entidad Edit en Kitsu (Usualmente Kitsu crea un 'Edit' global)
            edits = gazu.edit.all_edits_for_project(self.project_id)
            main_edit = edits[0] if edits else None
            
            status_name = "Not Created"
            assignees_names = "Unassigned"
            
            # 2. Extraer metadata de Kitsu si existe
            if main_edit:
                tasks = gazu.task.all_tasks_for_edit(main_edit["id"])
                task = tasks[0] if tasks else None

                #main_edit

                task = tasks[0] if tasks else None
                if task:
                    status_name = task.get("task_status", {}).get("name", "N/A")
                    assignees = task.get("assignees", [])
                    if assignees:
                        assignees_names = ", ".join([a.get("full_name", "Unknown") for a in assignees])

            # 3. Auditar la verdad física en el SVN
            edit_dir = self.project_root / self.vfs_svn / "edit"
            has_file = False
            file_name = "File not found"
            version = "N/A"
            
            if edit_dir.exists():
                # Buscar el archivo .blend de edición (ignora auto-saves)
                blend_files = glob.glob(str(edit_dir / "*.blend"))
                blend_files = [f for f in blend_files if "blend1" not in f]
                
                if blend_files:
                    has_file = True
                    blend_files.sort()
                    latest_file = Path(blend_files[-1]) # Tomamos la versión más alta
                    file_name = latest_file.name
                    
                    # Regex para extraer el v001, v002 del final del nombre
                    match = re.search(r'(v\d+)', file_name, re.IGNORECASE)
                    if match:
                        version = match.group(1).lower()

            # 4. Empaquetar resultados
            result = {
                "has_file": has_file,
                "file_name": file_name,
                "version": version,
                "assignees": assignees_names,
                "status": status_name
            }
            
            self.data_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))

```

--------------------------------------------------------------------------------

### Archivo: `ui/workers/blender_spawners.py`

```python
import gazu
import subprocess
import os
import glob
import platform
from pathlib import Path
from PySide6.QtCore import QThread, Signal


class BatchCreationWorker(QThread):
    progress_updated = Signal(int, str)
    log_stream = Signal(str)
    finished_batch = Signal(bool, str)

    def __init__(self, pm_core, config_factory, project_id: str, project_name: str, entities: list, task_types: list):
        super().__init__()
        self.pm_core = pm_core
        self.config = config_factory
        self.project_id = project_id
        self.project_name = project_name
        self.entities = entities # Lista de dicts crudos
        self.task_types = task_types

    def run(self):
        try:
            total_ents = len(self.entities)
            if total_ents == 0:
                self.finished_batch.emit(False, "No entities provided.")
                return

            nas_root = self.config.get_workspace_root()
            vfs_local = self.config.get_vfs_local_name()
            folder_name = self.project_name.strip().lower().replace(" ", "-")
            project_root = nas_root / folder_name
            base_blender_dir = project_root / vfs_local / "blender-build"
            
            import platform, glob, os, subprocess
            os_name = platform.system().lower()
            if os_name == "windows":
                exe_list = glob.glob(str(base_blender_dir / "**" / "blender.exe"), recursive=True)
            elif os_name == "darwin":
                exe_list = glob.glob(str(base_blender_dir / "**" / "MacOS" / "Blender"), recursive=True)
            else:
                exe_list = glob.glob(str(base_blender_dir / "**" / "blender"), recursive=True)
                
            if not exe_list:
                raise FileNotFoundError("Blender binary not found in sandbox.")

            vfs_svn = self.config.get_vfs_svn_name()

            for idx, entity in enumerate(self.entities):
                e_name = entity.get("name", "Unknown")
                e_id = entity.get("id", "")
                e_type = entity.get("type", "Asset").upper()
                
                # --- NUEVA LÓGICA DE FILTRADO POR TAREAS ---
                tasks_to_spawn = []
                if e_type == "SHOT":
                    tasks_dict = entity.get("tasks", {})
                    for t_name in self.task_types:
                        # Solo forjamos si la toma tiene esta tarea en Kitsu y NO tiene archivo
                        task_info = tasks_dict.get(t_name)
                        if task_info and not task_info.get("has_file"):
                            tasks_to_spawn.append(t_name)
                else:
                    # Los Assets conservan su comportamiento de iterar una vez por ahora
                    tasks_to_spawn = [""] 
                # -------------------------------------------
                
                # Bucle anidado para iterar cada tarea faltante de la entidad
                for t_idx, t_name in enumerate(tasks_to_spawn):
                    
                    display_name = f"{e_name} [{t_name}]" if t_name else e_name
                    base_progress = 10 + int((idx / total_ents) * 90)
                    self.progress_updated.emit(base_progress, self.tr(f"Processing {e_type}: {display_name} ({idx+1}/{total_ents})"))
                    
                    self.log_stream.emit(f"\n[{display_name}] Spawning physical file via Headless Engine...")
                    
                    env = os.environ.copy()
                    env["OPENSTUDIO_BUILD_TARGET"] = e_type 
                    env["OPENSTUDIO_PROJECT_ROOT"] = str(project_root)
                    env["OPENSTUDIO_PRODUCTION_FOLDER"] = vfs_svn
                    env["BLENDER_USER_RESOURCES"] = str(project_root / vfs_local / "blender_data")
                    env["OPENSTUDIO_KITSU_PROJECT_ID"] = str(self.project_id)
                    env["OPENSTUDIO_TARGET_ENTITY_ID"] = str(e_id) 
                    env["OPENSTUDIO_KITSU_ENTITY_NAME"] = str(e_name)
                    
                    env["OPENSTUDIO_KITSU_ASSET_TYPE_ID"] = str(entity.get("asset_type_id", ""))
                    env["OPENSTUDIO_KITSU_ASSET_TYPE_NAME"] = str(entity.get("asset_type_name", ""))

                    # Inyección dinámica de la secuencia y el tipo de tarea
                    if e_type == "SHOT":
                        env["OPENSTUDIO_KITSU_SEQUENCE_NAME"] = str(entity.get("parent", ""))
                        env["OPENSTUDIO_KITSU_TASK_TYPE_NAME"] = str(t_name) 
                    
                    env["OPENSTUDIO_KITSU_HOST"] = self.config.get_kitsu_api_url()
                    env["OPENSTUDIO_KITSU_USER"] = os.environ.get("OPENSTUDIO_KITSU_USER", "")
                    env["OPENSTUDIO_KITSU_PWD"] = os.environ.get("OPENSTUDIO_KITSU_PWD", "")
                    
                    script_path = Path(__file__).parent.parent.parent / "core" / "templates" / "headless_builder.py"
                    cmd = [exe_list[0], "-b", "--python", str(script_path)]
                    
                    proceso = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    for line in proceso.stdout:
                        if line.strip(): self.log_stream.emit(f"    ↳ {line.strip()}")
                    proceso.wait()
                    
                    if proceso.returncode != 0:
                        self.log_stream.emit(f"[{display_name}] ❌ ERROR: Blender Headless failed.")
                    else:
                        self.log_stream.emit(f"[{display_name}] ✓ Physical file spawned.")

                # base_progress = 10 + int((idx / total_ents) * 90)
                # self.progress_updated.emit(base_progress, self.tr(f"Processing {e_type}: {e_name} ({idx+1}/{total_ents})"))
                #
                # self.log_stream.emit(f"\n[{e_name}] Spawning physical file via Headless Engine...")
                #
                # env = os.environ.copy()
                # env["OPENSTUDIO_BUILD_TARGET"] = e_type # "ASSET" o "SHOT"
                # env["OPENSTUDIO_PROJECT_ROOT"] = str(project_root)
                # env["OPENSTUDIO_PRODUCTION_FOLDER"] = vfs_svn
                # env["BLENDER_USER_RESOURCES"] = str(project_root / vfs_local / "blender_data")
                # env["OPENSTUDIO_KITSU_PROJECT_ID"] = str(self.project_id)
                # env["OPENSTUDIO_TARGET_ENTITY_ID"] = str(e_id) # <- ID Inyectado
                # env["OPENSTUDIO_KITSU_ENTITY_NAME"] = str(e_name)
                #
                # # Inyectamos los datos del Asset Type que arreglamos en el ProductionManager
                # env["OPENSTUDIO_KITSU_ASSET_TYPE_ID"] = str(entity.get("asset_type_id", ""))
                # env["OPENSTUDIO_KITSU_ASSET_TYPE_NAME"] = str(entity.get("asset_type_name", ""))
                #
                # # Si llega a ser un Shot, enviamos el nombre de la secuencia (que está guardado en "parent")
                # if e_type == "SHOT":
                #     env["OPENSTUDIO_KITSU_SEQUENCE_NAME"] = str(entity.get("sequence_name", ""))
                #     env["OPENSTUDIO_KITSU_TASK_TYPE_NAME"] = "Layout"
                # # ----------------------------------------
                #
                # env["OPENSTUDIO_KITSU_HOST"] = self.config.get_kitsu_api_url()
                # env["OPENSTUDIO_KITSU_USER"] = os.environ.get("OPENSTUDIO_KITSU_USER", "")
                # env["OPENSTUDIO_KITSU_PWD"] = os.environ.get("OPENSTUDIO_KITSU_PWD", "")
                #  # --- DEBUG: VOLCADO COMPLETO DEL ENTORNO ---
                # print("\n" + "="*60)
                # print("🔍 AUDITORÍA COMPLETA DE VARIABLES DE ENTORNO")
                # print("="*60)
                #
                # # Cambia 'clean_env' por 'env' si quieres ver el diccionario original
                # for key, value in sorted(env.items()):
                #     # Filtramos un poco para no imprimir las cientos de variables base del sistema, 
                #     # y centrarnos solo en las inyectadas por OpenStudio o Blender.
                #     if key.startswith("OPENSTUDIO_") or key.startswith("BLENDER_"):
                #         print(f"[{key}]: '{value}'")
                #
                # print("="*60 + "\n")
                # # -------------------------------------------
                # script_path = Path(__file__).parent.parent.parent / "core" / "templates" / "headless_builder.py"
                # cmd = [exe_list[0], "-b", "--python", str(script_path)]
                #
                # proceso = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                # for line in proceso.stdout:
                #     if line.strip(): self.log_stream.emit(f"    ↳ {line.strip()}")
                # proceso.wait()
                #
                # if proceso.returncode != 0:
                #     self.log_stream.emit(f"[{e_name}] ❌ ERROR: Blender Headless failed.")
                # else:
                #     self.log_stream.emit(f"[{e_name}] ✓ Physical file spawned.")

            self.progress_updated.emit(100, self.tr("Batch Creation Complete!"))
            self.finished_batch.emit(True, f"{total_ents} entities processed successfully.")
            
        except Exception as e:
            self.finished_batch.emit(False, str(e))

class MasterSpawningWorker(QThread):
    progress_updated = Signal(int, str)
    log_stream = Signal(str)
    finished_spawn = Signal(bool, str)

    def __init__(self, config_factory, project_name, build_target, project_id=""):
        super().__init__()
        self.config = config_factory
        self.project_name = project_name
        self.build_target = build_target
        self.project_id = project_id

    def run(self):
        try:
            self.progress_updated.emit(10, self.tr("Locating project and sandbox..."))
            nas_root = self.config.get_workspace_root()
            vfs_local = self.config.get_vfs_local_name()
            folder_name = self.project_name.strip().lower().replace(" ", "-")
            project_root = nas_root / folder_name
            
            base_blender_dir = project_root / vfs_local / "blender-build"
            os_name = platform.system().lower()
            if os_name == "windows":
                exe_list = glob.glob(str(base_blender_dir / "**" / "blender.exe"), recursive=True)
            elif os_name == "darwin":
                exe_list = glob.glob(str(base_blender_dir / "**" / "MacOS" / "Blender"), recursive=True)
            else:
                exe_list = glob.glob(str(base_blender_dir / "**" / "blender"), recursive=True)
                
            if not exe_list:
                raise FileNotFoundError("Blender binary not found in sandbox.")
            blender_bin = exe_list[0]

            self.progress_updated.emit(20, self.tr("Preparing environment variables..."))
            env = os.environ.copy()
            
            # --- INYECCIÓN DE DEPENDENCIAS ---
            env["OPENSTUDIO_BUILD_TARGET"] = self.build_target
            env["OPENSTUDIO_PROJECT_ROOT"] = str(project_root)
            env["OPENSTUDIO_PRODUCTION_FOLDER"] = self.config.get_vfs_svn_name()
            env["BLENDER_USER_RESOURCES"] = str(project_root / vfs_local / "blender_data")
            env["OPENSTUDIO_KITSU_PROJECT_ID"] = str(self.project_id)
            
            # --- CÓDIGO CORREGIDO ---
            env["OPENSTUDIO_KITSU_HOST"] = self.config.get_kitsu_api_url()
            env["OPENSTUDIO_KITSU_USER"] = os.environ.get("OPENSTUDIO_KITSU_USER", "")
            env["OPENSTUDIO_KITSU_PWD"] = os.environ.get("OPENSTUDIO_KITSU_PWD", "")
            # ----------------------------------------
            
            script_path = Path(__file__).parent.parent.parent / "core" / "templates" / "headless_builder.py"
            
            self.progress_updated.emit(30, self.tr("Booting Blender Engine..."))
            cmd = [str(blender_bin), "-b", "--python", str(script_path)]
            proceso = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            for line in proceso.stdout:
                line_clean = line.strip()
                if not line_clean: continue
                self.log_stream.emit(line_clean)
                
                if "Cargando App-Template" in line_clean:
                    self.progress_updated.emit(50, self.tr("Loading UI Template..."))
                elif "Restaurando contexto Kitsu" in line_clean:
                    self.progress_updated.emit(70, self.tr("Authenticating with server..."))
                elif "GUARDADO FORZADO EXITOSO" in line_clean:
                    self.progress_updated.emit(90, self.tr("Writing physical file..."))
            
            proceso.wait()
            if proceso.returncode == 0:
                self.progress_updated.emit(100, self.tr("Master File Forged Successfully!"))
                self.finished_spawn.emit(True, f"{self.build_target} created.")
            else:
                raise RuntimeError(f"Blender crashed with return code {proceso.returncode}")
                
        except Exception as e:
            self.finished_spawn.emit(False, str(e))

class StoryboardBatchWorker(QThread):
    progress_updated = Signal(int, str)
    log_stream = Signal(str)
    finished_batch = Signal(bool, str)

    def __init__(self, pm_core, config_factory, project_id: str, project_name: str, sequence_names: list):
        super().__init__()
        self.pm_core = pm_core
        self.config = config_factory
        self.project_id = project_id
        self.project_name = project_name
        self.sequence_names = sequence_names

    def run(self):
        try:
            total_seqs = len(self.sequence_names)
            if total_seqs == 0:
                self.finished_batch.emit(False, self.tr("The sequence list is empty."))
                return

            self.progress_updated.emit(5, self.tr("Verifying Kitsu Pipeline schema..."))
            storyboard_tt = self.pm_core.get_or_create_storyboard_task_type(self.project_id)
            tt_id = storyboard_tt["id"]
            
            nas_root = self.config.get_workspace_root()
            vfs_local = self.config.get_vfs_local_name()
            folder_name = self.project_name.strip().lower().replace(" ", "-")
            project_root = nas_root / folder_name
            base_blender_dir = project_root / vfs_local / "blender-build"
            
            os_name = platform.system().lower()
            if os_name == "windows":
                exe_list = glob.glob(str(base_blender_dir / "**" / "blender.exe"), recursive=True)
            elif os_name == "darwin":
                exe_list = glob.glob(str(base_blender_dir / "**" / "MacOS" / "Blender"), recursive=True)
            else:
                exe_list = glob.glob(str(base_blender_dir / "**" / "blender"), recursive=True)
                
            if not exe_list:
                raise FileNotFoundError("Blender binary not found in sandbox.")

            for idx, seq_name in enumerate(self.sequence_names):
                base_progress = 10 + int((idx / total_seqs) * 90)
                self.progress_updated.emit(base_progress, self.tr(f"Processing Sequence: {seq_name} ({idx+1}/{total_seqs})"))
                
                self.log_stream.emit(f"\n[{seq_name}] Registering Entity and Task in Kitsu API...")
                existing_seq = gazu.shot.get_sequence_by_name(self.project_id, seq_name)
                
                if not existing_seq:
                    existing_seq = self.pm_core.create_sequence_with_task(self.project_id, seq_name, tt_id)
                    self.log_stream.emit(f"[{seq_name}] ✓ Kitsu database updated.")
                else:
                    self.log_stream.emit(f"[{seq_name}] ⚠️ Sequence already exists. Skipping Kitsu creation.")
               
                vfs_svn = self.config.get_vfs_svn_name()
                
                try:
                    storyboard_tt = self.pm_core.get_or_create_storyboard_task_type(self.project_id)
                    task = gazu.task.get_task_by_entity(existing_seq, storyboard_tt)
                    
                    if task is None:
                        self.log_stream.emit(f"[{seq_name}] Tarea no encontrada. Creando nueva tarea 'main'...")
                        default_status = gazu.task.get_default_task_status()
                        task = gazu.task.new_task(existing_seq, storyboard_tt, name="main", task_status=default_status)
                    
                    rel_path = f"{vfs_svn}/edit/storyboards/{seq_name.lower()}-storyboard.blend"
                    
                    seq_data = existing_seq.get("data")
                    if not seq_data:
                        seq_data = {}

                    seq_data["blend_file_path"] = rel_path
                    gazu.shot.update_sequence_data(existing_seq["id"], seq_data)
                    self.log_stream.emit(f"[{seq_name}] ✓ File path saved in Sequence metadata: {rel_path}")
                    
                    software = gazu.files.get_software_by_name("Blender")
                    if software and task:
                        gazu.files.new_working_file(task, software, name=rel_path)
                        
                    self.log_stream.emit(f"[{seq_name}] ✓ File path mapped to Kitsu Task.")
                except Exception as e:
                    self.log_stream.emit(f"[{seq_name}] ⚠️ Fallo al mapear archivo en Kitsu: {e}")

                self.log_stream.emit(f"[{seq_name}] Spawning physical .blend file via Headless Engine...")
                
                env = os.environ.copy()
                
                # --- INYECCIÓN DE DEPENDENCIAS ---
                env["OPENSTUDIO_BUILD_TARGET"] = "STORYBOARD"
                env["OPENSTUDIO_PROJECT_ROOT"] = str(project_root)
                env["OPENSTUDIO_PRODUCTION_FOLDER"] = vfs_svn
                env["BLENDER_USER_RESOURCES"] = str(project_root / vfs_local / "blender_data")
                env["OPENSTUDIO_TARGET_SEQUENCE"] = seq_name 
                env["OPENSTUDIO_KITSU_PROJECT_ID"] = str(self.project_id)
                
                # --- CÓDIGO CORREGIDO ---
                env["OPENSTUDIO_KITSU_HOST"] = self.config.get_kitsu_api_url()
                env["OPENSTUDIO_KITSU_USER"] = os.environ.get("OPENSTUDIO_KITSU_USER", "")
                env["OPENSTUDIO_KITSU_PWD"] = os.environ.get("OPENSTUDIO_KITSU_PWD", "")
                # ----------------------------------------
                
                script_path = Path(__file__).parent.parent.parent / "core" / "templates" / "headless_builder.py"
                cmd = [exe_list[0], "-b", "--python", str(script_path)]
                
                proceso = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in proceso.stdout:
                    if line.strip(): self.log_stream.emit(f"    ↳ {line.strip()}")
                proceso.wait()
                
                if proceso.returncode != 0:
                    self.log_stream.emit(f"[{seq_name}] ❌ ERROR: Blender Headless failed.")
                else:
                    self.log_stream.emit(f"[{seq_name}] ✓ Physical file spawned.")

            self.progress_updated.emit(100, self.tr("Batch Creation Complete!"))
            self.finished_batch.emit(True, f"{total_seqs} Storyboard sequences processed successfully.")
            
        except Exception as e:
            self.finished_batch.emit(False, str(e))

```

--------------------------------------------------------------------------------

