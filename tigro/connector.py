# -*- coding: utf-8 -*- 
## @package connector
#  LXC-container connector package.
#
#  This package makes firewall rules for LXC-containers.
from pyinotify import WatchManager, Notifier, ProcessEvent, IN_MODIFY
from db import Connection, Robot, DB_CONN_STRING
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from netfilter.rule import Rule, Match, Target
from netfilter.table import Table
from parser import OpenVPNStatusParser
from conf import OPENVPN_STATUS_FILE, GATEWAY_ADDRESS
from dictdiffer import DictDiffer
from subprocess import Popen
from threading import Thread
import time, logging

## Firewall controller class
class Firewall:

    ## The constructor
    def __init__(s, logger, session):

        # Save logger
        s.log = logger

        # Save database connection session
        s.db = session

        # Purge NAT table
        s.log.debug("Init NAT firewall table")
        s.table = Table('nat')
        s.table.flush_chain()
        s.table.delete_chain()

        # Init rules dictionary
        s.rules = {}

    ## Firewall rule creator method
    def createRules(s, clients):

        # Create firewall rules for all connections
        for key in clients:

            # Get robot by anchor
            r = s.db.query(Robot)\
                            .join('container')\
                            .filter(Robot.anchor==key)\
                            .first()

            if not r:
                # robot doesn't exist - skip
                s.log.critical('Robot {0} does NOT exist'.format(key))
                continue

            # Get virtual address of client from dict
            vaddress = clients[key]['Virtual Address']

            # Make client firewall rules
            s.log.info("Create firewall rule for: {0} -> {1}"
                            .format(vaddress, r.container.address))
            client_rule = Rule(
                protocol     = 'tcp',
                destination  = r.container.address,
                source       = vaddress,
                in_interface = 'tun0',
                jump         = Target('DNAT', '--to-destination {0}'.format(r.container.address))
            )

            # Make container firewall rules
            s.log.info("Create firewall rule for: {0} <- {1}"
                            .format(vaddress, r.container.address))
            container_rule = Rule(
                protocol     = 'tcp',
                source       = r.container.address,
                destination  = vaddress,
                in_interface = 'veth.{0}'.format(r.anchor),
                jump         = Target('DNAT', '--to-destination {0}'.format(vaddress))
            )
            master_rule = Rule(
                protocol     = 'tcp',
                source       = r.container.address,
                destination  = GATEWAY_ADDRESS,
                in_interface = 'veth.{0}'.format(r.anchor),
                matches      = [ Match('tcp', '--dport 11311') ],
                jump         = Target('DNAT', '--to-destination {0}:11311'.format(vaddress))
            )

            # Append rules to table
            s.table.append_rule('PREROUTING', client_rule)
            s.table.append_rule('PREROUTING', container_rule)
            s.table.append_rule('PREROUTING', master_rule)

            # Append rules to internal list
            s.rules[r.anchor] = {
                            'client': client_rule,
                            'container': container_rule,
                            'master': master_rule }

    ## Firewall rule remover method
    def deleteRules(s, clients):

        # Delete firewall rules for clients in list
        for key in clients:

            # Delete rules from table
            s.log.info("Delete firewall rule for: {0} -> {1}"
                            .format(s.rules[key]['client'].source,
                                    s.rules[key]['client'].destination))
            s.table.delete_rule('PREROUTING', s.rules[key]['client'])

            s.log.info("Delete firewall rule for: {0} <- {1}"
                            .format(s.rules[key]['container'].destination,
                                    s.rules[key]['container'].source))
            s.table.delete_rule('PREROUTING', s.rules[key]['container'])
            s.table.delete_rule('PREROUTING', s.rules[key]['master'])

            # Delete rules from internal list
            s.rules.pop(key)

## Database connector
#
#  This class provide access to connection status table.
class ConnectionStatus:

    ## The constructor
    def __init__(s, logger, session):

        # Save logger
        s.log = logger

        # Save database connection session
        s.db = session

        # Init empty table
        s.log.debug('Init connection table')
        items = s.db.query(Connection).all()
        if len(items) > 0:
            for i in items:
                s.db.delete(i)
                s.log.debug('Drop connection from {0}'.format(i.raddress))
            s.db.commit()
        s.log.debug('Connection table crear')

    ## Commit changes to database
    def commit(s):

        # Commit current session
        s.db.commit()

    ## append new connected clients
    def append(s, clients):

        # Insert to table all clients in list
        for key in clients:

            # Get robot by anchor
            r = s.db.query(Robot)\
                            .join('container')\
                            .filter(Robot.anchor==key)\
                            .first()

            if not r:
                # robot doesn't exist - skip
                s.log.critical('Robot {0} does NOT exist'.format(key))
                continue

            # Create connection row
            c = Connection(
                since     = clients[key]['Connected Since'],
                vaddress  = clients[key]['Virtual Address'],
                raddress  = clients[key]['Real Address'],
                sent      = int(clients[key]['Bytes Sent']),
                received  = int(clients[key]['Bytes Received']),
                container = r.container.id
            )

            # Add new item to session
            s.log.info('Append new connection: {0} -> {1}'
                            .format(c.raddress, c.vaddress))
            s.db.add(c)

    ## Delete disconnected clients
    def delete(s, clients):

        # Drop all clients in list
        for key in clients:

            # Select connection by source IP
            c = s.db.query(Connection).filter(
                    Connection.raddress == clients[key]['Real Address']
                ).first()

            if not c:
                # nothing to drop - skip
                continue

            # Drop item
            s.log.info('Delete connection from {0}'.format(c.raddress))
            s.db.delete(c)

    ## Update client connection
    def update(s, clients):

        # Decomposition of clients
        before, after = clients

        # Drop all clients in list
        for key in before:

            # Select connection by source IP
            c = s.db.query(Connection).filter(
                    Connection.raddress == before[key]['Real Address']
                ).first()

            if not c:
                # nothing to change - skip
                continue

            # Update columns
            c.since    = after[key]['Connected Since']
            c.vaddress = after[key]['Virtual Address']
            c.raddress = after[key]['Real Address']
            c.sent     = int(after[key]['Bytes Sent'])
            c.received = int(after[key]['Bytes Received'])

            # Update connection information
            s.log.info('Update connection stats: {0} -> {1}'
                            .format(c.raddress, c.vaddress))
            s.db.add(c)

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
    def __init__(s):
        Thread.__init__(s)

        # Init logger
        s.log = logging.getLogger('Connector-{0}'.format(s.name))

        # Init new database session
        sess = s.Session()

        # Init firewall tables
        s.f = Firewall(s.log, sess)

        # Init database connection status table
        s.connections = ConnectionStatus(s.log, sess)

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

