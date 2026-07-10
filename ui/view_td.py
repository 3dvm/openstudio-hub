import customtkinter as ctk
from ui.window_new_project import NewProjectWindow
from ui.widget_project_list import ProjectListWidget

class ViewTD(ctk.CTkFrame):
    def __init__(self, parent, auth_manager, nextcloud_dir, vault_manager, on_logout):
        """
        Panel de control avanzado para el Director Técnico (TD).
        Permite la visualización y la inicialización de nuevos pipelines en el servidor.
        """
        super().__init__(parent, fg_color="transparent")
        self.auth = auth_manager
        self.nextcloud_dir = nextcloud_dir
        self.on_logout = on_logout
        self.vault = vault_manager # Guardamos la referencia para el modal del mago

        # --- BARRA SUPERIOR ---
        top_bar = ctk.CTkFrame(self, height=50)
        top_bar.pack(fill="x", padx=20, pady=(20, 10))

        rol = self.auth.get_user_role()
        nombre_user = self.auth.user_data.get("first_name", rol)
        
        lbl_welcome = ctk.CTkLabel(top_bar, text=f"{nombre_user} [Panel Técnico / TD]", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_welcome.pack(side="left", padx=15, pady=10)

        # Barra superior de navegacion
        btn_logout = ctk.CTkButton(top_bar, text="Cerrar Sesión", width=100, fg_color="#EF4444", hover_color="#DC2626", command=self.on_logout)
        btn_logout.pack(side="right", padx=15, pady=10)

        # --- ACCIONES DE ADMINISTRACIÓN ---
        admin_bar = ctk.CTkFrame(self, height=60, fg_color="transparent")
        admin_bar.pack(fill="x", padx=20, pady=10)

        btn_nuevo_proy = ctk.CTkButton(
            admin_bar, 
            text="Crear Nuevo Proyecto", 
            font=ctk.CTkFont(weight="bold"),
            fg_color="#10B981", # Verde esmeralda de operaciones exitosas
            hover_color="#059669",
            command=self.abrir_wizard_proyecto
        )
        btn_nuevo_proy.pack(side="left", padx=5)

        # --- LISTA DE PROYECTOS ---
        lbl_seccion = ctk.CTkLabel(self, text="Monitoreo de Pipelines Globales:", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_seccion.pack(pady=(10, 5), padx=25, anchor="w")

        # --- BARRA DE ESTADO ---
        self.status_bar = ctk.CTkFrame(self, height=30)
        self.status_bar.pack(fill="x", side="bottom", padx=20, pady=(0, 20))

        self.lbl_status = ctk.CTkLabel(self.status_bar, text="Listo.", text_color="gray", font=ctk.CTkFont(size=11))
        self.lbl_status.pack(side="left", padx=15, pady=5)

        # === INYECCIÓN DEL COMPONENTE DE LISTA ===
        self.lista_proyectos = ProjectListWidget(
            parent=self,
            nextcloud_dir=self.nextcloud_dir,
            auth_manager=self.auth,
            vault_manager=vault_manager,
            status_callback=self.actualizar_status,
            width=550,
            height=340
        )
        self.lista_proyectos.pack(fill="both", expand=True, padx=20, pady=10)

    def abrir_wizard_proyecto(self):
        """Abre la ventan modal para inicializar un proyecto nuevo."""
        NewProjectWindow(
            parent=self.winfo_toplevel(),
            nextcloud_dir=self.nextcloud_dir,
            on_success_callback=self.lista_proyectos.cargar_proyectos
        )

    def actualizar_status(self, mensaje: str, color: str = "white"):
        colores = {"green": "#10B981", "yellow": "#F59E0B", "red": "#EF4444", "gray": "#9CA3AF", "white": "#FFFFFF"}
        texto_color = colores.get(color, color)
        self.lbl_status.configure(text=mensaje, text_color=texto_color)
