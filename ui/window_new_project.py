# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/window_new_project.py
# Rol Arquitectónico: UI View / Modal Dialog
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.6.0
# =========================================================================================

import json
import customtkinter as ctk
from customtkinter import filedialog
from pathlib import Path
from core.project_builder import ProjectBuilder

class NewProjectWindow(ctk.CTkToplevel):
    def __init__(self, parent, nextcloud_dir, on_success_callback):
        super().__init__(parent)
        self.title("Nuevo Proyecto")
        self.geometry("500x750")

        self.ruta_splash = ""
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()

        self.builder = ProjectBuilder(nextcloud_dir)
        self.on_success = on_success_callback
        
        # Rutas dinámicas de la bóveda
        self.vault_manifest_path = nextcloud_dir.parent / "04_BIBLIOTECA_ASSETS" / "00_SOFTWARE" / "vault_manifest.json"
        
        self.vault_data = self._cargar_vault_manifest()
        self.checkboxes_herramientas = {}  # {categoria: {nombre: CTkCheckBox}}
        self.vars_herramientas = {}        # {categoria: {nombre: StringVar}}

        # --- DISEÑO DE LA INTERFAZ ---
        lbl_titulo = ctk.CTkLabel(self, text="Configuración Inicial", font=ctk.CTkFont(size=18, weight="bold"))
        lbl_titulo.pack(pady=(20, 10))

        # 1. Nombre
        self.entry_nombre = ctk.CTkEntry(self, placeholder_text="Nombre (ej. p0004-nuevo-proyecto)", width=400)
        self.entry_nombre.pack(pady=10)

        # 2. Selector de Versión de Blender
        lbl_version = ctk.CTkLabel(self, text="Versión de Blender Objetivo:")
        lbl_version.pack(pady=(10, 0))
        
        versiones = list(self.vault_data.keys()) if self.vault_data else ["5.1.2"]
        self.combo_version = ctk.CTkComboBox(
            self, 
            values=versiones, 
            width=400,
            command=self.dibujar_dependencias_dinamicas
        )
        self.combo_version.pack(pady=5)

        # 3. Componentes y Dependencias (Categorizado)
        lbl_addons = ctk.CTkLabel(self, text="Componentes de Bóveda (vault_manifest.json):", font=ctk.CTkFont(weight="bold"))
        lbl_addons.pack(pady=(15, 5), padx=50, anchor="w")
        
        self.frame_addons = ctk.CTkScrollableFrame(self, width=380, height=250)
        self.frame_addons.pack(pady=0, padx=50, fill="x")

        if versiones:
            self.dibujar_dependencias_dinamicas(self.combo_version.get())

        # 4. Splash Screen
        lbl_splash = ctk.CTkLabel(self, text="Splash Screen Personalizado (1000x500px):")
        lbl_splash.pack( pady=(15,0) )

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

        # Feedback y Botón
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

    def _cargar_vault_manifest(self) -> dict:
        """Lee el manifiesto maestro de la bóveda para extraer las categorías y requisitos."""
        data = {}
        if self.vault_manifest_path.exists():
            try:
                with open(self.vault_manifest_path, 'r', encoding='utf-8') as f:
                    manifesto_crudo = json.load(f)
                    # Convertimos a un diccionario {version_blender: categories}
                    for _, bl_version_data in manifesto_crudo.items():
                        version = bl_version_data.get("blender_version")
                        if version:
                            data[version] = bl_version_data.get("categories", {})
            except Exception as e:
                print(f"[UI ERROR] Fallo al parsear vault_manifest: {e}")
        return data

    def dibujar_dependencias_dinamicas(self, version_seleccionada):
        """Renderiza las categorías y herramientas leyendo el manifesto de la bóveda."""
        for widget in self.frame_addons.winfo_children():
            widget.destroy()
        
        self.checkboxes_herramientas.clear()
        self.vars_herramientas.clear()

        categorias_disponibles = self.vault_data.get(version_seleccionada, {})

        if not categorias_disponibles:
            ctk.CTkLabel(self.frame_addons, text="No hay componentes definidos para esta versión.", text_color="gray").pack(pady=20)
            return

        for categoria, items in categorias_disponibles.items():
            # Título de Categoría
            lbl_cat = ctk.CTkLabel(self.frame_addons, text=f"[{categoria.upper()}]", text_color="#10B981", font=ctk.CTkFont(weight="bold"))
            lbl_cat.pack(pady=(10, 2), anchor="w")
            
            self.checkboxes_herramientas[categoria] = {}
            self.vars_herramientas[categoria] = {}

            for nombre_item, datos in items.items():
                version_item = datos.get("version", "1.0")
                es_obligatorio = datos.get("mandatory", False)
                descripcion = datos.get("description", "")
                requires = datos.get("requires", [])

                # Variable que almacena la versión si está activo, vacío si no
                var = ctk.StringVar(value=version_item if es_obligatorio else "")
                texto_label = f"{nombre_item} v{version_item} - {descripcion}"
                
                cb = ctk.CTkCheckBox(
                    self.frame_addons, 
                    text=texto_label, 
                    variable=var, 
                    onvalue=version_item, 
                    offvalue="",
                    command=lambda n=nombre_item, c=categoria, r=requires, v=var: self._resolver_subdependencias(c, n, r, v)
                )
                cb.pack(pady=5, padx=(10, 0), anchor="w")

                if es_obligatorio:
                    cb.select()
                    cb.configure(state="disabled")

                self.checkboxes_herramientas[categoria][nombre_item] = cb
                self.vars_herramientas[categoria][nombre_item] = var

    def _resolver_subdependencias(self, categoria_padre: str, nombre_padre: str, requires: list, var_padre: ctk.StringVar):
        """Auto-selecciona y bloquea dependencias subordinadas si el padre es activado."""
        if not var_padre.get():
            # Si el usuario desmarcó el padre, no hacemos rollback automático para no ser destructivos,
            # pero podríamos desbloquear las subordinadas si queremos. Por ahora solo evaluamos al activar.
            return
            
        for req in requires:
            # req suele venir en formato "categoria/nombre_item"
            partes = req.split("/")
            if len(partes) != 2: continue
            
            cat_req, nom_req = partes[0], partes[1]
            
            if cat_req in self.checkboxes_herramientas and nom_req in self.checkboxes_herramientas[cat_req]:
                cb_sub = self.checkboxes_herramientas[cat_req][nom_req]
                var_sub = self.vars_herramientas[cat_req][nom_req]
                
                # Obtener la versión correcta del sub-item (el onvalue del checkbox)
                version_sub = cb_sub.cget("onvalue")
                
                # Lo encendemos y lo bloqueamos
                var_sub.set(version_sub)
                cb_sub.select()
                cb_sub.configure(state="disabled", text_color="#F59E0B")
                
                # Feedback visual
                print(f"[HUB DEPENDENCY] Auto-seleccionado {nom_req} requerido por {nombre_padre}")

    def ejecutar_creacion(self):
        """Valida, aplana el diccionario de dependencias y delega a ProjectBuilder."""
        nombre = self.entry_nombre.get().strip()
        version_blender = self.combo_version.get().strip()

        # Validación básica de caracteres
        if not nombre:
            self.lbl_status.configure(text="El nombre del proyecto es obligatorio.", text_color="red")
            return
        if not nombre.replace("-", "").replace("_", "").isalnum():
            self.lbl_status.configure(text="Solo caracteres alfanuméricos, guiones o guiones bajos.", text_color="red")
            return

        # Construir el diccionario anidado de dependencias para project_init.json
        dependencias_finales = {}
        template_principal = "Macuare_Estudio" # Fallback por si no eligen nada
        
        for categoria, items in self.vars_herramientas.items():
            dependencias_finales[categoria] = {}
            for nombre_item, var in items.items():
                val = var.get()
                if val:
                    dependencias_finales[categoria][nombre_item] = val
                    # Identificar qué plantilla seleccionó el TD
                    if categoria == "templates":
                        template_principal = nombre_item

        self.btn_crear.configure(state="disabled", text="Creando...")
        self.lbl_status.configure(text="Estructurando directorios y subiendo al servidor...", text_color="yellow")
        self.update_idletasks() # Forzar refresco visual

        # Llamar al Builder
        exito, mensaje = self.builder.create_project(
            project_name=nombre, 
            blender_version=version_blender, 
            dependencies=dependencias_finales, 
            project_template=template_principal, 
            splash_image_path=self.ruta_splash
        )

        # Resolver Callbacks MVC (Issue 4)
        if exito:
            self.lbl_status.configure(text=mensaje, text_color="green")
            self.on_success() # Esto disparará cargar_proyectos() en la ViewTD
            self.after(1500, self.destroy)
        else:
            self.btn_crear.configure(state="normal", text="Generar Proyecto")
            self.lbl_status.configure(text=mensaje, text_color="red")
