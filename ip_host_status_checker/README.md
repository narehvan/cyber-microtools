# ip_host_status_checker
Given IPv4 and CIDR, it checks if the host is alive or dead

# Usage
`python ip_host_status_checker.py <network_ip> <cidr_prefix>`

`python ip_host_status_checker.py -a <network_ip> <cidr_prefix>`

Options:
    -a    Show only alive hosts - Optional

## example
`python ip_host_status_checker.py 192.168.1.0 24`

`python ip_host_status_checker.py -a 192.168.1.0 24`
