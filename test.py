import nmap

def scan_specific_subnets(port='10023', start_subnet=1, end_subnet=100):
    nm = nmap.PortScanner()
    mixer_ips = []
    for third_octet in range(start_subnet, end_subnet + 1):
        subnet = f'192.168.{third_octet}.0/24'
        print(f"Scanning subnet: {subnet}")
        nm.scan(hosts=subnet, arguments=f'-p {port}')
        for host in nm.all_hosts():
            if nm[host].has_tcp(int(port)):
                mixer_ips.append(host)
                print(f"Found device with open port {port} at {host}")
    return mixer_ips

# Example usage
mixer_ips = scan_specific_subnets()
print("Found potential X32 mixers at:", mixer_ips)