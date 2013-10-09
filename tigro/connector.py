# -*- coding: utf-8 -*- 
## @package connector
#  LXC-container connector package.
#
#  This package makes firewall rules for LXC-containers.
from pyinotify import WatchManager, Notifier, ProcessEvent, IN_MODIFY
from conf import OPENVPN_STATUS_FILE, DHCP_LEASES_FILE
from db import Connection, Robot, DB_CONN_STRING
from connection import ConnectionStatus
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from parser import OpenVPNStatusParser
from dictdiffer import DictDiffer
from firewall import Firewall
from subprocess import Popen
from threading import Thread
from dnsd import DNSDaemon
import time, logging

## Container connector thread
#
#  This thread makes TCP/IP forwarding rules for containers after client connect
#  to this. IP address of client takes from openvpn.status file.
#
class Connector(Thread):

    ## Database connection engine
    db = create_engine(DB_CONN_STRING, client_encoding='utf8')

    ## Session class with private engine
    Session = sessionmaker(bind=db)

    ## Connected clients dictionary
    clients = {}

    ## The constructor
    def __init__(s, nodename):
        Thread.__init__(s)

        # Init logger
        s.log = logging.getLogger('Connector-{0}'.format(s.name))

        # Init new database session
        s._sess = s.Session()

        # Init firewall tables
        s.f = Firewall(s.log, s._sess)

        # Init DNS daemon
        s.dns = DNSDaemon(s.log, s._sess)

        # Init database connection status table
        s.connections = ConnectionStatus(s.log, s._sess, nodename)

        # Make inotify watcher
        wm = WatchManager()

        ## OpenVPN status update handler
        class PUpdateStatus(ProcessEvent):

            ## Close file event method
            def process_IN_MODIFY(self, event):

                # Update status and firewall rules
                s.updateStatus()

        # Make notificator
        s.notifier = Notifier(wm, PUpdateStatus())

        # Add OpenVPN status file watcher
        wm.watch_transient_file(OPENVPN_STATUS_FILE, IN_MODIFY, PUpdateStatus)

        s._sess.close()

    ## Status updater method
    def updateStatus(s):
        # Init new database session
        s._sess = s.Session()

        # Parse OpenVPN status file
        status = OpenVPNStatusParser(OPENVPN_STATUS_FILE)

        # Parse DHCP daemon leases
        status.concat_dhcp(DHCP_LEASES_FILE)

        s.log.debug('Connected clients: {0}'.format(status.connected_clients.keys()))

        # Filter clients where doesn not have IP address
        clients = s.empty_va_filter(status.connected_clients.values())

        # Filter clients where robot does not exist
        clients = s.robot_exist_filter(clients)

        # Conver client list to dictionary
        clients = s.list_to_dict(clients)

        s.log.debug('Filtered clients: {0}'.format(clients.keys()))

        # Get difference between old and new client lists
        diff = DictDiffer(clients, s.clients)

        s.log.debug('Clients added: {0}'.format(diff.added))
        s.log.debug('Clients removed: {0}'.format(diff.removed))

        # Create new firewall rules
        s.f.createRules(diff.added)

        # Delete old firewall rules
        s.f.deleteRules(diff.removed)

        # Create new DNS records
        s.dns.append(diff.added)

        # Delete old DNS records
        s.dns.delete(diff.removed)

        # Update database records
        s.connections.append(diff.added)
        s.connections.delete(diff.removed)
        s.connections.update(diff.changed)
        s.connections.commit()

        # Start connected LXC-containers
        for name in diff.added:

            # Spawn lxc-start for added connections
            s.log.info('Start container: {0}'.format(name))
            Popen(['lxc-start', '--name', name, '-d']).wait()

        # Stop disconnected LXC-containers
        for name in diff.removed:

            # Spawn lxc-stop for removed connections
            Popen(['lxc-stop', '--name', name]).wait()
            s.log.info('Stop container: {0}'.format(name))

        # Restart DNS daemon (after all veth.* in status UP)
        s.dns.restart()

        # Replace status by new
        s.clients = clients

        s._sess.close()

    ## Empty virtual address filter method
    def empty_va_filter(s, clients):

        # Filter clients where does not have IP
        return filter(lambda x: len(x['Virtual Address']) > 0, clients)


    ## Filter clients if robot does not exist
    def robot_exist_filter(s, clients):

        # Filter clients where does not have robot
        return filter(lambda x: s._sess.query(Robot)\
                        .filter_by(anchor=x['Common Name']).first(), clients)

    ## Client list to dictionary converter
    def list_to_dict(s, clients):

        # Format client list as dictionary
        dict_clients = {}
        for c in clients:
            dict_clients[c['Common Name']] = c

        return dict_clients

    ## Main cycle
    def run(s):

        # Process inotify events
        s.notifier.loop()

