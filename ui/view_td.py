import customtkinter as ctk
from ui.window_new_project import NewProjectWindow
from ui.widget_project_list import ProjectListWidget

class ViewTD(ctk.CTkFrame):
    def __init__(self, parent, auth_manager, nextcloud_dir, on_logout):
        super().__init__(parent, fg_color="transparent")
        self.auth = auth_manager
        self.nextcloud_dir = nextcloud_dir
        self.on_logout = on_logout

        nombre = self.auth.user_data.get('first_name', 'Usuario')
        rol = self.auth.get_user_role()

        # Barra superior de navegacion
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=10, padx=20)

        lbl_bienvenida = ctk.CTkLabel(
            header_frame, 
            text=f"Usuario: {nombre} | Rol: {rol.upper()}", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl_bienvenida.pack(side="left")

        btn_logout = ctk.CTkButton(
            header_frame, text="Cerrar Sesion", fg_color="#A12A2A", 
            hover_color="#731D1D", width=100, command=self.on_logout
        )
        btn_logout.pack(side="right")

        # Panel exclusivo de Director Tecnico
        td_frame = ctk.CTkFrame(self)
        td_frame.pack(fill="x", pady=(10, 0), padx=20)
        
        lbl_td = ctk.CTkLabel(td_frame, text="Herramientas de Administracion", font=ctk.CTkFont(weight="bold"))
        lbl_td.pack(pady=(10, 5))
        
        btn_crear_proyecto = ctk.CTkButton(td_frame, text="Crear Nuevo Proyecto", command=self.abrir_wizard_proyecto)
        btn_crear_proyecto.pack(pady=(0, 10))

        # Titulo de la lista
        lbl_proyectos = ctk.CTkLabel(self, text="Proyectos Activos", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_proyectos.pack(pady=(15, 5), padx=20, anchor="w")

        # Inyeccion del componente reutilizable (ProjectListWidget)
        self.lista_proyectos = ProjectListWidget(
            parent=self, 
            nextcloud_dir=self.nextcloud_dir, 
            status_callback=self.actualizar_estado_callback,
            width=540, 
            height=200
        )
        self.lista_proyectos.pack(pady=5, padx=20, fill="both", expand=True)

        # Barra de estado inferior
        self.label_estado = ctk.CTkLabel(self, text="Panel de administracion listo.", text_color="gray")
        self.label_estado.pack(pady=10)

    def actualizar_estado_callback(self, mensaje, color="white"):
        try:
            self.label_estado.configure(text=mensaje, text_color=color)
        except Exception:
            pass

    def abrir_wizard_proyecto(self):
        """Abre la ventan modal para inicializar un proyecto nuevo."""
        NewProjectWindow(
            parent=self,
            nextcloud_dir=self.nextcloud_dir,
            on_success_callback=self.lista_proyectos.cargar_proyectos
        )
