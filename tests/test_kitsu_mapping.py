import gazu
import json

def main():
    print("=======================================")
    print(" KITSU API ISOLATED TEST: TASK MAPPING ")
    print("=======================================\n")

    # 1. CONFIGURACIÓN (Reemplaza con tus datos reales)
    # ---------------------------------------------------------
    KITSU_HOST = "http://localhost:8080/api"  # Ajusta tu URL y puerto
    KITSU_USER = "admin@example.com"     # Tu correo de admin
    KITSU_PWD  = "entrando1"      # Tu contraseña
    
    PROJECT_NAME = "01_test" # Pon el nombre de tu proyecto de prueba
    SEQUENCE_NAME = "01"              # Secuencia que sepas que existe
    # ---------------------------------------------------------

    try:
        # Autenticación
        print(f"[*] Conectando a Kitsu en {KITSU_HOST}...")
        gazu.client.set_host(KITSU_HOST)
        gazu.log_in(KITSU_USER, KITSU_PWD)
        print("[✓] Login exitoso.\n")

        # Buscar Proyecto y Secuencia
        print(f"[*] Buscando proyecto '{PROJECT_NAME}'...")
        project = gazu.project.get_project_by_name(PROJECT_NAME)
        if not project:
            print("[X] Proyecto no encontrado. Abortando.")
            return

        print(f"[*] Buscando secuencia '{SEQUENCE_NAME}'...")
        sequence = gazu.shot.get_sequence_by_name(project, SEQUENCE_NAME)
        if not sequence:
            print("[X] Secuencia no encontrada. Abortando.")
            return
        breakpoint()
        # Listar tareas de la secuencia
        tasks = gazu.task.all_tasks_for_sequence(sequence)
        print(f"\n[✓] Se encontraron {len(tasks)} tareas para la secuencia {SEQUENCE_NAME}.")
        
        if not tasks:
            print("[!] No hay tareas para inspeccionar. Crea una primero.")
            return

        # Tomar la primera tarea (Debería ser Storyboard si es la única)
        target_task = tasks[0]
        
        print("\n--- CONTENIDO ORIGINAL DE LA TAREA ---")
        # Imprimimos los campos clave para ver si "data" es None, dict, o string
        print(f"ID: {target_task.get('id')}")
        print(f"Task Type: {target_task.get('task_type_name')}")
        print(f"Data actual: {target_task.get('data')}")
        print("--------------------------------------\n")

        print("[*] Inyectando ruta dummy...")
        
        # Extracción hiper-segura
        task_data = target_task.get("data")
        
        # Validamos qué tipo de dato es para evitar el 'NoneType is not subscriptable'
        print(f"    -> Tipo de 'data' recibido de Gazu: {type(task_data)}")
        
        if task_data is None:
            task_data = {}
        elif not isinstance(task_data, dict):
            # Por si Gazu devuelve un string vacío o algo raro
            task_data = {}
            
        task_data["file_path"] = "svn/edit/storyboards/dummy_path-storyboard.blend"
        task_data["file_name"] = "dummy_path-storyboard.blend"
        
        # Intento de actualización
        print(f"[*] Enviando payload: {task_data}")
        gazu.task.update_task_data(target_task["id"], task_data)
        print("[✓] Petición enviada.\n")

        # Verificación
        print("[*] Consultando nuevamente la base de datos...")
        updated_task = gazu.task.get_task(target_task["id"])
        
        print("\n--- CONTENIDO ACTUALIZADO ---")
        print(f"Data verificada: {updated_task.get('data')}")
        print("-----------------------------\n")
        
        if updated_task.get('data') and updated_task['data'].get('file_path'):
            print("[SUCCESS] ¡La inserción fue exitosa y Kitsu la guardó!")
        else:
            print("[FAIL] Kitsu no retuvo la información de 'data'.")

    except Exception as e:
        print(f"\n[ERROR CRÍTICO] Excepción capturada:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
