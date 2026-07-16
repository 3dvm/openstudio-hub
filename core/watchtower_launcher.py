# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/watchtower_launcher.py
# Rol Arquitectónico: Subprocess Orchestrator / Ephemeral Web Server
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.6.5
# =========================================================================================

"""
Orquestador encargado de la integración de Watchtower (Visualización de Producción).
Extrae datos desde Kitsu, compila el cliente web mediante watchtower-pipeline 
y sirve los archivos JSON generados a través de un servidor HTTP local efímero 
en el navegador predeterminado del usuario.
"""

import os
import sys
import time
import socket
import threading
import subprocess
import webbrowser
import http.server
import socketserver
from pathlib import Path

class WatchtowerLauncher:
    def __init__(self, project_root: Path, kitsu_host: str, kitsu_user: str, kitsu_pwd: str, status_callback):
        self.project_root = project_root
        self.kitsu_host = kitsu_host
        self.kitsu_user = kitsu_user
        self.kitsu_pwd = kitsu_pwd
        self.status_callback = status_callback
        
        self.server_thread = None
        self.httpd = None

    def launch(self):
        """Inicia la extracción y el servidor en un hilo secundario."""
        threading.Thread(target=self._run_pipeline_and_serve, daemon=True).start()

    def _get_free_port(self) -> int:
        """Encuentra un puerto libre en el sistema operativo para evitar colisiones."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def _run_pipeline_and_serve(self):
        # 1. Preparar directorio de trabajo aislado
        wt_dir = self.project_root / "06_conf_LOCAL" / "watchtower_build"
        wt_dir.mkdir(parents=True, exist_ok=True)

        self.status_callback("Watchtower: Extrayendo datos desde la API de Kitsu...", "yellow")

        # 2. Inyectar Credenciales JIT (Zero-Disk) en el subproceso
        env = os.environ.copy()
        env["KITSU_DATA_SOURCE_URL"] = f"{self.kitsu_host}/api"
        env["KITSU_DATA_SOURCE_USER_EMAIL"] = self.kitsu_user
        env["KITSU_DATA_SOURCE_USER_PASSWORD"] = self.kitsu_pwd

        # 3. Ejecutar el compilador (watchtower_pipeline.kitsu -b)
        try:
            cmd = [sys.executable, "-m", "watchtower_pipeline.kitsu", "-b"]
            # Redirigimos el CWD al directorio temporal
            result = subprocess.run(cmd, cwd=str(wt_dir), env=env, capture_output=True, text=True)

            if result.returncode != 0:
                self.status_callback("Watchtower: Error al procesar datos de Kitsu.", "red")
                print(f"[WATCHTOWER ERROR]\n{result.stderr}")
                return

            self.status_callback("Watchtower: Datos procesados. Iniciando servidor local...", "yellow")

            # 4. Iniciar el servidor local apuntando al bundle generado
            serve_dir = wt_dir / "watchtower"
            if not serve_dir.exists():
                serve_dir = wt_dir # Fallback en caso de que la API de watchtower cambie

            self._start_ephemeral_server(serve_dir)

        except Exception as e:
            self.status_callback(f"Watchtower: Fallo crítico en subproceso: {e}", "red")

    def _start_ephemeral_server(self, serve_dir: Path):
        """Levanta un SimpleHTTPRequestHandler y abre el navegador del OS."""
        if self.httpd:
            self.status_callback("Watchtower ya se encuentra en ejecución.", "green")
            return 

        port = self._get_free_port()
        
        # Redirigir la ruta al directorio estático
        os.chdir(str(serve_dir))
        
        Handler = http.server.SimpleHTTPRequestHandler

        class DualStackServer(socketserver.ThreadingTCPServer):
            allow_reuse_address = True

        try:
            self.httpd = DualStackServer(("", port), Handler)
            
            # Lanzamos el servidor de forma asíncrona
            self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.server_thread.start()

            self.status_callback(f"Watchtower activo en puerto {port}", "green")
            
            # Damos un pequeño respiro al socket antes de abrir el navegador
            time.sleep(1.0)
            webbrowser.open(f"http://localhost:{port}")

        except OSError as e:
            self.status_callback(f"Watchtower: Fallo al enlazar el servidor local: {e}", "red")
