import bpy
import sys

# =========================================================================================
# PROPIEDADES DE LA ESCENA (Registrar al iniciar el add-on)
# =========================================================================================

class OpenStudioKitsuProperties(bpy.types.PropertyGroup):
    """Propiedades temporales para la creación del Shot en Kitsu."""
    sequence_name: bpy.props.StringProperty(
        name="Sequence",
        description="Nombre de la secuencia a la que pertenece la toma",
        default="SQ010"
    )
    shot_name: bpy.props.StringProperty(
        name="Shot Name",
        description="Nombre de la nueva toma",
        default="SH010"
    )

# =========================================================================================
# INTERFAZ GRÁFICA: PANEL EN EL VIEWPORT
# =========================================================================================

class OPENSTUDIO_PT_kitsu_panel(bpy.types.Panel):
    """Panel unificado para enviar tomas a Kitsu desde OpenStudio Toolkit."""
    bl_label = "Kitsu: Shot Builder"
    bl_idname = "OPENSTUDIO_PT_kitsu_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OpenStudio"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        kitsu_props = scene.os_kitsu_props

        # Caja de Nomenclatura
        box = layout.box()
        box.label(text="Shot Identification:", icon='INFO')
        box.prop(kitsu_props, "sequence_name")
        box.prop(kitsu_props, "shot_name")

        layout.separator()

        # Caja de Datos de la Escena (Lectura de fotogramas)
        box_scene = layout.box()
        box_scene.label(text="Current Scene Data:", icon='SCENE_DATA')
        row = box_scene.row()
        row.label(text=f"Start Frame: {scene.frame_start}")
        row.label(text=f"End Frame: {scene.frame_end}")

        layout.separator()

        # Botón de Enviar Toma (Requisito explícito en inglés)
        layout.operator("openstudio.send_shot", text="Send Shot", icon='EXPORT')

# =========================================================================================
# OPERADOR PRINCIPAL: SEND SHOT
# =========================================================================================

class OPENSTUDIO_OT_send_shot(bpy.types.Operator):
    """
    Toma los datos de la escena y crea la toma en Kitsu usando la API interna 
    del add-on/extensión Blender Kitsu, extrayendo el módulo desde sys.modules.
    """
    bl_idname = "openstudio.send_shot"
    bl_label = "Send Shot"
    bl_description = "Registra la toma y secuencia en Kitsu usando los fotogramas de la escena"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        kitsu_props = scene.os_kitsu_props
        
        seq_name = kitsu_props.sequence_name
        shot_name = kitsu_props.shot_name
        frame_start = scene.frame_start
        frame_end = scene.frame_end

        # 1. Validación básica
        if not seq_name or not shot_name:
            self.report({'WARNING'}, "Sequence and Shot names cannot be empty.")
            return {'CANCELLED'}

        print("\n==================================================")
        print(f"[OPENSTUDIO KITSU] Iniciando creación por API: {seq_name} / {shot_name}")
        print(f" -> Rango de fotogramas: {frame_start} a {frame_end}")

        # 2. Extracción segura del módulo 'cache' desde la memoria de Blender
        # Esto evita el error de "ModuleNotFoundError" en el nuevo sistema de extensiones.
        kitsu_cache = sys.modules.get("blender_kitsu.cache")
        
        if not kitsu_cache:
            self.report({'ERROR'}, "Kitsu cache module not found. Is the extension enabled?")
            return {'CANCELLED'}

        try:
            # 3. Obtener el proyecto activo actual del usuario
            project = kitsu_cache.project_active_get()
            
            if not project:
                self.report({'ERROR'}, "No active Kitsu project found. Please select one in Kitsu.")
                return {'CANCELLED'}

            # 4. Buscar o crear la secuencia mediante la API de Kitsu
            seq = project.get_sequence_by_name(seq_name)
            if not seq:
                print(f" -> La secuencia {seq_name} no existe. Creándola...")
                seq = project.create_sequence(sequence_name=seq_name)
                
            if not seq:
                self.report({'ERROR'}, "Failed to find or create the Sequence in Kitsu.")
                return {'CANCELLED'}

            # 5. Buscar o crear la toma (Shot) mediante la API
            shot = project.get_shot_by_name(sequence=seq, name=shot_name)
            if not shot:
                print(f" -> El shot {shot_name} no existe. Creándolo...")
                shot = project.create_shot(
                    sequence=seq,
                    shot_name=shot_name,
                    frame_in=frame_start,
                    frame_out=frame_end
                )
                self.report({'INFO'}, f"Shot '{shot_name}' successfully created in Kitsu!")
            else:
                self.report({'INFO'}, f"Shot '{shot_name}' already exists in this sequence.")

        except Exception as e:
            self.report({'ERROR'}, f"Kitsu API Error: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}

# =========================================================================================
# FUNCIONES DE REGISTRO
# =========================================================================================

classes = (
    OpenStudioKitsuProperties,
    OPENSTUDIO_PT_kitsu_panel,
    OPENSTUDIO_OT_send_shot,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # Registrar el PointerProperty en la escena
    bpy.types.Scene.os_kitsu_props = bpy.props.PointerProperty(type=OpenStudioKitsuProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.os_kitsu_props

if __name__ == "__main__":
    register()
