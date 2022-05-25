import paramiko
import select

if __name__ == '__main__':
    host = "foundry.mst.edu"
    port = 22
    username = "amlfhg"
    password = "AMLONS3253$"

    # commands needs to be chained together in one statement with ;

    client = paramiko.SSHClient()
    localpath = r"C:\Users\fabio\Downloads"

    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, port, username, password)

    #iron_spin_directory = 'cd Spin/Iron\ Spin\ Plus\ Charge/'

    stdin, stdout, stderr = client.exec_command(f'ls -d */')
    print("select one of the following directories: ")
    print("Or alternatively, ")
    for directory in stdout.readlines():
        print(directory.strip())
    choice = str(input())

    client.close()
