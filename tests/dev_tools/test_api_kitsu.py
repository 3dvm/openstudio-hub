import gazu
import getpass

host = input("URL de Kitsu: ").strip()
if not host.endswith("/api"): host += "/api"

gazu.client.set_host(host)
gazu.log_in(input("Email: "), getpass.getpass("Clave: "))

print("\n--- DUMP DE LA API ---")
for task_name in ["Animation", "Rigging"]:
    t = gazu.task.get_task_type_by_name(task_name)
    if t:
        print(f"[{task_name}] ID: {t.get('id')}")
        print(f"[{task_name}] For Entity: {t.get('for_entity')}")
    else:
        print(f"[{task_name}] No encontrado.")
