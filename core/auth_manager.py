# =========================================================================================
# OPENSTUDIOHUB
# Módulo: core/auth_manager.py
# Rol Arquitectónico: Backend SDK / Autenticación y Contexto (Gazu)
# =========================================================================================
# Copyright (c) 2026 Ernesto Del Valle Macuare. Todos los derechos reservados.
# Licencia: GNU General Public License v3.0 (GPLv3)
#
# Autor: Ernesto Del Valle Macuare
# Versión del archivo: 0.6.0
# =========================================================================================

"""
Gestor de Autenticación y Contexto de Kitsu.
Maneja las sesiones, tokens JWT, resolución de la matriz RBAC,
extracción de metadatos de tareas, y sincronización dinámica 
de la identidad visual del estudio.
"""

import os
import json
import gazu
import requests
from pathlib import Path
from typing import Dict, Tuple, Optional, List

OPENSTUDIO_CONFIG_DIR = Path.home() / ".openstudio"
SESSION_FILE = OPENSTUDIO_CONFIG_DIR / "session.json"
CACHE_DIR = OPENSTUDIO_CONFIG_DIR / "cache"

class AuthManager:
    def __init__(self):
        self.kitsu_host = None
        self.user_data = None
        self.access_token = "" 
        
        if not OPENSTUDIO_CONFIG_DIR.exists():
            OPENSTUDIO_CONFIG_DIR.mkdir(parents=True)
            
        if not CACHE_DIR.exists():
            CACHE_DIR.mkdir(parents=True)

    def set_host(self, host_url: str) -> None:
        if not host_url.endswith("/api"):
            host_url = f"{host_url.rstrip('/')}/api"
        self.kitsu_host = host_url
        gazu.client.set_host(self.kitsu_host)

    def login_with_credentials(self, email: str, password: str, host_url: str) -> Tuple[bool, str]:
        try:
            self.set_host(host_url)
            tokens = gazu.log_in(email, password)
            self.user_data = gazu.client.get_current_user()
            
            if isinstance(tokens, dict):
                self.access_token = tokens.get("access_token", "")
            
            self._save_session(tokens)
            return True, "Login exitoso"
        except gazu.exception.AuthFailedException:
            return False, "Credenciales incorrectas."
        except Exception as e:
            return False, f"Error de conexión: {str(e)}"

    def login_with_saved_session(self) -> bool:
        if not SESSION_FILE.exists():
            return False
        try:
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)
            self.set_host(data["host"])
            gazu.client.set_tokens(data["tokens"])
            self.user_data = gazu.client.get_current_user()
            
            if isinstance(data["tokens"], dict):
                self.access_token = data["tokens"].get("access_token", "")
                
            return True
        except Exception:
            if SESSION_FILE.exists():
                SESSION_FILE.unlink()
            return False

    def logout(self) -> None:
        """Cierra sesión de forma segura y purga el rastro local."""
        if self.access_token and self.kitsu_host:
            try:
                gazu.log_out()
            except Exception as e:
                print(f"[AuthManager] Advertencia al cerrar sesión en el servidor Kitsu: {e}")

        self.user_data = None
        self.access_token = ""
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()

    # ---------------------------------------------------------
    # IDENTIDAD B2B Y SINCRONIZACIÓN
    # ---------------------------------------------------------

    def fetch_studio_identity(self) -> dict:
        """
        Descarga dinámicamente la configuración global del estudio 
        y el avatar del usuario conectado (Issue 5).
        """
        identity = {
            "studio_name": "OPENSTUDIO",
            "avatar_path": None
        }

        if not self.user_data or not self.access_token:
            return identity

        # 1. Recuperar el nombre del estudio desde Gazu
        try:
            studio_profile = gazu.client.get("settings")
            # Gazu Settings a veces devuelve un array o un dict
            if isinstance(studio_profile, list) and len(studio_profile) > 0:
                name = studio_profile[0].get("name")
                if name: identity["studio_name"] = name
            elif isinstance(studio_profile, dict):
                name = studio_profile.get("name")
                if name: identity["studio_name"] = name
        except Exception as e:
            print(f"[AuthManager] Info: No se pudo obtener el nombre del estudio ({e})")

        # 2. Descargar Avatar del Usuario
        avatar_id = self.user_data.get("avatar_id")
        if avatar_id:
            try:
                # Armamos la ruta física usando la URL base y el endpoint de Gazu
                base_url = self.kitsu_host.replace("/api", "")
                avatar_url = f"{base_url}/api/pictures/thumbnails/persons/{avatar_id}.png"
                
                headers = {"Authorization": f"Bearer {self.access_token}"}
                response = requests.get(avatar_url, headers=headers, stream=True, timeout=5)
                
                if response.status_code == 200:
                    local_avatar = CACHE_DIR / f"{avatar_id}.png"
                    with open(local_avatar, "wb") as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    identity["avatar_path"] = str(local_avatar)
            except Exception as e:
                print(f"[AuthManager] Info: No se pudo descargar el avatar ({e})")

        return identity

    def obtener_proyectos_activos(self) -> Dict[str, str]:
        """
        Consulta la API de Gazu para obtener el SSoT de proyectos (Issue 6).
        Retorna un diccionario { "nombre_proyecto_lower": "uuid_proyecto" }
        """
        mapeo = {}
        try:
            proyectos = gazu.project.all_open_projects()
            for p in proyectos:
                nombre = p.get("name", "").lower()
                uuid = p.get("id", "")
                if nombre and uuid:
                    mapeo[nombre] = uuid
        except Exception as e:
            print(f"[AuthManager] Error al consultar proyectos activos: {e}")
        
        return mapeo

    # ---------------------------------------------------------
    # MATRIZ RBAC
    # ---------------------------------------------------------

    def get_user_role(self) -> str:
        if not self.user_data:
            return "guest"
        kitsu_role = self.user_data.get("role", "").lower()
        kitsu_position = self.user_data.get("position", "").lower()
        
        if kitsu_role == "admin": return "td"
        elif kitsu_role == "supervisor": return "supervisor"
        elif kitsu_role == "manager": return "manager"
        elif kitsu_role == "vendor": return "vendor"
        elif kitsu_role == "client": return "client"
        elif kitsu_role == "user":
            if kitsu_position == "lead": return "lead"
            return "artist"
        else: return "artist"

    def get_user_position(self) -> str:
        if not self.user_data:
            return ""
        return self.user_data.get("position", "").lower()

    def get_current_token(self) -> str:
        return self.access_token

    def get_task_metadata(self, task_id: str) -> Optional[Dict[str, str]]:
        try:
            task = gazu.task.get_task(task_id)
            if not task: return None
            entity = gazu.entity.get_entity(task["entity_id"])
            if not entity: return None

            entity_type = entity.get("type", "")
            entity_name = entity.get("name", "")
            
            metadata = {
                "entity_type": entity_type,
                "entity_name": entity_name
            }
            
            if entity_type.lower() == "shot":
                sequence = gazu.shot.get_sequence(entity.get("parent_id"))
                metadata["sequence_name"] = sequence.get("name", "") if sequence else ""
            elif entity_type.lower() == "asset":
                asset_type = gazu.asset.get_asset_type(entity.get("entity_type_id"))
                metadata["asset_type_name"] = asset_type.get("name", "") if asset_type else ""
                
            return metadata
        except Exception as e:
            print(f"[AuthManager] Error extrayendo metadatos de Tarea: {e}")
            return None

    # ---------------------------------------------------------
    # FUNCIONES UI / DASHBOARD
    # ---------------------------------------------------------

    def get_assigned_tasks(self) -> List[dict]:
        if not self.user_data:
            return []
            
        try:
            raw_tasks = gazu.user.all_tasks_to_do()
            formatted_tasks = []
            
            for task in raw_tasks:
                project_name = task.get("project_name", "Unknown Project")
                entity_name = task.get("entity_name", "Unknown Entity")
                task_type_name = task.get("task_type_name", "Unknown Task")
                task_type_id = task.get("task_type_id", "")
                
                # Extracción extra para v0.5.7: Short name del Task Type
                task_type_short_name = ""
                try:
                    task_type_obj = gazu.task.get_task_type(task_type_id)
                    if task_type_obj:
                        task_type_short_name = task_type_obj.get("short_name", "")
                except Exception:
                    pass
                
                status_color = "#444444"
                status_name = "TODO"
                try:
                    status_obj = gazu.task.get_task_status(task.get("task_status_id"))
                    if status_obj:
                        status_color = status_obj.get("color", "#444444")
                        status_name = status_obj.get("name", "TODO")
                except Exception:
                    pass
                    
                preview_id = None
                entity_type = ""
                sequence_id = ""
                sequence_name = ""
                asset_type_id = ""
                asset_type_name = ""
                
                try:
                    entity_obj = gazu.entity.get_entity(task.get("entity_id"))
                    if entity_obj:
                        preview_id = entity_obj.get("preview_file_id")
                        entity_type = entity_obj.get("type", "")
                        
                        # Resolución relacional profunda (Issue 2 de la v0.5.7)
                        if entity_type.lower() == "shot":
                            sequence_id = entity_obj.get("parent_id", "")
                            if sequence_id:
                                seq_obj = gazu.shot.get_sequence(sequence_id)
                                if seq_obj:
                                    sequence_name = seq_obj.get("name", "")
                        elif entity_type.lower() == "asset":
                            asset_type_id = entity_obj.get("entity_type_id", "")
                            if asset_type_id:
                                type_obj = gazu.asset.get_asset_type(asset_type_id)
                                if type_obj:
                                    asset_type_name = type_obj.get("name", "")
                except Exception:
                    pass

                task_url = ""
                try:
                    task_url = gazu.task.get_task_url(task)
                except Exception:
                    pass
                
                formatted_tasks.append({
                    "task_id": task["id"],
                    "project_id": task.get("project_id", ""),
                    "project_name": project_name,
                    "entity_id": task.get("entity_id", ""),
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                    "task_type_id": task_type_id,
                    "task_type_name": task_type_name,
                    "task_type_short_name": task_type_short_name,
                    "sequence_id": sequence_id,
                    "sequence_name": sequence_name,
                    "asset_type_id": asset_type_id,
                    "asset_type_name": asset_type_name,
                    "status_name": status_name,
                    "status_color": status_color,
                    "preview_file_id": preview_id,
                    "task_url": task_url
                })
                
            return formatted_tasks
        except Exception as e:
            import traceback
            print(f"[AuthManager] Error extrayendo tareas:\n{traceback.format_exc()}")
            return []

    def get_recent_activity(self, limit: int = 15) -> List[dict]:
        if not self.user_data:
            return []
            
        current_user_id = self.user_data.get("id")
            
        try:
            tasks = gazu.user.all_tasks_to_do()
            feed = []
            
            for task in tasks:
                comments = gazu.task.all_comments_for_task(task)
                for comment in comments:
                    if comment.get("person_id") == current_user_id:
                        continue
                        
                    if current_user_id in comment.get("acknowledgements", []):
                        continue
                    
                    author = comment.get("person", {})
                    entity_name = task.get("entity_name", "Entity")
                    task_type = task.get("task_type_name", "Task")
                    
                    status_obj = comment.get("task_status", {})
                    status_name = status_obj.get("name", "") if status_obj else ""
                    status_color = status_obj.get("color", "") if status_obj else ""
                    
                    previews = comment.get("previews", [])
                    attachments = comment.get("attachment_files", [])
                    replies = comment.get("replies", [])
                    
                    task_url = ""
                    try:
                        task_url = gazu.task.get_task_url(task)
                    except Exception:
                        pass
                    
                    feed.append({
                        "task_id": task["id"],
                        "comment_id": comment["id"],
                        "author_name": author.get("first_name", "User"),
                        "text": comment.get("text", ""),
                        "created_at": comment.get("created_at", ""),
                        "task_name": f"{entity_name} - {task_type}",
                        "task_url": task_url,
                        "status_name": status_name,
                        "status_color": status_color,
                        "has_previews": len(previews) > 0,
                        "has_attachments": len(attachments) > 0,
                        "reply_count": len(replies)
                    })
            
            feed.sort(key=lambda x: x["created_at"], reverse=True)
            return feed[:limit]
            
        except Exception as e:
            import traceback
            print(f"[AuthManager] Error extrayendo Activity Feed:\n{traceback.format_exc()}")
            return []

    def acknowledge_activity(self, task_id: str, comment_id: str) -> bool:
        try:
            gazu.task.acknowledge_comment(task_id, comment_id)
            return True
        except Exception as e:
            print(f"[AuthManager] Error al acusar recibo del comentario: {e}")
            return False

    def _save_session(self, tokens) -> None:
        data = {
            "host": self.kitsu_host,
            "tokens": tokens
        }
        with open(SESSION_FILE, 'w') as f:
            json.dump(data, f)
