[ INICIO ] -> El usuario abre Macuare Hub.
   |
   v
[ CHECK SESSION ] -> ¿Existe un token de Kitsu válido guardado localmente?
   |
   +-- (NO) --> [ LOGIN SCREEN ]
   |              |-> Pide Email y Password (Kitsu).
   |              |-> Se guarda token localmente en disco (~/.macuare).
   |              +-> (Vuelve a CHECK SESSION)
   v
(SÍ) -> [ GET USER ROLE ] -> Consulta a Kitsu: "¿Qué rol tiene este usuario?"
   |
   +-- Si Rol == 'Admin' / 'Manager' (Es un TD)
   |      |
   |      v
   |   [ TD DASHBOARD ]
   |      |-> Botón: "Crear Nuevo Proyecto" -> Llama a project_builder.py
   |      |-> Componente: Lista de Proyectos Activos (Para abrirlos)
   |
   +-- Si Rol == 'User' / 'Artist' (Es un Animador/Modelador)
          |
          v
       [ ARTIST DASHBOARD ]
          |-> (No puede crear proyectos)
          |-> Componente: Lista de Proyectos Activos
          |-> Botón: "Abrir: [Proyecto]" -> Llama a env_launcher.py
                 |
                 +-> (Pide clave SVN por única vez y la guarda en RAM)
                 +-> Ejecuta entorno aislado de Blender.
