import os
import json
import subprocess
import shutil
from pathlib import Path


def lanzar_blender(project_root: Path, config_path: Path, svn_user: str, svn_pwd: str, 
                   kitsu_user: str, kitsu_pwd: str, kitsu_host: str, user_role: str, task_type: str, status_callback):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
                adn = json.load(f)

        template_name = adn.get("template", "Macuare_Estudio")

        if "version_locking" in adn:
            version = adn["version_locking"]["blender_version"]
        else:
            version = adn.get("blender_version", "5.1.2")

        status_callback(f"Buscando Blender {version}...", "yellow")

        # 1. Buscar en boveda global
        boveda_blender = Path.home() / "Nextcloud" / "Macuare-Estudio-Archivos" / "04_BIBLIOTECA_ASSETS" / "blender_versions"
        blender_folder = boveda_blender / f"blender-{version}-linux-x64"
        blender_bin = blender_folder / "blender"

        # 2. Buscar localmente en el proyecto si no esta en boveda (Ej. Aether X)
        if not blender_bin.exists():
            blender_bin = project_root / "06_conf_LOCAL" / "blender-build" / f"blender-{version}-linux-x64" / "blender"

        if not blender_bin.exists():
            raise FileNotFoundError(f"No se encontro el ejecutable para Blender {version}")

        status_callback("Preparando variables de entorno...", "yellow")

        env = os.environ.copy()
        env["OPENSTUDIO_PROJECT_CONFIG"] = str(config_path)

        # Configurar Variables de Entorno OS del contexto de producción
        env["OPENSTUDIO_PROJECT_ROOT"] = str(project_root)
        env["OPENSTUDIO_USER_ROLE"] = user_role
        env["OPENSTUDIO_TASK_TYPE"] = task_type
        
        # Inyección de Kitsu (Zero-Disk Passwords: En crudo solo para el subproceso temporal)
        env["OPENSTUDIO_KITSU_USER"] = kitsu_user
        env["OPENSTUDIO_KITSU_PWD"] = kitsu_pwd
        env["OPENSTUDIO_KITSU_HOST"] = kitsu_host

        # Override de directorios de Blender (Sandboxing)
        sandbox_dir = project_root / "06_conf_LOCAL" / "blender_data"
        sandbox_dir.mkdir(parents=True, exist_ok=True)

        env["BLENDER_USER_RESOURCES"] = str(sandbox_dir)
        env["BLENDER_USER_CONFIG"] = str(sandbox_dir / "config")
        env["BLENDER_USER_SCRIPTS"] = str(sandbox_dir / "scripts")

        env["OPENSTUDIO_SVN_USER"] = svn_user
        env["OPENSTUDIO_SVN_PASSWORD"] = svn_pwd

        # 2. Preparar el script bootstrap
        bootstrap_src = Path(__file__).parent / "templates" / "bootstrap.py"
        bootstrap_dst = project_root / "06_conf_LOCAL" / "bootstrap.py"

        bootstrap_dst.parent.mkdir(parents=True, exist_ok=True)
        if bootstrap_src.exists():
            shutil.copy2(bootstrap_src, bootstrap_dst)
        else:
            raise FileNotFoundError("No se encontro core/templates/bootstrap.py")

        status_callback(f"Arrancando {project_root.name} (Contexto: {task_type.upper()})...", "green")

        # 4. Lanzar el subproceso con el template y el script bootstrap
        cmd = [str(blender_bin), "--app-template", template_name, "--python", str(bootstrap_dst)]
        proceso = subprocess.Popen(cmd, env=env)

        status_callback(f"Blender en ejecucion ({project_root.name})...", "#00aaff")

        proceso.wait()

        status_callback(f"Sesion de {project_root.name} terminada.", "green")
    except Exception as e:
        status_callback(f"Error: {str(e)}", "red")
        print(f"Error detallado: {e}")

def _buscar_blender_exe(project_root: Path) -> Path:
    """Busca el binario de Blender dentro de 06_conf_LOCAL."""
    build_dir = project_root / "06_conf_LOCAL" / "blender-build"
    # Lógica de búsqueda simple (ajustar según tu OS)
    for exe in build_dir.rglob("blender*"):
        if exe.is_file() and os.access(exe, os.X_OK):
            return exe
    # Fallback si no está contenido
import json
import threading
import customtkinter as ctk
from pathlib import Path
from core.env_launcher import lanzar_blender
from core.local_installer import LocalInstaller
from ui.window_svn_login import SVNLoginWindow

class ProjectListWidget(ctk.CTkScrollableFrame):
    def __init__(self, parent, nextcloud_dir, auth_manager, vault_manager, status_callback, **kwargs):
        """
        Componente reutilizable que escanea, verifica el estado de instalacion
        y despliega la lista de proyectos con acciones contextuales (Instalar o Abrir).
        También verifica las credenciales en RAM antes de proceder.
        """
        super().__init__(parent, **kwargs)
        self.nextcloud_dir = nextcloud_dir
        
        # === INYECCION DE DEPENDENCIAS ===
        self.auth_manager = auth_manager
        self.vault = vault_manager
        self.status_callback = status_callback
        
        # Inicializamos el motor de instalacion local
        self.installer = LocalInstaller(nextcloud_dir)
        
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
                        # Leemos el JSON antiguo para extraer el nombre y la version
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
        dialog = ctk.CTkInputDialog(text="Ingrese el Tipo de Tarea\n(ej. animation, rigging, lookdev):", title="Context-Aware Tooling")
        task_type = dialog.get_input()
        
        if not task_type:
            self.status_callback("Lanzamiento cancelado por el usuario.", "red")
            return

        self.status_callback("Iniciando entorno aislado...", "yellow")

        # Lanzamos el hilo inyectando TODAS las credenciales (en crudo) para que el bootstrap las procese
        threading.Thread(
            target=lanzar_blender, 
            args=(project_root, config_path, svn_user, svn_pwd, kitsu_user, kitsu_pwd, kitsu_host, user_role, task_type, self.status_callback), 
            daemon=True
        ).start()

    def ejecutar_instalacion_hilo(self, project_root: Path):
        # === INTERCEPTOR JIT PARA INSTALAR ===
        if not self.vault.has_svn_credentials():
            SVNLoginWindow(
                parent=self.winfo_toplevel(),
                vault_manager=self.vault,
                on_success_callback=lambda: self.ejecutar_instalacion_hilo(project_root)
            )
            return

        threading.Thread(
            target=self._hilo_instalacion, 
            args=(project_root,), 
            daemon=True
        ).start()

    def _hilo_instalacion(self, project_root: Path):
        # Extraemos las claves de la RAM para que el motor haga el checkout silencioso
        svn_user, svn_pwd = self.vault.get_svn_credentials()
        
        exito, mensaje = self.installer.instalar_entorno(project_root, svn_user, svn_pwd, self.status_callback)
        
        if exito:
            self.status_callback(mensaje, "green")
            self.after(500, self.cargar_proyectos)
        else:
            self.status_callback(mensaje, "red")
