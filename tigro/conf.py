# -*- coding: utf-8 -*- 
## @package conf
#  TIGRO configuration file.
#
#  This file contain some configuration details.

## DNS daemon config file
DNSD_CONFIG = '/etc/lxc-hosts'

## DHCP leases file
DHCP_LEASES_FILE = '/var/lib/misc/dnsmasq.leases'

## Start WebSocket port number
WS_START_PORT = 7000

## LXC-containers directory
LXC_DIR = '/lxc'

## LXC-container config template
#
#  This is template config file for LXC container.
#  Template accept two arguments: anchor and ipaddr for new container.
CONFIG_TEMPLATE = '{0}/config.template'.format(LXC_DIR)

## LXC-container IP-address template
ADDRESS_TEMPLATE = '10.10.{0}.{1}'

## LXC-container gateway address
GATEWAY_ADDRESS = '10.10.255.254/16'

## OpenVPN status file, version 3
OPENVPN_STATUS_FILE = '/run/openvpn.status'

## Database name
DB_NAME = 'tigro'

## Database user
DB_USER = 'akru'

## Database password
DB_PASSWORD = 'akru'

## Database host
DB_HOST = 'localhost'

## Database driver
DB_DRIVER = 'postgresql+psycopg2'
