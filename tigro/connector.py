# -*- coding: utf-8 -*- 
## @package connector
#  LXC-container connector package.
#
#  This package makes firewall rules for LXC-containers.
from pyinotify import WatchManager, Notifier, ProcessEvent, IN_MODIFY
from db import Connection, DB_CONN_STRING
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from parser import OpenVPNStatusParser
from conf import OPENVPN_STATUS_FILE
from dictdiffer import DictDiffer
from threading import Thread
import time

## Firewall controller class
class Firewall:

    ## The constructor
    def __init__(s):
        pass

    ## Firewall rule creator method
    def createRules(s, clients):

        if not clients:
            # nothing to create
            return

        print "Create rules for:", clients

    ## Firewall rule remover method
    def deleteRules(s, clients):

        if not clients:
            # nothing to delete
            return

        print "Delete rules for:", clients

## Database connector
#
#  This class provide access to connection status table.
class Database:

    ## Database connection engine
    db = create_engine(DB_CONN_STRING, client_encoding='utf8')

    ## Session class with private engine
    Session = sessionmaker(bind=db)

    ## The constructor
    def __init__(s):

        # Create new database connection session
        s._sess = s.Session()

        # Init empty table
        a = s._sess.query(Connection).all()
        if len(a) > 0:
            s._sess.delete(a)
            s._sess.commit()

    def insert(s, clients):

        # Insert to table all clients in list
        for client in clients:
            pass

    def drop(s, clients):
        pass

    def update(s, clients):
        pass

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

        # Init firewall tables
        s.f = Firewall()

        # Init database connection status table
        s.db = Database()

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

        # Replace status by new
        s.clients = status.connected_clients

    ## Main cycle
    def run(s):

        # Process inotify events
        s.notifier.loop()

