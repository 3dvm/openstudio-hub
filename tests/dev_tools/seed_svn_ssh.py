import json
import getpass
import paramiko
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "svn_ssh_env.json"

def get_credentials():
    """Carga o solicita las credenciales SSH y de SVN."""
    if CONFIG_FILE.exists():
        print(f"[+] Cargando credenciales cacheadas desde {CONFIG_FILE.name}...")
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("[-] Error: Configuración corrupta. Borrando...")
            CONFIG_FILE.unlink()
            
    print("[!] Configuración de Conexión SSH al Servidor SVN:")
    ssh_host = input("IP/Dominio del Servidor SSH (ej. 192.168.1.100): ").strip()
    
    ssh_port = input("Puerto SSH [Enter para 2222]: ").strip()
    if not ssh_port:
        ssh_port = "2222"
        
    ssh_user = input("Usuario SSH (ej. root o ubuntu): ").strip()
    ssh_passphrase = getpass.getpass("Passphrase de la llave SSH (o contraseña): ")
    
    print("\n[!] Configuración del Proyecto SVN:")
    project_name = input("Nombre del Proyecto (ej. p0004-hub-test): ").strip()
    svn_user = input("Usuario SVN a crear (ej. vendor): ").strip()
    svn_pass = getpass.getpass("Contraseña del Usuario SVN: ")
    
    config_data = {
        "ssh_host": ssh_host,
        "ssh_port": int(ssh_port),
        "ssh_user": ssh_user,
        "ssh_passphrase": ssh_passphrase,
        "project_name": project_name,
        "svn_user": svn_user,
        "svn_pass": svn_pass
    }
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)
    print(f"[+] Credenciales guardadas en {CONFIG_FILE.name}\n")
    return config_data

def execute_remote_cmd(ssh_client, command, step_name):
    """Ejecuta un comando vía SSH e imprime el resultado."""
    print(f"⚙️  {step_name}...")
    stdin, stdout, stderr = ssh_client.exec_command(command)
    
    # Bloquea hasta que el comando termine y lee los resultados
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    
    if exit_status == 0:
        if out: print(f"    Salida: {out}")
        return True
    else:
        # Ignoramos el error si el repositorio ya existe
        if "already exists" in err or "ya existe" in err:
            print("    -> El repositorio/directorio ya existe. Omitiendo.")
            return True
        print(f"    ❌ Error: {err}")
        return False

def main():
    print("==================================================")
    print("🚀 SVN SSH Aprovisionador Automático (Docker)")
    print("==================================================")
    
    creds = get_credentials()
    project = creds["project_name"]
    repo_path = f"/var/opt/svn/{project}"
    file_url = f"file://{repo_path}"
    
    # 1. Establecer conexión SSH
    print(f"\n[+] Conectando vía SSH a {creds['ssh_user']}@{creds['ssh_host']}:{creds['ssh_port']}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # paramiko intentará usar la llave por defecto (~/.ssh/id_rsa, etc.)
        # Le pasamos el passphrase explícitamente para descifrarla, o como fallback de contraseña
        ssh.connect(
            hostname=creds["ssh_host"],
            port=creds["ssh_port"],
            username=creds["ssh_user"],
            password=creds["ssh_passphrase"],
            passphrase=creds["ssh_passphrase"],
            timeout=10
        )
    except Exception as e:
        print(f"❌ Fallo de conexión SSH: {e}")
        # Purgamos el archivo corrupto/inválido para forzar la re-evaluación la próxima vez
        if CONFIG_FILE.exists(): CONFIG_FILE.unlink()
        return

    # 2. Definir Comandos Docker
    cmd_create = f"docker exec estudio_svn svnadmin create {repo_path}"
    
    cmd_conf = (
        f"docker exec estudio_svn sh -c \"echo '[general]' > {repo_path}/conf/svnserve.conf && "
        f"echo 'anon-access = none' >> {repo_path}/conf/svnserve.conf && "
        f"echo 'auth-access = write' >> {repo_path}/conf/svnserve.conf && "
        f"echo 'password-db = passwd' >> {repo_path}/conf/svnserve.conf\""
    )
    
    cmd_users = (
        f"docker exec estudio_svn sh -c \"echo '[users]' > {repo_path}/conf/passwd && "
        f"echo '{creds['svn_user']} = {creds['svn_pass']}' >> {repo_path}/conf/passwd\""
    )
    
    cmd_mkdir = (
        f"docker exec estudio_svn svn mkdir "
        f"{file_url}/02_archivos_de_produccion "
        f"{file_url}/02_archivos_de_produccion/edit "
        f"{file_url}/02_archivos_de_produccion/pro "
        f"{file_url}/02_archivos_de_produccion/pro/assets "
        f"{file_url}/02_archivos_de_produccion/pro/assets/Character "
        f"{file_url}/02_archivos_de_produccion/pro/assets/Character/Prota "
        f"{file_url}/02_archivos_de_produccion/pro/shots "
        f"{file_url}/02_archivos_de_produccion/pro/shots/sq01 "
        f"{file_url}/02_archivos_de_produccion/pro/shots/sq01/sh010 "
        f"{file_url}/02_archivos_de_produccion/pro/shots/sq01/sh020 "
        f"-m 'Init: Estructura base automatizada y Kitsu Sandbox para {project}'"
    )

    # 3. Ejecutar la secuencia
    print(f"\n[+] Forjando el Árbol de Producción SVN...")
    
    if not execute_remote_cmd(ssh, cmd_create, "[1/4] Creando la bóveda SVN"): return
    if not execute_remote_cmd(ssh, cmd_conf, "[2/4] Blindando el acceso (svnserve.conf)"): return
    if not execute_remote_cmd(ssh, cmd_users, "[3/4] Inyectando credenciales base de artistas"): return
    if not execute_remote_cmd(ssh, cmd_mkdir, "[4/4] Forjando la topología de carpetas"): return

    ssh.close()
    print("\n==================================================")
    print(f"✅ ÉXITO: El repositorio {project} está online y estructurado.")
    print("==================================================")

if __name__ == "__main__":
    main()
