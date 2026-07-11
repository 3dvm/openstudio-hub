class VaultManager:
    """
    Gestor de Bóveda en Memoria (RAM).
    Almacena credenciales críticas de la sesión.
    Garantiza el principio Zero-Disk Passwords evitando la persistencia en disco duro.
    """
    def __init__(self):
        # Credenciales VCS (SVN / Git LFS)
        self._svn_user: str = ""
        self._svn_password: str = ""
        
        # Credenciales Kitsu (Para inyección automatizada)
        self._kitsu_email: str = ""
        self._kitsu_password: str = ""

    def save_svn_credentials(self, user: str, password: str) -> None:
        """Guarda las credenciales del Control de Versiones (VCS) en la sesión actual."""
        self._svn_user = user
        self._svn_password = password

    def get_svn_credentials(self) -> tuple[str, str]:
        """Retorna una tupla con (usuario_vcs, contraseña_vcs)."""
        return self._svn_user, self._svn_password

    def has_svn_credentials(self) -> bool:
        """Verifica si las credenciales del repositorio existen en la memoria RAM."""
        return bool(self._svn_user and self._svn_password)

    def save_kitsu_credentials(self, email: str, password: str) -> None:
        """Guarda las credenciales de Kitsu capturadas en el formulario de Login."""
        self._kitsu_email = email
        self._kitsu_password = password

    def get_kitsu_credentials(self) -> tuple[str, str]:
        """Retorna una tupla con (email_kitsu, contraseña_kitsu)."""
        return self._kitsu_email, self._kitsu_password

    def has_kitsu_credentials(self) -> bool:
        """Verifica si el Hub tiene la contraseña de Kitsu en RAM para esta sesión."""
        return bool(self._kitsu_email and self._kitsu_password)

    def clear(self) -> None:
        """
        Destruye de forma absoluta todas las credenciales de la RAM.
        Debe ser invocado obligatoriamente por el AuthManager o la UI al cerrar sesión.
        """
        self._svn_user = ""
        self._svn_password = ""
        self._kitsu_email = ""
        self._kitsu_password = ""
