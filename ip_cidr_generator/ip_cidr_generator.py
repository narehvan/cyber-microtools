import sys
import ipaddress

##### Usage function to display how to use the script
def usage():
    print(f"Usage: {sys.argv[0]} <network_ip> <cidr_prefix>")
    print()
    print("Arguments:")
    print("  network_ip   Network IPv4 address (e.g. 192.168.1.0)")
    print("  cidr_prefix  CIDR prefix length (e.g. 24)")
    print()
    print("Example:")
    print(f"  {sys.argv[0]} 192.168.1.0 24")

##### Generate IP addresses from the given network IP and CIDR prefix
def generate_ipaddresses(network_ip, cidr):
    network = ipaddress.ip_network(f"{network_ip}/{cidr}", strict=False)

    # print only usable host addresses
    for ip in network.hosts():
        print(ip)

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
    # Expect exactly two arguments: IP and CIDR
    if len(sys.argv) != 3:
        print("Error: Invalid number of arguments.\n")
        usage()
        sys.exit(1)

    network_ip = sys.argv[1]
    cidr = sys.argv[2]

    try:
        if (is_valid_ip(network_ip) and is_valid_cidr(cidr)):
            generate_ipaddresses(network_ip, cidr)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()