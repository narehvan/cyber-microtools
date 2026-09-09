import ipaddress
import platform
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

##### Usage function to display how to use the script
def usage():
    print(f"Usage: {sys.argv[0]} [-a] <network_ip> <cidr_prefix>")
    print()
    print("Options:")
    print("  -a    Show only alive hosts - Optional")
    print()
    print("Arguments:")
    print("  network_ip   Network IPv4 address (e.g. 192.168.1.0)")
    print("  cidr_prefix  CIDR prefix length (e.g. 24)")
    print()
    print("Example:")
    print(f"  {sys.argv[0]} 192.168.1.0 24")
    print(f"  {sys.argv[0]} -a 192.168.1.0 24")

##### Ping a host and print its status
def check_host(host, alive_only):
    ip = str(host)
    alive = ping(ip)

    if alive:
        print(f"{ip:<15} [Alive]")
    elif not alive_only:
        print(f"{ip:<15} [Dead]")


##### Returns True if the host responds to a single ping. Executed in a separate thread for each host
def ping(host):
    system = platform.system().lower()

    if system == "windows":
        cmd = [
            "C:\\Windows\\System32\\ping",
            "-n", "1",          # Send 1 echo request
            "-w", "1000",       # Timeout: 1000 ms
            host
        ]
    elif system == "darwin":
        # macOS
        cmd = [
            "/sbin/ping",
            "-c", "1",          # Send 1 packet
            "-W", "1000",       # Timeout in milliseconds
            host
        ]
    else:
        # Linux
        cmd = [
            "/usr/bin/ping",
            "-c", "1",          # Send 1 packet
            "-W", "1",          # Timeout in seconds
            host
        ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return result.returncode == 0


##### Scan the network for alive hosts
def scan_network(network_ip, cidr, alive_only):
    network = ipaddress.ip_network(f"{network_ip}/{cidr}", strict=False)

    hosts = list(network.hosts())

    # Increase or decrease max_workers depending on your system.
    with ThreadPoolExecutor(max_workers=64) as executor:
        executor.map(
            lambda host: check_host(host, alive_only),
            hosts
        )

##### Validate the provided IP address
def is_valid_ip(ip):
    # Validate IPv4 address
    try:
        ipaddress.IPv4Address(ip)
    except ipaddress.AddressValueError:
        print(f"Error: '{ip}' is not a valid IPv4 address.")
        return False
    return True

##### Validate the provided CIDR prefix
def is_valid_cidr(cidr):
    # Validate CIDR prefix length
    try:
        cidr = int(cidr)
        # Validate CIDR range
        if cidr < 0 or cidr > 32:
            print("Error: CIDR prefix must be between 0 and 32.")
            return False
        
    except ValueError:
        print("Error: CIDR prefix must be an integer.\n")
        usage()
        return False

    return True

##### Main function to handle command-line arguments and initiate IP address generation
def main():
    alive_only = False
    args = sys.argv[1:]

    if len(args) > 0 and args[0] == "-a":
        alive_only = True
        args = args[1:]

    if len(args) != 2:
        print("Error: Invalid number of arguments.\n")
        usage()
        sys.exit(1)

    network_ip = args[0]
    cidr = args[1]

    try:
        if (is_valid_ip(network_ip) and is_valid_cidr(cidr)):
            scan_network(network_ip, cidr, alive_only)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()