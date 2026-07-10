import json
import gazu
from pathlib import Path

# Ruta donde guardaremos el token inofensivo de Kitsu
OPENSTUDIO_CONFIG_DIR = Path.home() / ".openstudio"
SESSION_FILE = OPENSTUDIO_CONFIG_DIR / "session.json"

class AuthManager:
    def __init__(self):
        self.kitsu_host = None
        self.user_data = None
        
        # Asegurarnos de que exista la carpeta oculta
        if not OPENSTUDIO_CONFIG_DIR.exists():
            OPENSTUDIO_CONFIG_DIR.mkdir(parents=True)

    def set_host(self, host_url: str):
        """Configura a dónde va a apuntar Kitsu (Gazu)"""
        # Gazu requiere que la URL termine en /api
        if not host_url.endswith("/api"):
            host_url = f"{host_url.rstrip('/')}/api"
        
        self.kitsu_host = host_url
        gazu.client.set_host(self.kitsu_host)

    def login_with_credentials(self, email, password, host_url):
        """Inicia sesión con email y contraseña, y guarda el token localmente"""
        try:
            self.set_host(host_url)
            # Gazu se encarga del login
            tokens = gazu.log_in(email, password)
            self.user_data = gazu.client.get_current_user()
            
            # Guardar la sesión para no pedir clave mañana
            self._save_session(tokens)
            return True, "Login exitoso"
            
        except gazu.exception.AuthFailedException:
            return False, "Credenciales incorrectas."
        except Exception as e:
            return False, f"Error de conexión: {str(e)}"

    def login_with_saved_session(self):
        """Intenta restaurar la sesión usando el JSON local"""
        if not SESSION_FILE.exists():
            return False

        try:
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)
            
            self.set_host(data["host"])
            gazu.client.set_tokens(data["tokens"])
            
            # Verificar si el token sigue siendo válido haciendo un ping a Kitsu
            self.user_data = gazu.client.get_current_user()
            return True
            
        except Exception:
            # Si el token expiró o el archivo está corrupto
            if SESSION_FILE.exists():
                SESSION_FILE.unlink() # Borrar archivo inválido
            return False

    def logout(self):
        """Cierra sesión y borra el rastro en el disco"""
        gazu.log_out()
        self.user_data = None
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()

    def get_user_role(self) -> str:
        """
        Determina el rol del usuario según la Matriz RBAC de OpenStudio.
        Evalúa el 'rol' nativo del servidor y el campo 'position' para Leads.
        """
        if not self.user_data:
            return "guest"
            
        kitsu_role = self.user_data.get("role", "").lower()
        kitsu_position = self.user_data.get("position", "").lower()
        
        if kitsu_role == "admin":
            return "td"
        elif kitsu_role == "supervisor":
            return "supervisor"
        elif kitsu_role == "manager":
            return "manager" # Project Managers
        elif kitsu_role == "vendor":
            return "vendor"
        elif kitsu_role == "client":
            return "client"
        elif kitsu_role == "user":
            # Si es usuario base, verificamos su posición en el estudio
            if kitsu_position == "lead":
                return "lead"
            return "artist"
        else:
            return "artist"

    def get_current_token(self) -> str:
        """
        Retorna el token JWT activo de Kitsu (Gazu) para que el Hub 
        pueda inyectarlo como la variable de entorno GAZU_AUTH_TOKEN 
        en el subproceso aislado de Blender.
        """
        tokens = gazu.client.get_tokens()
        if tokens:
            return tokens.get("access_token", "")
        return ""

    def _save_session(self, tokens):
        """Guarda los tokens de Gazu en un JSON local oculto"""
        data = {
            "host": self.kitsu_host,
            "tokens": tokens
        }
        with open(SESSION_FILE, 'w') as f:
            json.dump(data, f)
