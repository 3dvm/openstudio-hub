import customtkinter as ctk
from ui.widget_project_list import ProjectListWidget

class ViewArtist(ctk.CTkFrame):
    def __init__(self, parent, auth_manager, nextcloud_dir, vault_manager, on_logout):
        """
        Panel de control para los Artistas.
        Muestra la lista de proyectos asignados y control de estados.
        """
        super().__init__(parent, fg_color="transparent")
        self.auth = auth_manager
        self.nextcloud_dir = nextcloud_dir
        self.on_logout = on_logout

        # --- BARRA SUPERIOR (Usuario y Logout) ---
        top_bar = ctk.CTkFrame(self, height=50)
        top_bar.pack(fill="x", padx=20, pady=(20, 10))

        # Barra superior de navegacion
        rol = self.auth.get_user_role()
        nombre_user = self.auth.user_data.get("first_name", rol)
        
        lbl_welcome = ctk.CTkLabel(top_bar, text=f"¡Hola, {nombre_user}! [Panel Artista]", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_welcome.pack(side="left", padx=15, pady=10)

        btn_logout = ctk.CTkButton(top_bar, text="Cerrar Sesión", width=100, fg_color="#EF4444", hover_color="#DC2626", command=self.on_logout)
        btn_logout.pack(side="right", padx=15, pady=10)

        # --- CONTENIDO PRINCIPAL ---
        lbl_seccion = ctk.CTkLabel(self, text="Tus Proyectos Activos:", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_seccion.pack(pady=(10, 5), padx=25, anchor="w")

        # --- BARRA DE ESTADO INFERIOR ---
        self.status_bar = ctk.CTkFrame(self, height=30)
        self.status_bar.pack(fill="x", side="bottom", padx=20, pady=(0, 20))

        self.lbl_status = ctk.CTkLabel(self.status_bar, text="Listo.", text_color="gray", font=ctk.CTkFont(size=11))
        self.lbl_status.pack(side="left", padx=15, pady=5)

        # === INYECCIÓN DEL COMPONENTE DE LISTA ===
        # Pasamos el vault_manager recibido al inicializar el widget de lista
        self.lista_proyectos = ProjectListWidget(
            parent=self,
            nextcloud_dir=self.nextcloud_dir,
            vault_manager=vault_manager,
            status_callback=self.actualizar_status,
            width=550,
            height=400
        )
        self.lista_proyectos.pack(fill="both", expand=True, padx=20, pady=10)

    def actualizar_status(self, mensaje: str, color: str = "white"):
        """Callback seguro para que los componentes hijos reporten su progreso."""
        # Mapeo simple de colores amigables para el tema oscuro de CustomTkinter
        colores = {"green": "#10B981", "yellow": "#F59E0B", "red": "#EF4444", "gray": "#9CA3AF", "white": "#FFFFFF"}
        texto_color = colores.get(color, color)
        
        self.lbl_status.configure(text=mensaje, text_color=texto_color)
