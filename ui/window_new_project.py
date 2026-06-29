import json
import customtkinter as ctk
from customtkinter import filedialog
from pathlib import Path
from core.project_builder import ProjectBuilder

class NewProjectWindow(ctk.CTkToplevel):
    def __init__(self, parent, nextcloud_dir, on_success_callback):
        super().__init__(parent)
        self.title("Nuevo Proyecto")
        self.geometry("450x690") # Agrandamos un poco mas para el nuevo selector

        self.ruta_splash = ""
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()

        self.builder = ProjectBuilder(nextcloud_dir)
        self.on_success = on_success_callback
        
        # Rutas dinamicas de la boveda
        self.manifests_dir = nextcloud_dir.parent / "04_BIBLIOTECA_ASSETS" / "00_SOFTWARE" / "manifests"
        self.templates_dir = nextcloud_dir.parent / "04_BIBLIOTECA_ASSETS" / "00_SOFTWARE" / "templates"
        
        self.manifestos_data = self._cargar_manifestos()
        self.templates_disponibles = self._cargar_templates()
        self.checkboxes_addons = {}

        # --- DISEÑO DE LA INTERFAZ ---
        lbl_titulo = ctk.CTkLabel(self, text="Configuracion Inicial", font=ctk.CTkFont(size=18, weight="bold"))
        lbl_titulo.pack(pady=(20, 10))

        # 1. Nombre
        self.entry_nombre = ctk.CTkEntry(self, placeholder_text="Nombre (ej. p0004-nuevo-proyecto)", width=350)
        self.entry_nombre.pack(pady=10)

        # 2. Selector de Template
        lbl_template = ctk.CTkLabel(self, text="Template de Pipeline:")
        lbl_template.pack(pady=(10, 0))
        
        self.combo_template = ctk.CTkComboBox(self, values=self.templates_disponibles, width=350)
        self.combo_template.pack(pady=5)

        # 3. Selector de Version de Blender
        lbl_version = ctk.CTkLabel(self, text="Version de Blender Objetivo:")
        lbl_version.pack(pady=(10, 0))
        
        versiones = list(self.manifestos_data.keys()) if self.manifestos_data else ["Default"]
        self.combo_version = ctk.CTkComboBox(
            self, 
            values=versiones, 
            width=350,
            command=self.dibujar_addons_dinamicos
        )
        self.combo_version.pack(pady=5)

        # 4. Plugins y Dependencias
        lbl_addons = ctk.CTkLabel(self, text="Plugins y Dependencias:", font=ctk.CTkFont(weight="bold"))
        lbl_addons.pack(pady=(15, 5), padx=50, anchor="w")
        
        self.frame_addons = ctk.CTkScrollableFrame(self, width=330, height=120)
        self.frame_addons.pack(pady=0, padx=50, fill="x")

        if versiones:
            self.dibujar_addons_dinamicos(self.combo_version.get())

        lbl_splash = ctk.CTkLabel(self, text="Splash Screen Personalizado(1000x500px):")
        lbl_splash.pack( pady=(10,0) )

        frame_splash = ctk.CTkFrame(self, fg_color="transparent")
        frame_splash.pack(pady=5, fill="x", padx=50)

        self.btn_splash = ctk.CTkButton(
                frame_splash,
                text="Buscar PNG",
                command=self.seleccionar_splash,
                width=120,
                fg_color="#4F46E5",
                hover_color="#4338CA"
        )
        self.btn_splash.pack( side="left", padx=(0,10) )

        self.lbl_splash_name = ctk.CTkLabel(frame_splash, text="Ninguna imagen", text_color="gray")
        self.lbl_splash_name.pack(side="left", fill="x", expand=True)

        # Feedback y Boton
        self.lbl_status = ctk.CTkLabel(self, text="", text_color="red")
        self.lbl_status.pack(pady=10)

        self.btn_crear = ctk.CTkButton(self, text="Generar Proyecto", command=self.ejecutar_creacion)
        self.btn_crear.pack(pady=10)

    def seleccionar_splash(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar Splash Screen del Proyecto",
            filetypes=[("Imágenes PNG", "*.png")]
        )
        if ruta:
            self.ruta_splash = ruta
            nombre_archivo = Path(ruta).name
            self.lbl_splash_name.configure(text=nombre_archivo, text_color="white")

    def _cargar_manifestos(self) -> dict:
        data = {}
        if self.manifests_dir.exists():
            for archivo in self.manifests_dir.glob("*.json"):
                try:
                    with open(archivo, 'r', encoding='utf-8') as f:
                        manifesto = json.load(f)
                        version = manifesto.get("blender_version")
                        if version:
                            data[version] = manifesto.get("available_addons", {})
                except Exception:
                    pass
        return data

    def _cargar_templates(self) -> list:
        """Escanea la carpeta de templates y retorna los nombres de las carpetas."""
        templates = []
        if self.templates_dir.exists():
            for item in self.templates_dir.iterdir():
                if item.is_dir():
                    templates.append(item.name)
        return templates if templates else ["Macuare_Estudio"]

    def dibujar_addons_dinamicos(self, version_seleccionada):
        for widget in self.frame_addons.winfo_children():
            widget.destroy()
        self.checkboxes_addons.clear()

        addons_disponibles = self.manifestos_data.get(version_seleccionada, {})

        if not addons_disponibles:
            ctk.CTkLabel(self.frame_addons, text="No hay plugins definidos para esta version.", text_color="gray").pack()
            return

        for nombre_addon, datos in addons_disponibles.items():
            version_addon = datos.get("version", "1.0")
            es_obligatorio = datos.get("mandatory", False)
            descripcion = datos.get("description", "")

            var = ctk.StringVar(value=version_addon if es_obligatorio else "")
            texto_label = f"{nombre_addon} v{version_addon} - {descripcion}"
            
            cb = ctk.CTkCheckBox(self.frame_addons, text=texto_label, variable=var, onvalue=version_addon, offvalue="")
            cb.pack(pady=5, anchor="w")

            if es_obligatorio:
                cb.select()
                cb.configure(state="disabled")

            self.checkboxes_addons[nombre_addon] = var

    def ejecutar_creacion(self):
        nombre = self.entry_nombre.get().strip()
        template = self.combo_template.get().strip()
        version = self.combo_version.get().strip()

        if not nombre:
            self.lbl_status.configure(text="El nombre es obligatorio.", text_color="red")
            return

        dependencias_finales = {}
        for nombre_addon, var in self.checkboxes_addons.items():
            if var.get():
                dependencias_finales[nombre_addon] = var.get()

        self.btn_crear.configure(state="disabled", text="Creando...")
        self.lbl_status.configure(text="Generando estructura en Nextcloud...", text_color="yellow")

        exito, mensaje = self.builder.create_project(nombre, version, dependencias_finales, template, self.ruta_splash)

        if exito:
            self.lbl_status.configure(text=mensaje, text_color="green")
            self.on_success()
            self.after(1500, self.destroy)
        else:
            self.btn_crear.configure(state="normal", text="Generar Proyecto")
            self.lbl_status.configure(text=mensaje, text_color="red")
