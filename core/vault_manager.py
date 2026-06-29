class VaultManager:
    def __init__(self):
        """
        Almacena credenciales críticas de la sesión estrictamente en memoria (RAM).
        Evita la persistencia en disco duro por motivos de seguridad en entornos compartidos.
        """
        # Credenciales SVN
        self._svn_user = ""
        self._svn_password = ""
        
        # Credenciales Kitsu (Para inyección automatizada en Blender)
        self._kitsu_email = ""
        self._kitsu_password = ""

    def save_svn_credentials(self, user: str, password: str):
        """Guarda las credenciales de SVN en la sesión actual."""
        self._svn_user = user
        self._svn_password = password

    def get_svn_credentials(self) -> tuple[str, str]:
        """Retorna una tupla con (usuario_svn, contraseña_svn)."""
        return self._svn_user, self._svn_password

    def has_svn_credentials(self) -> bool:
        """Verifica si las credenciales de SVN existen en la memoria."""
        return bool(self._svn_user and self._svn_password)

    def save_kitsu_credentials(self, email: str, password: str):
        """Guarda las credenciales de Kitsu capturadas en el formulario de Login."""
        self._kitsu_email = email
        self._kitsu_password = password

    def get_kitsu_credentials(self) -> tuple[str, str]:
        """Retorna una tupla con (email_kitsu, contraseña_kitsu)."""
        return self._kitsu_email, self._kitsu_password

    def has_kitsu_credentials(self) -> bool:
        """Verifica si el Hub tiene la contraseña de Kitsu en RAM para esta sesión."""
        return bool(self._kitsu_email and self._kitsu_password)

    def clear(self):
        """Destruye de forma absoluta todas las credenciales de la RAM al cerrar sesión."""
        self._svn_user = ""
        self._svn_password = ""
        self._kitsu_email = ""
        self._kitsu_password = ""
