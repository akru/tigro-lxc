# -*- coding: utf-8 -*- 
## @package connector
#  LXC-container connector package.
#
#  This package makes firewall rules for LXC-containers.
from pyinotify import WatchManager, Notifier, ProcessEvent, IN_MODIFY
from db import Connection, Robot, DB_CONN_STRING
from connection import ConnectionStatus
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from parser import OpenVPNStatusParser
from conf import OPENVPN_STATUS_FILE
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
    def __init__(s, node):
        Thread.__init__(s)

        # Init logger
        s.log = logging.getLogger('Connector-{0}'.format(s.name))

        # Init new database session
        sess = s.Session()

        # Init firewall tables
        s.f = Firewall(s.log, sess)

        # Init DNS daemon
        s.dns = DNSDaemon(s.log, sess)

        # Init database connection status table
        s.connections = ConnectionStatus(s.log, sess, node)

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

    ## Status updater method
    def updateStatus(s):

        # Parse OpenVPN status file
        status = OpenVPNStatusParser(OPENVPN_STATUS_FILE)

        # Get difference between old and new client lists
        diff = DictDiffer(status.connected_clients, s.clients)

        # Create new firewall rules
        s.f.createRules(diff.added)

        # Delete old firewall rules
        s.f.deleteRules(diff.removed)

        # Create new DNS records
        s.dns.append(diff.added)

        # Delete old DNS records
        s.dns.delete(diff.removed)

        # Restart DNS daemon
        s.dns.restart()

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

        # Replace status by new
        s.clients = status.connected_clients

    ## Main cycle
    def run(s):

        # Process inotify events
        s.notifier.loop()

