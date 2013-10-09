# -*- coding: utf-8 -*- 
## @package connection
#  OpenVPN connection status.
#
#  This package exports information about OpenVPN connections to database.
from db import Connection, Robot, Node

## Connection status class 
#
#  This class provide access to connection status table.
class ConnectionStatus:

    ## The constructor
    def __init__(s, logger, session, nodename):

        # Save logger
        s.log = logger

        # Save database connection session
        s.db = session
        s.db_changed = False

        # Save node id
        s.nodeid = s.db.query(Node).filter_by(name = nodename).first().id

        # Init empty table
        s.log.debug('Init connection table')
        items = s.db.query(Connection).filter_by(node = s.nodeid).all()
        if len(items) > 0:
            for i in items:
                s.db.delete(i)
                s.log.debug('Drop connection from {0}'.format(i.raddress))
            s.db.commit()
        s.log.debug('Connection table crear')

    ## Commit changes to database
    def commit(s):

        # Commit current session
        if s.db_changed:
            s.db.commit()
            s.db_changed = False

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
                container = r.container.id,
                node      = s.nodeid
            )

            # Add new item to session
            s.log.info('Append new connection: {0} -> {1}'
                            .format(c.raddress, c.vaddress))
            s.db.add(c)
            s.db_changed = True

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
            s.db_changed = True

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
            s.log.debug('Update connection stats: {0} -> {1}'
                            .format(c.raddress, c.vaddress))
            s.db.add(c)
            s.db_changed = True

