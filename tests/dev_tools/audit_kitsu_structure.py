import gazu
import getpass
import sys

def main():
    print("==================================================")
    print("🔍 Kitsu Structural Audit Tool - OpenStudio Hub")
    print("==================================================")
    
    # 1. Autenticación
    host_url = input("URL de Kitsu (ej. https://proyectos.macuare.com.ve/api): ").strip()
    if not host_url.endswith("/api"):
        host_url = f"{host_url.rstrip('/')}/api"
        
    email = input("Email de Admin: ").strip()
    password = getpass.getpass("Contraseña: ")
    
    print("\n[+] Conectando a la API...")
    gazu.client.set_host(host_url)
    
    try:
        gazu.log_in(email, password)
        print("[+] Login exitoso.\n")
    except Exception as e:
        print(f"[-] Error de conexión: {e}")
        sys.exit(1)

    print("==================================================")
    print("RADIOGRAFÍA DEL ESTUDIO")
    print("==================================================")

    # 2. Volcado de Departamentos
    print("\n--- 1. DEPARTAMENTOS ---")
    departments = gazu.task.all_departments()
    for dept in departments:
        print(f"  • {dept['name']}")

    # 3. Volcado de Tipos de Tareas (Task Types)
    print("\n--- 2. TIPOS DE TAREAS (Task Types) ---")
    task_types = gazu.task.all_task_types()
    # Agrupamos por entidad para mayor claridad
    tt_by_entity = {}
    for tt in task_types:
        entity = tt.get('for_entity', 'Desconocido')
        if entity not in tt_by_entity:
            tt_by_entity[entity] = []
        tt_by_entity[entity].append(tt['name'])
        
    for entity, names in tt_by_entity.items():
        print(f"\n  [{entity}]")
        for name in names:
            print(f"    • {name}")

    # 4. Volcado de Tipos de Assets (Asset Types)
    print("\n--- 3. TIPOS DE ASSETS (Asset Types) ---")
    asset_types = gazu.asset.all_asset_types()
    for at in asset_types:
        print(f"  • {at['name']}")

    # 5. Volcado de Proyectos Activos
    print("\n--- 4. PROYECTOS ---")
    projects = gazu.project.all_projects()
    if not projects:
        print("  (No hay proyectos creados)")
    for p in projects:
        status = p.get('project_status_name', 'Activo')
        print(f"  • {p['name']} [{status}]")

    print("\n==================================================")
    print("✅ Auditoría completada.")
    print("==================================================")

if __name__ == "__main__":
    main()
