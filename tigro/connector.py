# -*- coding: utf-8 -*- 
## @package connector
#  LXC-container connector package.
#
#  This package makes firewall rules for LXC-containers.
from pyinotify import WatchManager, Notifier, ProcessEvent, IN_MODIFY
from db import Connection, Robot, DB_CONN_STRING
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from parser import OpenVPNStatusParser
from conf import OPENVPN_STATUS_FILE
from dictdiffer import DictDiffer
from threading import Thread
import time, logging

## Firewall controller class
class Firewall:

    ## The constructor
    def __init__(s, logger):

        # Save logger
        s.log = logger

    ## Firewall rule creator method
    def createRules(s, clients):

        if not clients:
            # nothing to create
            return

        s.log.info("Create rules for: {0}".format(clients))

    ## Firewall rule remover method
    def deleteRules(s, clients):

        if not clients:
            # nothing to delete
            return

        s.log.info("Delete rules for: {0}".format(clients))

## Database connector
#
#  This class provide access to connection status table.
class Database:

    ## Database connection engine
    db = create_engine(DB_CONN_STRING, client_encoding='utf8')

    ## Session class with private engine
    Session = sessionmaker(bind=db)

    ## The constructor
    def __init__(s, logger):

        # Save logger
        s.log = logger

        # Create new database connection session
        s._sess = s.Session()

        # Init empty table
        s.log.debug('Start init connection table')
        items = s._sess.query(Connection).all()
        if len(items) > 0:
            for i in items:
                s._sess.delete(i)
                s.log.debug('Drop connection from {0}'.format(i.raddress))
            s._sess.commit()
        s.log.debug('Connection table crear')

    ## Commit changes to database
    def flush(s):

        # Commit current session
        s._sess.commit()

    ## Insert new connected clients
    def insert(s, clients):

        # Insert to table all clients in list
        for key in clients:

            # Get robot by anchor
            r = s._sess.query(Robot)\
                            .join('container')\
                            .filter(Robot.anchor==key)\
                            .first()

            if not r:
                # robot doesn't exist - skip
                s.log.critical('Robot {0} does NOT exist'.format(key))
                continue

            # Create connection row
            c = Connection(
                since=clients[key]['Connected Since'],
                vaddress=clients[key]['Virtual Address'],
                raddress=clients[key]['Real Address'],
                sent=int(clients[key]['Bytes Sent']),
                received=int(clients[key]['Bytes Received']),
                container=r.container.id
            )

            # Add new item to session
            s.log.info('Append new connection: {0} -> {1}'
                            .format(c.raddress, c.vaddress))
            s._sess.add(c)

    ## Drop disconnected clients
    def drop(s, clients):

        # Drop all clients in list
        for key in clients:

            # Select connection by source IP
            c = s._sess.query(Connection).filter(
                    Connection.raddress == clients[key]['Real Address']
                ).first()

            if not c:
                # nothing to drop - skip
                continue

            # Drop item
            s.log.info('Delete connection from {0}'.format(c.raddress))
            s._sess.delete(c)

    ## Update client connection
    def update(s, clients):

        # Decomposition of clients
        before, after = clients

        # Drop all clients in list
        for key in before:

            # Select connection by source IP
            c = s._sess.query(Connection).filter(
                    Connection.raddress == before[key]['Real Address']
                ).first()

            if not c:
                # nothing to change - skip
                continue

            # Update columns
            c.since = after[key]['Connected Since']
            c.vaddress = after[key]['Virtual Address']
            c.raddress = after[key]['Real Address']
            c.sent = int(after[key]['Bytes Sent'])
            c.received=int(after[key]['Bytes Received'])

            # Update connection information
            s.log.info('Update connection stats: {0} -> {1}'
                            .format(c.raddress, c.vaddress))
            s._sess.add(c)

## Container connector thread
#
#  This thread makes TCP/IP forwarding rules for containers after client connect
#  to this. IP address of client takes from openvpn.status file.
#
class Connector(Thread):

    ## Connected clients dictionary
    clients = {}

    ## The constructor
    def __init__(s):
        Thread.__init__(s)

        # Init logger
        s.log = logging.getLogger('Connector-{0}'.format(s.name))

        # Init firewall tables
        s.f = Firewall(s.log)

        # Init database connection status table
        s.db = Database(s.log)

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
        s.db.insert(diff.added)
        s.db.drop(diff.removed)
        s.db.update(diff.changed)
        s.db.flush()

        # Replace status by new
        s.clients = status.connected_clients

    ## Main cycle
    def run(s):

        # Process inotify events
        s.notifier.loop()

