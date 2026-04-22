import socket
import time

host = "moa6.eecs.utk.edu"
ports = [3002, 3009, 6055, 13222, 32100, 32110, 32130, 32150, 32000, 32001, 32010, 32020, 32030, 32040, 32050, 32222, 32323]

def scan_port(port):
    try:
        with socket.create_connection((host, port), timeout=2) as s:
            s.setblocking(False)
            time.sleep(0.5)
            try:
                banner = s.recv(1024)
            except (BlockingIOError, socket.error):
                banner = b""
            
            s.setblocking(True)
            # Send 'map' command as per instructions
            s.sendall(b"map\n")
            time.sleep(1.5)
            s.setblocking(False)
            try:
                response = s.recv(4096)
            except (BlockingIOError, socket.error):
                response = b""
            
            return banner, response
    except (socket.timeout, ConnectionRefusedError, socket.error):
        return None, None

for port in ports:
    banner, response = scan_port(port)
    if banner is not None or response is not None:
        print(f"Port {port}:")
        if banner:
            print(f"  Banner: {banner[:100]!r}")
        if response:
            print(f"  Response: {response[:200]!r}")
            resp_str = response.decode('utf-8', errors='ignore')
            # Signatures from instructions: '$ ', /proc/self/maps, ldd strings, 'bash: command not found'
            if ('$ ' in resp_str or '/proc/self/maps' in resp_str or 
                'libc.so' in resp_str or 'bash:' in resp_str or 
                ' 0x' in resp_str or 'stack' in resp_str):
                print(f"  *** MATCH DETECTED on port {port} ***")
