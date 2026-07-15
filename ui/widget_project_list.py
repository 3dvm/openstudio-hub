# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_project_list.py
# Rol Arquitectónico: UI Component / JIT Interceptor / Artist Dashboard
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.5.8
# =========================================================================================

"""
Componente del panel del artista que sincroniza dinámicamente las tareas asignadas.
Actúa como un Controlador MVC: Renderiza pestañas de filtrado (Tabs) por proyecto,
instancia las tarjetas modulares (TaskCard) y orquesta el ciclo de vida de Blender.
"""

import json
import threading
import customtkinter as ctk
from pathlib import Path

from core.env_launcher import lanzar_blender
from core.local_installer import LocalInstaller
from core.vcs_router import VCSRouter
from ui.window_svn_login import SVNLoginWindow
from ui.components.task_card import TaskCard

# Cambiamos la herencia a CTkFrame para anclar las pestañas en la parte superior
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
        self.current_filter = "All"
        
        # === ESTRUCTURA UI ===
        # 1. Contenedor de Pestañas (Horizontal)
        self.tabs_container = ctk.CTkScrollableFrame(self, orientation="horizontal", height=55, fg_color="transparent")
        self.tabs_container.pack(fill="x", padx=10, pady=(0, 5))
        
        # 2. Etiqueta de cabecera
        self.header_label = ctk.CTkLabel(
            self, text="Your Tasks", font=ctk.CTkFont(size=20, weight="bold"), text_color="#E2E8F0"
        )
        self.header_label.pack(anchor="w", padx=15, pady=(5, 10))
        
        # 3. Contenedor de Tarjetas (Vertical Scrolleable)
        self.cards_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cards_container.pack(fill="both", expand=True)
        
        self.cargar_proyectos()

    # ---------------------------------------------------------
    # FLUJO DE CARGA DE DATOS (ASÍNCRONO)
    # ---------------------------------------------------------

    def cargar_proyectos(self):
        """Inicia el proceso de carga en un hilo secundario para no congelar la UI."""
        for widget in self.cards_container.winfo_children():
            widget.destroy()
            
        self.loading_label = ctk.CTkLabel(
            self.cards_container, text="Sincronizando tareas con la base de datos...", 
            font=ctk.CTkFont(size=14, slant="italic"), text_color="#94A3B8"
        )
        self.loading_label.pack(pady=40)
        
        self.status_callback("Obteniendo tareas asignadas desde Kitsu...", "white")
        threading.Thread(target=self._hilo_cargar_datos, daemon=True).start()

    def _hilo_cargar_datos(self):
        """Hilo secundario que consulta la API y mapea los proyectos locales."""
        tasks = self.auth_manager.get_assigned_tasks()
        
        local_projects_map = {}
        if self.nextcloud_dir.exists():
            for carpeta in self.nextcloud_dir.iterdir():
                if carpeta.is_dir():
                    init_path = carpeta / "05_config_estudio" / "project_init.json"
                    if init_path.exists():
                        try:
                            with open(init_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            nombre = data.get("project_name", carpeta.name)
                            local_projects_map[nombre.lower()] = carpeta
                        except Exception:
                            pass
                            
        self.after(0, self._almacenar_y_renderizar, tasks, local_projects_map)

    def _almacenar_y_renderizar(self, tasks: list, local_projects_map: dict):
        """Guarda los datos en el estado del componente y detona el dibujo."""
        if hasattr(self, 'loading_label'):
            self.loading_label.destroy()
            
        self.all_tasks = tasks
        self.local_projects_map = local_projects_map
        
        # Validar si el filtro actual sigue existiendo (por si se cerró un proyecto en Kitsu)
        active_projects = {t.get("project_name", "Unknown Project") for t in tasks}
        if self.current_filter != "All" and self.current_filter not in active_projects:
            self.current_filter = "All"

        self._render_tabs()
        self._render_tasks()

    # ---------------------------------------------------------
    # RENDERIZADO DE PESTAÑAS (TABS)
    # ---------------------------------------------------------

    def _render_tabs(self):
        """Construye los botones de filtrado (píldoras) en la parte superior."""
        for widget in self.tabs_container.winfo_children():
            widget.destroy()

        if not self.all_tasks:
            # Ocultar contenedor de tabs si no hay tareas
            self.tabs_container.pack_forget() 
            return
        else:
            # Asegurar que esté visible
            self.tabs_container.pack(fill="x", padx=10, pady=(0, 5), before=self.header_label)

        # Contar tareas por proyecto
        project_counts = {}
        for t in self.all_tasks:
            p_name = t.get("project_name", "Unknown Project")
            project_counts[p_name] = project_counts.get(p_name, 0) + 1

        # Tab "All Projects"
        self._crear_tab_btn("All", len(self.all_tasks))

        # Tabs individuales por proyecto
        for p_name, count in project_counts.items():
            self._crear_tab_btn(p_name, count)

    def _crear_tab_btn(self, name: str, count: int):
        is_active = (self.current_filter == name)

        # Estilo AAA: Verde resaltado si está activo, Gris oscuro si está inactivo
        fg_color = "#064E3B" if is_active else "#1E293B"
        border_color = "#10B981" if is_active else "#334155"
        text_color = "#10B981" if is_active else "#94A3B8"
        hover_color = "#047857" if is_active else "#334155"

        btn_text = f"All Projects  {count}" if name == "All" else f"{name}  {count}"

        btn = ctk.CTkButton(
            self.tabs_container, text=btn_text, fg_color=fg_color,
            border_width=1, border_color=border_color, text_color=text_color,
            hover_color=hover_color, corner_radius=20, height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda n=name: self._seleccionar_tab(n)
        )
        btn.pack(side="left", padx=5)

    def _seleccionar_tab(self, name: str):
        """Callback al hacer clic en una pestaña."""
        self.current_filter = name
        self._render_tabs()   # Redibujar para actualizar colores (Glow)
        self._render_tasks()  # Redibujar tarjetas filtradas

    # ---------------------------------------------------------
    # RENDERIZADO DE TARJETAS (CARDS)
    # ---------------------------------------------------------

    def _render_tasks(self):
        """Filtra y dibuja las tarjetas correspondientes."""
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

        # Aplicar el filtro seleccionado
        filtered_tasks = [
            t for t in self.all_tasks 
            if self.current_filter == "All" or t.get("project_name") == self.current_filter
        ]

        for task in filtered_tasks:
            proyecto_nombre = task["project_name"]
            project_root = self.local_projects_map.get(proyecto_nombre.lower())
            
            esta_instalado = False
            if project_root:
                esta_instalado = self.installer.verificar_instalacion(project_root)
                
            tarjeta = TaskCard(
                parent=self.cards_container,
                task_data=task,
                project_root=project_root,
                is_installed=esta_instalado,
                auth_manager=self.auth_manager,
                on_launch_callback=self.iniciar_proyecto_hilo,
                on_install_callback=self.ejecutar_instalacion_hilo
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

        svn_user, svn_pwd = self.vault.get_svn_credentials()
        kitsu_user, kitsu_pwd = self.vault.get_kitsu_credentials()
        kitsu_host = self.auth_manager.kitsu_host
        user_role = self.auth_manager.get_user_role()

        task_type = task_data.get("task_type_name", "unknown")

        threading.Thread(
            target=self._hilo_ejecucion_blender, 
            args=(project_root, config_path, svn_user, svn_pwd, kitsu_user, kitsu_pwd, kitsu_host, user_role, task_type), 
            daemon=True
        ).start()

    def _hilo_ejecucion_blender(self, project_root, config_path, svn_user, svn_pwd, kitsu_user, kitsu_pwd, kitsu_host, user_role, task_type):
        adapter = None
        ruta_bloqueo = "edit/master_edit.blend"
        
        try:
            self.status_callback("Saneando repositorio local...", "yellow")
            vcs_type = self.config_factory.get_vcs_adapter_type()
            base_url = self.config_factory.get_vcs_repository_url()
            repo_url = f"{base_url}/{project_root.name}/02_archivos_de_produccion"
            workspace = project_root / "02_archivos_de_produccion"
            
            router = VCSRouter(vcs_type=vcs_type, repo_url=repo_url, workspace_dir=workspace)
            adapter = router.get_adapter()
            adapter.cleanup()
        except Exception as e:
            print(f"[CLEANUP WARNING] No se pudo ejecutar el saneamiento automático: {e}")

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

        app_root = self.winfo_toplevel()
        if hasattr(app_root, "registrar_instancia"):
            app_root.registrar_instancia(activa=True)

        try:
            lanzar_blender(project_root, config_path, svn_user, svn_pwd, kitsu_user, kitsu_pwd, kitsu_host, user_role, task_type, self.status_callback)
        except Exception as e:
            self.status_callback(f"Error crítico al ejecutar Blender: {str(e)}", "red")
        finally:
            if hasattr(app_root, "registrar_instancia"):
                app_root.registrar_instancia(activa=False)

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
