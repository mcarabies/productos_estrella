import paramiko

def fetch_logs():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("147.93.2.187", username="root", password="v4rD@7wLq8#kM_1p")
    
    cmd = "docker compose -f /opt/prodEstrella_bot/docker-compose.yml logs --tail 300 app | grep -E 'ai.tool|ai.route_message|mercadopago|error'"
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print("--- STDOUT ---")
    print(stdout.read().decode())
    print("--- STDERR ---")
    print(stderr.read().decode())
    client.close()

if __name__ == "__main__":
    fetch_logs()
