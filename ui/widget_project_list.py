# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_project_list.py
# Rol Arquitectónico: UI Component / JIT Interceptor / Artist Dashboard
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.6.0
# =========================================================================================

"""
Componente del panel del artista que sincroniza dinámicamente las tareas asignadas.
Actúa como un Controlador MVC: Renderiza una barra lateral de filtrado por proyecto,
instancia las tarjetas modulares (TaskCard) y orquesta el ciclo de vida de Blender.
Implementa validación bidireccional (SSoT) contra Kitsu.
"""

import json
import threading
import time
import customtkinter as ctk
from pathlib import Path

from core.env_launcher import lanzar_blender
from core.local_installer import LocalInstaller
from core.vcs_router import VCSRouter
from core.path_resolver import PathResolver
from ui.window_svn_login import SVNLoginWindow
from ui.components.task_card import TaskCard

class ProjectListWidget(ctk.CTkFrame):
    def __init__(self, parent, nextcloud_dir: Path, auth_manager, vault_manager, config_factory, status_callback, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.nextcloud_dir = nextcloud_dir
        
        # === INYECCIÓN DE DEPENDENCIAS ===
        self.auth_manager = auth_manager
        self.vault = vault_manager
        self.config_factory = config_factory
        self.status_callback = status_callback
        
        self.installer = LocalInstaller(nextcloud_dir, config_factory)
        
        # === ESTADO DEL COMPONENTE ===
        self.all_tasks = []
        self.local_projects_map = {}
        self.active_kitsu_projects = {} # Mapeo SSoT {nombre: uuid}
        self.current_filter = "All"
        self._last_refresh_time = 0
        
        # === ESTRUCTURA UI (GRID LAYOUT) ===
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0) # Columna 0: Barra Lateral (Filtros)
        self.grid_columnconfigure(1, weight=1) # Columna 1: Contenido Principal (Tarjetas)
        
        # 1. Contenedor Lateral Izquierdo (Sidebar de Proyectos)
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=8, fg_color="#1A1A1A")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 15), pady=5)
        self.sidebar_frame.grid_propagate(False) # Forzar el ancho mínimo
        
        self.lbl_filtros = ctk.CTkLabel(
            self.sidebar_frame, text="📁 MIS PROYECTOS", 
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#94A3B8"
        )
        self.lbl_filtros.pack(pady=(20, 10), padx=15, anchor="w")
        
        self.tabs_container = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.tabs_container.pack(fill="both", expand=True, padx=5, pady=5)

        # 2. Contenedor Principal Derecho
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", pady=5)
        
        # 2.1 Cabecera del Contenedor Principal
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        self.header_label = ctk.CTkLabel(
            self.header_frame, text="Tus Tareas Asignadas", 
            font=ctk.CTkFont(size=20, weight="bold"), text_color="#E2E8F0"
        )
        self.header_label.pack(side="left")
        
        self.refresh_btn = ctk.CTkButton(
            self.header_frame, text="↻ Recargar", width=100, height=28,
            fg_color="transparent", border_width=1, border_color="#334155",
            text_color="#94A3B8", hover_color="#1E293B",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._forzar_recarga
        )
        self.refresh_btn.pack(side="right")
        
        # 2.2 Contenedor de Tarjetas (Vertical Scrolleable)
        self.cards_container = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent")
        self.cards_container.pack(fill="both", expand=True)
        
        self.cargar_proyectos()

    # ---------------------------------------------------------
    # FLUJO DE CARGA DE DATOS (ASÍNCRONO)
    # ---------------------------------------------------------

    def _forzar_recarga(self):
        """Bloquea spam a la API y detona recarga."""
        now = time.time()
        if now - self._last_refresh_time < 3:
            self.status_callback("Espera unos segundos antes de volver a recargar...", "yellow")
            return
            
        self._last_refresh_time = now
        self.status_callback("Sincronización manual forzada.", "white")
        self.cargar_proyectos()

    def cargar_proyectos(self):
        """Inicia el proceso de carga en un hilo secundario para no congelar la UI."""
        for widget in self.cards_container.winfo_children():
            widget.destroy()
            
        self.loading_label = ctk.CTkLabel(
            self.cards_container, text="Sincronizando tareas con la base de datos...", 
            font=ctk.CTkFont(size=14, slant="italic"), text_color="#94A3B8"
        )
        self.loading_label.pack(pady=40)
        
        self.status_callback("Verificando integridad de proyectos contra Kitsu...", "white")
        threading.Thread(target=self._hilo_cargar_datos, daemon=True).start()

    def _hilo_cargar_datos(self):
        """Hilo secundario que consulta la API y mapea los proyectos locales (Validación Bidireccional)."""
        # 1. Obtener SSoT (Single Source of Truth) desde el Servidor
        kitsu_projects_map = self.auth_manager.obtener_proyectos_activos()
        
        # 2. Cargar Tareas del Usuario
        tasks = self.auth_manager.get_assigned_tasks()
        
        # 3. Mapear Proyectos Locales y Contrastar
        local_projects_map = {}
        if self.nextcloud_dir.exists():
            for carpeta in self.nextcloud_dir.iterdir():
                if carpeta.is_dir():
                    init_path = carpeta / "05_config_estudio" / "project_init.json"
                    if init_path.exists():
                        try:
                            with open(init_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            nombre = data.get("project_name", carpeta.name).lower()
                            
                            # Validar que el proyecto local existe y está ACTIVO en Kitsu (Issue 6)
                            if nombre in kitsu_projects_map:
                                local_projects_map[nombre] = carpeta
                            else:
                                print(f"[WARNING] Proyecto local '{nombre}' ignorado (No activo en Kitsu).")
                        except Exception:
                            pass
                            
        self.after(0, self._almacenar_y_renderizar, tasks, local_projects_map, kitsu_projects_map)

    def _almacenar_y_renderizar(self, tasks: list, local_projects_map: dict, kitsu_projects_map: dict):
        """Guarda los datos en el estado del componente y detona el dibujo."""
        if hasattr(self, 'loading_label'):
            self.loading_label.destroy()
            
        self.all_tasks = tasks
        self.local_projects_map = local_projects_map
        self.active_kitsu_projects = kitsu_projects_map
        
        active_projects = {t.get("project_name", "Unknown Project") for t in tasks}
        if self.current_filter != "All" and self.current_filter not in active_projects:
            self.current_filter = "All"

        self._render_tabs()
        self._render_tasks()

    # ---------------------------------------------------------
    # RENDERIZADO DE BARRA LATERAL (TABS VERTICALES)
    # ---------------------------------------------------------

    def _render_tabs(self):
        for widget in self.tabs_container.winfo_children():
            widget.destroy()

        if not self.all_tasks:
            lbl_empty = ctk.CTkLabel(
                self.tabs_container, text="Sin proyectos activos", 
                text_color="#64748B", font=ctk.CTkFont(slant="italic")
            )
            lbl_empty.pack(pady=20)
            return

        project_counts = {}
        for t in self.all_tasks:
            p_name = t.get("project_name", "Unknown Project")
            project_counts[p_name] = project_counts.get(p_name, 0) + 1

        self._crear_tab_btn("All", len(self.all_tasks))

        for p_name, count in project_counts.items():
            self._crear_tab_btn(p_name, count)

    def _crear_tab_btn(self, name: str, count: int):
        is_active = (self.current_filter == name)

        fg_color = "#064E3B" if is_active else "transparent"
        text_color = "#10B981" if is_active else "#94A3B8"
        hover_color = "#047857" if is_active else "#334155"

        btn_text = f"Todas las Tareas ({count})" if name == "All" else f"{name} ({count})"

        btn = ctk.CTkButton(
            self.tabs_container, text=btn_text, fg_color=fg_color,
            text_color=text_color, hover_color=hover_color, corner_radius=6, height=35,
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
            command=lambda n=name: self._seleccionar_tab(n)
        )
        btn.pack(side="top", fill="x", pady=2)

    def _seleccionar_tab(self, name: str):
        self.current_filter = name
        self._render_tabs()   
        self._render_tasks()  

    # ---------------------------------------------------------
    # RENDERIZADO DE TARJETAS (CARDS)
    # ---------------------------------------------------------

    def _render_tasks(self):
        for widget in self.cards_container.winfo_children():
            widget.destroy()

        if not self.all_tasks:
            msg = ctk.CTkLabel(
                self.cards_container, text="No tienes tareas pendientes (TODO/WIP). ¡Buen trabajo!", 
                font=ctk.CTkFont(size=14), text_color="#10B981"
            )
            msg.pack(pady=40)
            self.status_callback("Sincronización completada. Tablero limpio.", "white")
            return

        filtered_tasks = [
            t for t in self.all_tasks 
            if self.current_filter == "All" or t.get("project_name") == self.current_filter
        ]

        resolver = PathResolver()
        user_role = self.auth_manager.get_user_role()
        is_admin = user_role in ["lead", "supervisor", "td", "manager"]
        prod_folder = self.config_factory.get_production_folder_name()

        for task in filtered_tasks:
            proyecto_nombre = task["project_name"].lower()
            project_root = self.local_projects_map.get(proyecto_nombre)
            
            # Reinyectar el UUID verificado desde Kitsu para evitar ambigüedades
            if proyecto_nombre in self.active_kitsu_projects:
                task["project_id"] = self.active_kitsu_projects[proyecto_nombre]
            
            esta_instalado = False
            can_work = True
            blocked_reason = ""

            # Validar existencia de archivo (Fail-Fast Pre-Flight Check)
            if project_root:
                esta_instalado = self.installer.verificar_instalacion(project_root)
                if esta_instalado:
                    try:
                        relative_target = resolver.resolve(task)
                        if relative_target:
                            target_file = project_root / prod_folder / "pro" / relative_target
                            
                            if not target_file.exists() and not is_admin:
                                can_work = False
                                blocked_reason = "Falta archivo (Requiere Setup)"
                    except Exception as e:
                        print(f"[OPENSTUDIO DEBUG] Error interno del PathResolver: {e}")
                        pass
            else:
                # El proyecto no está en el mapa local verificado (Desincronizado)
                can_work = False
                blocked_reason = "Proyecto Desincronizado / Archivado"
                
            tarjeta = TaskCard(
                parent=self.cards_container,
                task_data=task,
                project_root=project_root,
                is_installed=esta_instalado,
                auth_manager=self.auth_manager,
                on_launch_callback=self.iniciar_proyecto_hilo,
                on_install_callback=self.ejecutar_instalacion_hilo,
                can_work=can_work,
                blocked_reason=blocked_reason
            )
            tarjeta.pack(pady=10, padx=15, fill="x")
            
        self.status_callback(f"Tablero filtrado: {len(filtered_tasks)} tareas visibles.", "green")

    # ---------------------------------------------------------
    # INTERCEPTORES Y ORQUESTADORES DE HILOS (LÓGICA CORE)
    # ---------------------------------------------------------

    def iniciar_proyecto_hilo(self, project_root: Path, config_path: Path, task_data: dict):
        if not self.vault.has_svn_credentials():
            self.status_callback("Esperando credenciales de repositorio...", "yellow")
            self.update_idletasks() 
            SVNLoginWindow(
                parent=self.winfo_toplevel(),
                vault_manager=self.vault,
                on_success_callback=lambda: self.iniciar_proyecto_hilo(project_root, config_path, task_data)
            )
            return

        user_role = self.auth_manager.get_user_role()
        prod_folder = self.config_factory.get_production_folder_name()
        target_file = None
        
        # Validación redundante para seguridad
        try:
            resolver = PathResolver()
            relative_target = resolver.resolve(task_data)
            if relative_target:
                target_file = project_root / prod_folder / "pro" / relative_target
                if user_role not in ["lead", "supervisor", "td", "manager"]:
                    if not target_file.exists():
                        self.status_callback("❌ Archivo no encontrado. Solicite al Lead la creación de la toma.", "red")
                        return
        except Exception as e:
            self.status_callback(f"Error interno resolviendo la ruta: {e}", "red")
            return

        svn_user, svn_pwd = self.vault.get_svn_credentials()
        kitsu_user, kitsu_pwd = self.vault.get_kitsu_credentials()
        kitsu_host = self.auth_manager.kitsu_host

        threading.Thread(
            target=self._hilo_ejecucion_blender, 
            args=(project_root, config_path, svn_user, svn_pwd, kitsu_user, kitsu_pwd, kitsu_host, user_role, task_data, target_file, prod_folder), 
            daemon=True
        ).start()

    def _hilo_ejecucion_blender(self, project_root, config_path, svn_user, svn_pwd, kitsu_user, kitsu_pwd, kitsu_host, user_role, task_data, target_file, prod_folder):
        task_type = task_data.get("task_type_name", "unknown")
        adapter = None
        ruta_bloqueo = "edit/master_edit.blend"
        
        # 2. SVN Cleanup
        try:
            self.status_callback("Saneando repositorio local...", "yellow")
            vcs_type = self.config_factory.get_vcs_adapter_type()
            base_url = self.config_factory.get_vcs_repository_url()
            repo_url = f"{base_url}/{project_root.name}/{prod_folder}"
            workspace = project_root / prod_folder
            
            router = VCSRouter(vcs_type=vcs_type, repo_url=repo_url, workspace_dir=workspace)
            adapter = router.get_adapter()
            adapter.cleanup()
        except Exception as e:
            print(f"[CLEANUP WARNING] No se pudo ejecutar el saneamiento automático: {e}")

        # 3. Lock Management
        requiere_bloqueo = task_type.lower() in ["edit", "editorial", "montaje"]
        cargo_usuario = self.auth_manager.get_user_position()
        
        cargos_autorizados = ["editor", "director", "lead"]
        roles_autorizados = ["td", "supervisor", "lead", "manager"]
        esta_autorizado = (user_role in roles_autorizados) or (cargo_usuario in cargos_autorizados)
        
        if requiere_bloqueo:
            if esta_autorizado:
                self.status_callback("Adquiriendo testigo de edición (SVN Lock)...", "yellow")
                try:
                    adapter.lock(path=ruta_bloqueo, username=svn_user, password=svn_pwd)
                    self.status_callback("Testigo adquirido. Lanzando entorno de edición...", "green")
                except Exception as e:
                    err_msg = str(e).lower()
                    if "already locked" in err_msg and svn_user.lower() in err_msg:
                        self.status_callback("Sesión recuperada: El testigo ya pertenece a tu usuario.", "green")
                    elif "was not found" in err_msg or "e155010" in err_msg or "unversioned" in err_msg or "e155008" in err_msg:
                        self.status_callback("Archivo nuevo detectado. Omitiendo bloqueo inicial.", "green")
                    else:
                        self.status_callback("Acceso denegado: El archivo está en uso por otro artista.", "red")
                        return
            else:
                self.status_callback("Aviso: Modo Solo Lectura (No posees cargo de Editor).", "yellow")
        else:
            self.status_callback("Iniciando entorno aislado...", "yellow")

        # 4. Orquestación del GUI e Invocación a env_launcher
        app_root = self.winfo_toplevel()
        if hasattr(app_root, "registrar_instancia"):
            app_root.registrar_instancia(activa=True)

        try:
            lanzar_blender(
                project_root, config_path, svn_user, svn_pwd, 
                kitsu_user, kitsu_pwd, kitsu_host, user_role, 
                task_data, target_file, self.status_callback, 
                production_folder=prod_folder
            )
        except Exception as e:
            self.status_callback(f"Error crítico al ejecutar Blender: {str(e)}", "red")
        finally:
            if hasattr(app_root, "registrar_instancia"):
                app_root.registrar_instancia(activa=False)

        # 5. Lock Release
        if adapter and requiere_bloqueo and esta_autorizado:
            self.status_callback("Liberando testigo de edición (SVN Unlock)...", "yellow")
            try:
                adapter.unlock(path=ruta_bloqueo, username=svn_user, password=svn_pwd)
                self.status_callback("Testigo liberado con éxito. Sesión finalizada.", "green")
            except Exception as e:
                err_msg = str(e).lower()
                if "was not found" in err_msg or "not locked" in err_msg or "e155010" in err_msg or "e155008" in err_msg:
                    self.status_callback("Sesión finalizada. (Archivo nuevo o sin bloqueo)", "green")
                else:
                    self.status_callback("Advertencia: No se pudo liberar el archivo automáticamente en el servidor.", "red")

    def ejecutar_instalacion_hilo(self, project_root: Path, task_data: dict):
        if not self.vault.has_svn_credentials():
            self.status_callback("Esperando credenciales de repositorio...", "yellow")
            self.update_idletasks() 
            SVNLoginWindow(
                parent=self.winfo_toplevel(),
                vault_manager=self.vault,
                on_success_callback=lambda: self.ejecutar_instalacion_hilo(project_root, task_data)
            )
            return
            
        user_role = self.auth_manager.get_user_role()
        
        threading.Thread(
            target=self._hilo_instalacion, 
            args=(project_root, user_role, task_data), 
            daemon=True
        ).start()

    def _hilo_instalacion(self, project_root: Path, user_role: str, task_data: dict):
        svn_user, svn_pwd = self.vault.get_svn_credentials()
        
        task_metadata = None
        if user_role == "vendor":
            task_id = task_data.get("task_id")
            if task_id:
                self.status_callback("Resolviendo grafo de dependencias de la Tarea...", "yellow")
                task_metadata = self.auth_manager.get_task_metadata(task_id)
        
        exito, mensaje = self.installer.instalar_entorno(
            project_root, svn_user, svn_pwd, self.status_callback,
            user_role=user_role, task_metadata=task_metadata
        )
        
        if exito:
            self.status_callback(mensaje, "green")
            self.after(500, self.cargar_proyectos)
        else:
            self.status_callback(mensaje, "red")
            self.vault.clear()
