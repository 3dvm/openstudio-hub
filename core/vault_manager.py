class VaultManager:
    """
        Gestionamos las contraseñas del usuario en la RAM, sin usar keyrings del OS
    """

    def __init__(self):
        self._svn_password = "" 

    def store_password(self, password: str):
        if password:
            self._svn_password = password.strip()

    def get_password(self) -> str:
        return self._svn_password

    def has_credentials(self) -> bool:
        return self._svn_password != ""

    def clear(self):
        self._svn_password = ""
