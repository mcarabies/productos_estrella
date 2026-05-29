import paramiko

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('147.93.2.187', username='root', password='NR4Cp5nyodxr2Xeqyb8A0xXE')
    print("Connected.")
    stdin, stdout, stderr = client.exec_command('docker logs prodestrella-bot-app-1 --tail 300')
    output = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    
    with open('remote_logs.txt', 'w', encoding='utf-8') as f:
        f.write(output)
        f.write("\n================\n")
        f.write(err)
    print("Logs saved to remote_logs.txt")
except Exception as e:
    print("Error:", str(e))
finally:
    client.close()
