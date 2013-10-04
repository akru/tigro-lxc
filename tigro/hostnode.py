# -*- coding: utf-8 -*- 
## @package hostnode 
#  TIGRO host nodes package.
#
#  This package provide interface to TIGRO host nodes.
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from db import DB_CONN_STRING, Node
from connector import Connector
from creator import Creator
from threading import Thread
import socket, logging

## Host node class
#
#  This class register node on main database and start creators and connector.
class HostNode(Thread):

    ## Database connection engine
    db = create_engine(DB_CONN_STRING, client_encoding='utf8')

    ## Session class with private engine
    Session = sessionmaker(bind=db)

    ## Host node IP address
    address = socket.gethostbyname(socket.gethostname())

    ## The constructor
    #  @param nodename Host node name in the database.
    #  @param creators Count of creator threads to start.
    def __init__(s, nodename = socket.gethostname(), creators = 1):
        Thread.__init__(s)

        s.log = logging.getLogger('HostNode-{0}'.format(s.name))

        # Save count of creators
        s.creators = creators

        # Save node name
        s.nodename = nodename

        # Create database session
        sess = s.Session()

        # Get node by name
        node = sess.query(Node).filter_by(name=nodename).first()

        if node is not None:
            # update IP address
            node.address = s.address

        else:
            node = Node(name=nodename, address=s.address)

        # Commit changes
        sess.add(node)
        sess.commit()

    ## Main cycle
    def run(s):

        s.log.info('Started host node {0} on {1}'.format(s.nodename, s.address))

        # Make some count of creator
        for i in range(0, s.creators):

            # Create instance
            creator = Creator(s.nodename)

            # Run thread
            creator.start()

            # Logging
            s.log.info('Started creator thread: {0}'.format(creator.name))

        # Make connector
        connector = Connector(s.nodename)

        # Run connector thread
        connector.start()

        # Logging
        s.log.info('Started connector thread: {0}'.format(connector.name))
