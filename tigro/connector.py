# -*- coding: utf-8 -*- 
## @package connector
#  LXC-container connector package.
#
#  This package makes firewall rules for LXC-containers.
from parser import OpenVPNStatusParser
from threading import Thread
import time

## Container connector thread
#
#  This thread makes TCP/IP forwarding rules for containers after client connect
#  to this. IP address of client takes from openvpn.status file.
#
class Connector(Thread):
    def __init__(s):
        Thread.__init__(s)

