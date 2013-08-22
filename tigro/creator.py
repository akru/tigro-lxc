# -*- coding: utf-8 -*- 
## @package creator
#  LXC-container creator package.
#
#  This package makes new containers.
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from threading import Thread
from conf import CONFIG_TEMPLATE, LXC_DIR
from db import *
import time, os

## Container creator thread
#
#  This thread wait for creation tasks in 'new_container' table. New task has a
#  link to container item. 
class Creator(Thread):

    ## Database connection engine
    db = create_engine(DB_CONN_STRING, client_encoding='utf8')

    ## Session class with private engine
    Session = sessionmaker(bind=db)

    ## LXC-config template
    template = file(CONFIG_TEMPLATE).read()

    ## The constructor
    def __init__(s):
        Thread.__init__(s)
        
        # Create new database connection session
        s._sess = s.Session()

    ## Container IP generation method
    def genAddress(s, ident):
        # Only two bytes for /16 network, one address reserved for server
        assert (ident < 65535 - 1)
        # Address generates by id as high and low bytes.
        return '10.10.{0}.{1}'.format(ident / 255, ident % 255)

    ## Container creation method
    def createContainer(s, container):

        # Generate address for new container
        container.ipaddr = s.genAddress(container.id)

        # Save address in session
        s._sess.add(container)
        s._sess.commit()

        # Get robot anchor
        anchor = s._sess.query(Robot.anchor
                        ).filter_by(id=container.robot).first()

        if not anchor:
            # robot doesn't exist =(
            # TODO: maybe exception
            return None

        else:
            # get anchor string from tuple
            anchor = anchor[0]

        # Create target directory
        target = os.path.join(LXC_DIR, anchor)
        os.makedirs(target)
        
        # Create config from template
        config = s.template.format(anchor=anchor, ipaddr=container.ipaddr)

        # Save config file
        file(os.path.join(target, 'config'), 'w').write(config)

    ## Get task from database method
    def getWork(s):

        # Get one work from db
        work = s._sess.query(NewContainer).first()

        if not work:
            # nothing to do
            return None

        # Save container link
        link = work.link

        # Drop work from queue
        s._sess.delete(work)
        s._sess.commit()

        # Return container from link or None if doesn't exist
        return s._sess.query(Container).filter_by(id=link).first()

    ## Main cycle
    def run(s):

        # Infinity cycle =)
        while True:

            # Get container for creation task
            container = s.getWork()

            if container:
                # task exist - do create container
                s.createContainer(container)

            else:
                # waiting for other tasks
                time.sleep(0.5)

