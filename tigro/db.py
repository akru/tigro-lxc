# -*- coding: utf-8 -*- 
## @package db
#  TIGRO database tables defines.
#
#  This package provide declarative tables for working with TIGRO database.
from sqlalchemy import Column, Integer, String, Sequence, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from conf import DB_DRIVER, DB_USER, DB_PASSWORD, DB_HOST, DB_NAME 

## Database connection string
#
#  This is a SQLAlchemy engine connection string.
DB_CONN_STRING = '{0}://{1}:{2}@{3}/{4}'.format(
                DB_DRIVER, DB_USER, DB_PASSWORD, DB_HOST, DB_NAME)

## Declarative database synonym
Base = declarative_base()

## TIGRO-node server table
class Node(Base):

    ## Table name
    __tablename__ = 'node'

    ## Primary key
    id = Column(Integer, Sequence('node_id_seq'), primary_key=True)

    ## Node name
    name = Column(String)

    ## Node address
    address = Column(String)

    ## Relationship link to containers placed on
    containers = relationship("Container")

    ## Relationship link to containers placed on
    connections = relationship("Connection")

## Robot table
class Robot(Base):

    ## Table name
    __tablename__ = 'robot'

    ## Primary key
    id = Column(Integer, Sequence('robot_id_seq'), primary_key=True)
    
    ## Robot name
    name = Column(String)

    ## Anchor string
    anchor = Column(String)

    ## Relationship link to user item
    owner = Column(Integer, ForeignKey('user.id'))
    
    ## Plugins json string
    plugins = Column(String)

    ## Web-socket port
    wsport = Column(Integer)

    ## Web-socket auth string
    wsauth = Column(String)

    ## Relationship link to container
    container = relationship("Container", uselist=False)

## LXC-container table
class Container(Base):

    ## Table name
    __tablename__ = 'container'

    ## Primary key
    id = Column(Integer, Sequence('container_id_seq'), primary_key=True)

    ## Relationship link to robot item
    robot = Column(Integer, ForeignKey('robot.id'))

    ## Relationship link to node item
    node = Column(Integer, ForeignKey('node.id'))

    ## Container IP address
    address = Column(String)

    ## Relationship link to connection
    connection = relationship("Connection")

## New LXC-container queue
class NewContainer(Base):

    ## Table name
    __tablename__ = 'new_container'

    ## Primary key
    id = Column(Integer, Sequence('new_container_id_seq'), primary_key=True)

    ## Relationship link to container item
    link = Column(Integer, ForeignKey('container.id'))

## Connection status table
class Connection(Base):

    ## Table name
    __tablename__ = 'connection'

    ## Primary key
    id = Column(Integer, Sequence('connection_id_seq'), primary_key=True)

    ## Relationship link to container item
    container = Column(Integer, ForeignKey('container.id'))

    ## Relationship link to node item
    node = Column(Integer, ForeignKey('node.id'))

    ## Connection since string
    since = Column(String)

    ## Client virtual address
    vaddress = Column(String)

    ## Client real address
    raddress = Column(String)

    ## Bytes sent
    sent = Column(Integer)

    ## Bytes received
    received = Column(Integer)

