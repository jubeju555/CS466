import socket
import threading
import sys

target = 'moa6.eecs.utk.edu'
ports = range(32000, 32251)
timeout = 0.2
flag_keywords = ['$ ', '/proc/', 'ldd', 'bash: command not found', 'maps', 'さよなら', 'Error! opening file']

results = []
open_ports_count = 0
lock = threading.Lock()

def scan_port(port):
    global open_ports_count
    try:
        with socket.create_connection((target, port), timeout=timeout) as s:
            with lock:
                open_ports_count += 1
            
            # Try to receive initial banner
            banner = b""
            try:
                banner = s.recv(1024)
            except socket.timeout:
                pass
            
            # Send map command
            try:
                s.sendall(b'map\n')
                response = s.recv(1024)
            except (socket.timeout, ConnectionResetError):
                response = b""

            full_output = banner + response
            output_str = full_output.decode('utf-8', errors='ignore')
            
            if any(keyword in output_str for keyword in flag_keywords):
                snippet = output_str[:120].replace('\n', ' ')
                print(f"Port {port}: {snippet}")
    except (socket.timeout, ConnectionRefusedError, OSError):
        pass

threads = []
for port in ports:
    t = threading.Thread(target=scan_port, args=(port,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print(f"Total open ports: {open_ports_count}")
