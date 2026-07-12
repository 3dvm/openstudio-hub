import gazu
import getpass
import sys

def main():
    print("==================================================")
    print("🌱 Kitsu Seed Data Generator - OpenStudio Hub Test")
    print("==================================================")
    
    # 1. Recolección de credenciales
    host_url = input("URL de Kitsu (ej. http://localhost/api): ").strip()
    # Asegurarnos de que termine en /api
    if not host_url.endswith("/api"):
        host_url = f"{host_url.rstrip('/')}/api"
        
    email = input("Email de Admin: ").strip()
    password = getpass.getpass("Contraseña: ")
    
    print("\n[+] Conectando a la API...")
    gazu.client.set_host(host_url)
    
    try:
        gazu.log_in(email, password)
        print("[+] Login exitoso.")
    except gazu.exception.AuthFailedException:
        print("[-] Error: Credenciales incorrectas.")
        sys.exit(1)
    except Exception as e:
        print(f"[-] Error de red: {e}")
        sys.exit(1)

    # 2. Creación del Proyecto
    project_name = "p0004-hub-test"
    print(f"\n[+] Buscando/Creando Proyecto: {project_name}")
    project = gazu.project.get_project_by_name(project_name)
    if not project:
        project = gazu.project.new_project(project_name)
        print(f"    -> Proyecto '{project_name}' creado.")
    else:
        print(f"    -> Proyecto '{project_name}' ya existe.")

    # 3. Creación de Tipología y Asset
    print("\n[+] Configurando Assets...")
    asset_type = gazu.asset.get_asset_type_by_name("Character")
    if not asset_type:
        asset_type = gazu.asset.new_asset_type("Character")
        
    asset_name = "Prota"
    asset = gazu.asset.get_asset_by_name(project, asset_name)
    if not asset:
        asset = gazu.asset.new_asset(project, asset_type, asset_name)
        print(f"    -> Asset '{asset_name}' (Character) creado.")
    else:
        print(f"    -> Asset '{asset_name}' ya existe.")

    # 4. Creación de Secuencia y Shots
    print("\n[+] Configurando Shots...")
    seq_name = "sq01"
    sequence = gazu.shot.get_sequence_by_name(project, seq_name)
    if not sequence:
        sequence = gazu.shot.new_sequence(project, seq_name)
        print(f"    -> Secuencia '{seq_name}' creada.")
        
    shots = ["sh010", "sh020"]
    for shot_name in shots:
        shot = gazu.shot.get_shot_by_name(sequence, shot_name)
        if not shot:
            gazu.shot.new_shot(project, sequence, shot_name)
            print(f"    -> Shot '{shot_name}' creado en '{seq_name}'.")
        else:
            print(f"    -> Shot '{shot_name}' ya existe.")

    # 5. Creación de Usuarios Dummy (RBAC)
    print("\n[+] Configurando Usuarios Dummy (Contraseña por defecto: openstudio123)...")
    dummy_users = [
        {"first_name": "Test", "last_name": "Vendor", "email": "vendor@dummy.com", "role": "user", "title": "Vendor"},
        {"first_name": "Test", "last_name": "Artist", "email": "artist@dummy.com", "role": "user", "title": "Artist"},
        {"first_name": "Test", "last_name": "Lead", "email": "lead@dummy.com", "role": "user", "title": "Lead"},
    ]
    
    created_users = {}
    for du in dummy_users:
        user = gazu.person.get_person_by_email(du["email"])
        if not user:
            try:
                # Nota: Gazu asigna roles internamente, si la API lo rechaza, los creamos como standard users.
                user = gazu.person.new_person(
                    first_name=du["first_name"],
                    last_name=du["last_name"],
                    email=du["email"],
                    role=du["role"],
                    password="openstudio123"
                )
                print(f"    -> Usuario '{du['email']}' ({du['title']}) creado.")
            except Exception as e:
                print(f"    -> Advertencia: No se pudo crear el usuario {du['email']}. ¿Faltan permisos de Admin? Detalle: {e}")
        else:
            print(f"    -> Usuario '{du['email']}' ya existe.")
        created_users[du["title"]] = user

    # 6. Creación de Tareas y Asignaciones
    print("\n[+] Creando Tareas y asignando usuarios...")
    
    # Asegurar Tipos de Tarea
    anim_type = gazu.task.get_task_type_by_name("Animation")
    if not anim_type: anim_type = gazu.task.new_task_type("Animation")
    
    rig_type = gazu.task.get_task_type_by_name("Rigging")
    if not rig_type: rig_type = gazu.task.new_task_type("Rigging")

    # Asignar Vendor a Animation en sh010
    shot_10 = gazu.shot.get_shot_by_name(sequence, "sh010")
    if shot_10 and created_users.get("Vendor"):
        task = gazu.task.get_task_by_entity(shot_10, anim_type)
        if not task: task = gazu.task.new_task(shot_10, anim_type)
        gazu.task.assign_task(task, created_users["Vendor"])
        print(f"    -> Tarea 'Animation' en 'sh010' asignada al Vendor.")

    # Asignar Artist a Rigging en Prota
    if asset and created_users.get("Artist"):
        task = gazu.task.get_task_by_entity(asset, rig_type)
        if not task: task = gazu.task.new_task(asset, rig_type)
        gazu.task.assign_task(task, created_users["Artist"])
        print(f"    -> Tarea 'Rigging' en 'Prota' asignada al Artist.")

    print("\n==================================================")
    print("✅ Siembra de datos completada con éxito.")
    print("==================================================")

if __name__ == "__main__":
    main()
