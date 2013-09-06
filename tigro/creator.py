# -*- coding: utf-8 -*- 
## @package creator
#  LXC-container creator package.
#
#  This package makes new containers.
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from db import DB_CONN_STRING, Container, NewContainer, Robot
from conf import CONFIG_TEMPLATE, ADDRESS_TEMPLATE, LXC_DIR
from threading import Thread
import time, os, logging

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
    def __init__(s, node):
        Thread.__init__(s)

        # Init logger
        s.log = logging.getLogger('Creator-{0}'.format(s.name))
        
        # Create new database connection session
        s._sess = s.Session()

        # Host node where creator runs
        s.node = node

        # Count containers on node
        s.count = len(node.containers)

    ## Container IP generation method
    def genAddress(s, ident):
        # Only two bytes for /16 network, one address reserved for server
        assert (ident < 65535 - 1)
        # Address generates by id as high and low bytes.
        return ADDRESS_TEMPLATE.format(ident / 255, ident % 255)

    ## Container creation method
    def createContainer(s, robot):

        # Generate address for new container
        robot.container.address = s.genAddress(robot.container.id)
        s.log.debug('Gen address {0}'.format(robot.container.address))

        # Set node id
        robot.container.node = s.node.id
        s.log.debug('Append container to node {0}'.format(s.node.name))

        # Commit changes
        s._sess.add(robot.container)
        s._sess.commit()

        # Create target directory
        target = os.path.join(LXC_DIR, robot.anchor)
        try:
            os.makedirs(target)
            s.log.debug('Created directory \'{0}\''.format(target))

        except OSError as e:
            s.log.critical('Cannot create directory: {0}'.format(e))
        
        # Create config from template
        config = s.template.format(anchor=robot.anchor, address=robot.container.address)
        s.log.debug('Gen config with anchor={0} and address={1}'
                        .format(robot.anchor, robot.container.address))

        # Save config file
        file(os.path.join(target, 'config'), 'w').write(config)
        s.log.debug('Saved config file')

        # Inc count of containers
        s.count += 1

    ## Get task from database method
    def getWork(s):

        # Get one work from db
        work = s._sess.query(NewContainer).first()

        if not work:
            # nothing to do
            return None

        # Save container link
        link = work.link
        s.log.debug('New task: conatiner.id={0}'.format(link))

        # Drop work from queue
        s._sess.delete(work)
        s._sess.commit()

        # Return robot from link or None if doesn't exist
        return s._sess.query(Robot)\
                    .join('container')\
                    .filter(Container.id == link).first()

    ## Main cycle
    def run(s):

        # Infinity cycle =)
        while True:

            # Get robot for creation task
            robot = s.getWork()

            if robot is not None:
                # task exist - do create container
                s.createContainer(robot)
                s.log.info('Container for robot {0} created'.format(robot.anchor))

            else:
                # waiting for other tasks
                time.sleep(0.5 + s.count)

