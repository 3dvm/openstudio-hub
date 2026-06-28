from core.auth_manager import AuthManager

auth = AuthManager()

# Intentar usar sesión guardada
if auth.login_with_saved_session():
    print("✅ Sesión restaurada automáticamente.")
else:
    print("❌ No hay sesión, iniciando login manual...")
    # Reemplaza con tus datos reales de Kitsu (Vectra Genisys / Aether X)
    url = "https://proyectos.macuare.com.ve" 
    email = "ernesto@macuare.com.ve"
    password = 'fFs&"b?#?Y5>tz&1'
    
    exito, mensaje = auth.login_with_credentials(email, password, url)
    print(mensaje)

if auth.user_data:
    print(f"👤 Hola, {auth.user_data['first_name']}!")
    
    rol = auth.get_user_role()
    if rol == "td":
        print("👑 Eres un DIRECTOR TÉCNICO. Tienes acceso a crear proyectos.")
    else:
        print("🎨 Eres un ARTISTA. Tienes acceso al Hub de trabajo.")
