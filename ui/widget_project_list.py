# =========================================================================================
# OPENSTUDIOHUB
# Módulo: ui/widget_project_list.py
# Rol Arquitectónico: UI Component / JIT Interceptor
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.4.4
# =========================================================================================

"""
Componente reutilizable que escanea y despliega la lista de proyectos.
Verifica el estado de instalación y las credenciales en RAM antes de proceder,
actuando como el interceptor Just-In-Time (JIT) principal de la interfaz.
Integra la política de "Paso del Testigo" (Lock Passing) para archivos críticos
y el motor asíncrono de auto-recuperación ante caídas físicas (Crash Recovery).
"""

import json
import threading
import customtkinter as ctk
from pathlib import Path
from core.env_launcher import lanzar_blender
from core.local_installer import LocalInstaller
from core.vcs_router import VCSRouter
from ui.window_svn_login import SVNLoginWindow

class ProjectListWidget(ctk.CTkScrollableFrame):
    def __init__(self, parent, nextcloud_dir: Path, auth_manager, vault_manager, config_factory, status_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.nextcloud_dir = nextcloud_dir
        
        # === INYECCION DE DEPENDENCIAS ===
        self.auth_manager = auth_manager
        self.vault = vault_manager
        self.config_factory = config_factory
        self.status_callback = status_callback
        
        # Inicializamos el motor de instalacion local inyectándole el factory
        self.installer = LocalInstaller(nextcloud_dir, config_factory)
        
        self.cargar_proyectos()

    def limpiar_lista(self):
        """Borra todos los widgets internos para poder refrescar la lista de forma limpia."""
        for widget in self.winfo_children():
            widget.destroy()

    def cargar_proyectos(self):
        self.limpiar_lista()
        proyectos_encontrados = 0
        
        if self.nextcloud_dir.exists():
            for carpeta in self.nextcloud_dir.iterdir():
                if carpeta.is_dir():
                    # La semilla global ahora vive en 05_config_estudio
                    init_path = carpeta / "05_config_estudio" / "project_init.json"
                    
                    # Soporte para proyectos antiguos (Legacy) creados con scripts anteriores
                    config_legacy_path = carpeta / "06_conf_LOCAL" / "project_config.json"
                    
                    if init_path.exists():
                        self.procesar_proyecto_hub(carpeta, init_path)
                        proyectos_encontrados += 1
                    elif config_legacy_path.exists():
                        # Proyecto antiguo pre-Hub: se asume ya instalado y listo para abrir
                        with open(config_legacy_path, 'r', encoding='utf-8') as f:
                            data_legacy = json.load(f)
                        
                        nombre_legacy = data_legacy.get("project_name", carpeta.name)
                        version_legacy = data_legacy.get("blender_version", "??")
                        
                        self.crear_boton_abrir(carpeta, config_legacy_path, f"{nombre_legacy} [Blender {version_legacy}]")
                        proyectos_encontrados += 1

        if proyectos_encontrados == 0:
            self.status_callback("No se encontraron proyectos activos sincronizados.", "gray")
        else:
            self.status_callback(f"Sincronizacion completada. Total de proyectos: {proyectos_encontrados}", "white")

    def procesar_proyecto_hub(self, project_root: Path, init_path: Path):
        """Determina dinamicamente si el proyecto necesita instalacion o si ya puede abrirse."""
        with open(init_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        nombre = data.get("project_name", project_root.name)
        version = data.get("blender_version", "??")
        
        # Comprobar si el artista ya configuro su entorno local en esta PC
        esta_instalado = self.installer.verificar_instalacion(project_root)
        
        if esta_instalado:
            config_local_path = project_root / "06_conf_LOCAL" / "project_config.json"
            self.crear_boton_abrir(project_root, config_local_path, f"{nombre} [Blender {version}]")
        else:
            self.crear_boton_instalar(project_root, f"{nombre} [Requiere Configuracion]")

    def crear_boton_abrir(self, project_root: Path, config_path: Path, label_text: str):
        """Genera un boton para lanzar directamente el entorno aislado de Blender."""
        btn = ctk.CTkButton(
            self, 
            text=f"Abrir: {label_text}", 
            font=ctk.CTkFont(size=13),
            height=40,
            command=lambda: self.iniciar_proyecto_hilo(project_root, config_path)
        )
        btn.pack(pady=5, fill="x", padx=10)

    def crear_boton_instalar(self, project_root: Path, label_text: str):
        """Genera un boton contextual llamativo para desplegar la instalacion local."""
        btn = ctk.CTkButton(
            self, 
            text=f"Instalar: {label_text}", 
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#D97706",      # Color ambar/naranja corporativo sobrio y limpio
            hover_color="#B45309",
            height=40,
            command=lambda: self.ejecutar_instalacion_hilo(project_root)
        )
        btn.pack(pady=5, fill="x", padx=10)

    def iniciar_proyecto_hilo(self, project_root: Path, config_path: Path):
        # === INTERCEPTOR JIT PARA ABRIR ===
        if not self.vault.has_svn_credentials():
            self.status_callback("Esperando credenciales de repositorio...", "yellow")
            self.update_idletasks() # FIX: Forzar renderizado antes de secuestrar el hilo con la modal
            
            SVNLoginWindow(
                parent=self.winfo_toplevel(),
                vault_manager=self.vault,
                on_success_callback=lambda: self.iniciar_proyecto_hilo(project_root, config_path)
            )
            return

        # Extraemos credenciales de SVN y Kitsu de forma segura desde la memoria RAM
        svn_user, svn_pwd = self.vault.get_svn_credentials()
        kitsu_user, kitsu_pwd = self.vault.get_kitsu_credentials()
        
        # Obtenemos metadatos desde el AuthManager
        kitsu_host = self.auth_manager.kitsu_host
        user_role = self.auth_manager.get_user_role()

        # Input interactivo temporal para capturar el TaskType
        dialog = ctk.CTkInputDialog(text="Ingrese el Tipo de Tarea\n(ej. animation, edit, rigging):", title="Context-Aware Tooling")
        task_type = dialog.get_input()
        
        if not task_type:
            self.status_callback("Lanzamiento cancelado por el usuario.", "red")
            return

        # Despachamos el ciclo de vida del DCC a un hilo secundario dedicado
        threading.Thread(
            target=self._hilo_ejecucion_blender, 
            args=(project_root, config_path, svn_user, svn_pwd, kitsu_user, kitsu_pwd, kitsu_host, user_role, task_type), 
            daemon=True
        ).start()

    def _hilo_ejecucion_blender(self, project_root, config_path, svn_user, svn_pwd, kitsu_user, kitsu_pwd, kitsu_host, user_role, task_type):
        """
        Orquesta el ciclo de vida completo del software 3D.
        Implementa la política del Testigo (Lock Passing) interceptando la apertura y cierre.
        Sanea de manera automática el repositorio local (Crash Recovery) en cada inicio.
        """
        adapter = None
        # FIX v0.4.4: Apuntar al archivo maestro, no al directorio.
        ruta_bloqueo = "edit/master_edit.blend"
        
        # === PRE-FLIGHT: SANEAMIENTO PREVENTIVO (Crash Recovery) ===
        try:
            self.status_callback("Saneando repositorio local...", "yellow")
            vcs_type = self.config_factory.get_vcs_adapter_type()
            base_url = self.config_factory.get_vcs_repository_url()
            repo_url = f"{base_url}/{project_root.name}/02_archivos_de_produccion"
            workspace = project_root / "02_archivos_de_produccion"
            
            router = VCSRouter(vcs_type=vcs_type, repo_url=repo_url, workspace_dir=workspace)
            adapter = router.get_adapter()
            
            # Limpia bloqueos SQLite locales provocados por apagones abruptos de la PC
            adapter.cleanup()
            
        except Exception as e:
            print(f"[CLEANUP WARNING] No se pudo ejecutar el saneamiento automático: {e}")

        # Evaluamos si la tarea requiere bloqueo estricto (Departamento Editorial)
        requiere_bloqueo = task_type.lower() in ["edit", "editorial", "montaje"]
        
        # Evaluamos la matriz de autorizaciones RBAC
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
                    # ANALISIS DE EXCEPCION: Bypass de seguridad
                    err_msg = str(e).lower()
                    if "already locked" in err_msg and svn_user.lower() in err_msg:
                        print("[LOCK CRASH RECOVERY] El archivo ya estaba bloqueado por ti. Recuperando sesión.")
                        self.status_callback("Sesión recuperada: El testigo ya pertenece a tu usuario.", "green")
                    elif "was not found" in err_msg or "e155010" in err_msg or "unversioned" in err_msg or "e155008" in err_msg:
                        print(f"[LOCK NEW FILE] Nodo no versionado o nuevo. Omitiendo bloqueo inicial. (Detalle: {e})")
                        self.status_callback("Archivo nuevo detectado. Omitiendo bloqueo inicial.", "green")
                    else:
                        print(f"[LOCK ERROR FATAL] {e}")
                        self.status_callback("Acceso denegado: El archivo está en uso por otro artista.", "red")
                        return # Interrumpimos el flujo: Prohibido abrir si no obtenemos el testigo
            else:
                self.status_callback("Aviso: Modo Solo Lectura (No posees cargo de Editor).", "yellow")
        else:
            self.status_callback("Iniciando entorno aislado...", "yellow")

        # Notificamos a la aplicación raíz que un entorno DCC está a punto de abrirse
        app_root = self.winfo_toplevel()
        if hasattr(app_root, "registrar_instancia"):
            app_root.registrar_instancia(activa=True)

        # Lanzar el proceso bloqueante de Blender
        try:
            lanzar_blender(project_root, config_path, svn_user, svn_pwd, kitsu_user, kitsu_pwd, kitsu_host, user_role, task_type, self.status_callback)
        except Exception as e:
            self.status_callback(f"Error crítico al ejecutar Blender: {str(e)}", "red")
        finally:
            # Notificamos a la aplicación raíz que el entorno DCC se ha cerrado
            if hasattr(app_root, "registrar_instancia"):
                app_root.registrar_instancia(activa=False)

        # === POST-FLIGHT: Liberación obligatoria del recurso ===
        if adapter and requiere_bloqueo and esta_autorizado:
            self.status_callback("Liberando testigo de edición (SVN Unlock)...", "yellow")
            try:
                adapter.unlock(path=ruta_bloqueo, username=svn_user, password=svn_pwd)
                self.status_callback("Testigo liberado con éxito. Sesión finalizada.", "green")
            except Exception as e:
                err_msg = str(e).lower()
                if "was not found" in err_msg or "not locked" in err_msg or "e155010" in err_msg or "e155008" in err_msg:
                    print("[UNLOCK INFO] Archivo no estaba bloqueado o es nuevo.")
                    self.status_callback("Sesión finalizada. (Archivo nuevo o sin bloqueo)", "green")
                else:
                    print(f"[UNLOCK ERROR FATAL] {e}")
                    self.status_callback("Advertencia: No se pudo liberar el archivo automáticamente en el servidor.", "red")

    def ejecutar_instalacion_hilo(self, project_root: Path):
        # === INTERCEPTOR JIT PARA INSTALAR ===
        if not self.vault.has_svn_credentials():
            self.status_callback("Esperando credenciales de repositorio...", "yellow")
            self.update_idletasks() # FIX: Forzar renderizado antes de secuestrar el hilo con la modal
            
            SVNLoginWindow(
                parent=self.winfo_toplevel(),
                vault_manager=self.vault,
                on_success_callback=lambda: self.ejecutar_instalacion_hilo(project_root)
            )
            return
            
        # Extraemos el rol dinámicamente antes de lanzar la descarga
        user_role = self.auth_manager.get_user_role()
        task_metadata = None
        
        # === JIT INTERCEPTOR PARA VENDORS (Traducción de Tarea) ===
        if user_role == "vendor":
            dialog = ctk.CTkInputDialog(text="[Vendor Jailing] Ingrese el ID de su Tarea en Kitsu:", title="Validación Sparse")
            task_id = dialog.get_input()
            
            if not task_id:
                self.status_callback("Instalación cancelada por el usuario.", "red")
                return
                
            self.status_callback("Consultando jerarquía de tarea en Kitsu...", "yellow")
            self.update_idletasks()
            
            task_metadata = self.auth_manager.get_task_metadata(task_id)
            if not task_metadata:
                self.status_callback("Error: Tarea no encontrada o metadatos incompletos.", "red")
                return

        # Despachamos el hilo pasando el contexto completo
        threading.Thread(
            target=self._hilo_instalacion, 
            args=(project_root, user_role, task_metadata), 
            daemon=True
        ).start()

    def _hilo_instalacion(self, project_root: Path, user_role: str, task_metadata: dict):
        # Extraemos las claves de la RAM para que el motor haga el checkout silencioso
        svn_user, svn_pwd = self.vault.get_svn_credentials()
        
        exito, mensaje = self.installer.instalar_entorno(
            project_root, svn_user, svn_pwd, self.status_callback,
            user_role=user_role, task_metadata=task_metadata
        )
        
        if exito:
            self.status_callback(mensaje, "green")
            self.after(500, self.cargar_proyectos)
        else:
            self.status_callback(mensaje, "red")
            # Issue 4: Sincronización asíncrona fallida. Purgamos de inmediato la RAM 
            # para obligar a la interfaz a desplegar de nuevo el modal JIT en el próximo intento.
            self.vault.clear()
