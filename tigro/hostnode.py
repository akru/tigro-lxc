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

        # Create database session
        s._sess = s.Session()

        # Get node by name
        node = s._sess.query(Node).filter_by(name=nodename).first()

        if node is not None:
            # node exist - save them
            s.node = node

            # update IP address
            s.node.address = s.address

        else:
            s.node = Node(name=nodename, address=s.address)

        # Commit changes
        s._sess.add(s.node)
        s._sess.commit()

    ## Main cycle
    def run(s):

        s.log.info('Started host node {0} on {1}'.format(s.node.name, s.node.address))

        # Make some count of creator
        for i in range(0, s.creators):

            # Create instance
            creator = Creator(s.node)

            # Run thread
            creator.start()

            # Logging
            s.log.info('Started creator thread: {0}'.format(creator.name))

