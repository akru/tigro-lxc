# -*- coding: utf-8 -*- 
## @package creator
#  LXC-container creator package.
#
#  This package makes new containers.
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from db import DB_CONN_STRING, Container, NewContainer, Robot, Node
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
    def __init__(s, nodename):
        Thread.__init__(s)

        # Init logger
        s.log = logging.getLogger('Creator-{0}'.format(s.name))

        # Create new database connection s._session
        s._sess = s.Session()

        # Save node name
        s.nodename = nodename

        # Count containers on node
        s.count = len(s._sess.query(Node).\
                        filter_by(name = nodename).\
                        first().containers)
        s._sess.close()

    ## Container IP generation method
    def genAddress(s, ident):
        # Only two bytes for /16 network, one address reserved for server
        assert (ident < 65535 - 1)
        # Address generates by id as high and low bytes.
        return ADDRESS_TEMPLATE.format(ident / 255, ident % 255)

    ## Container creation method
    def createContainer(s, robotid):

        # Generate address for new container
        robot = s._sess.query(Robot)\
                    .join('container')\
                    .filter_by(id = robotid).first()
        robot.container.address = s.genAddress(robot.container.id)
        s.log.debug('Gen address {0}'.format(robot.container.address))

        # Set node id
        robot.container.node = s._sess.query(Node).\
                        filter_by(name = s.nodename).\
                        first().id
        s.log.debug('Append container to node {0}'.format(s.nodename))

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

        # Drop work from queue safely
        try:
            s._sess.delete(work)
            s._sess.commit()
        except:
            # Rollback the changes
            s._sess.rollback()
            return None

        # Return robot id from link or None if doesn't exist
        robot = s._sess.query(Robot)\
                    .filter_by(id = link).first()

        if robot:
            return int(robot.id)
        else:
            return None

    ## Main cycle
    def run(s):

        # Infinity cycle =)
        while True:
            # Create new database connection s._session
            s._sess = s.Session()

            # Get robot for creation task
            robot = s.getWork()

            if robot is not None:
                # task exist - do create container
                s.createContainer(robot)
                s.log.info('Container for robot {0} created'.format(robot))

            else:
                # waiting for other tasks
                s._sess.close()
                time.sleep(5 + s.count)

