# -*- coding: utf-8 -*- 
## @package db
#  TIGRO database tables defines.
#
#  This package provide declarative tables for working with TIGRO database.
from sqlalchemy import Column, Integer, String, Sequence, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from conf import DB_DRIVER, DB_USER, DB_PASSWORD, DB_HOST, DB_NAME 

## Database connection string
#
#  This is a SQLAlchemy engine connection string.
DB_CONN_STRING = '{0}://{1}:{2}@{3}/{4}'.format(
                DB_DRIVER, DB_USER, DB_PASSWORD, DB_HOST, DB_NAME)

## Declarative database synonym
Base = declarative_base()

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
    
    ## Plugins string TODO: maybe relationship
    plugins = Column(String)

    ## Web-socket port
    wsport = Column(Integer)

    ## Web-socket auth string
    wsauth = Column(String)

## LXC-container table
class Container(Base):

    ## Table name
    __tablename__ = 'container'

    ## Primary key
    id = Column(Integer, Sequence('container_id_seq'), primary_key=True)

    ## Relationship link to robot item
    robot = Column(Integer, ForeignKey('robot.id'))

## New LXC-container table
class NewContainer(Base):

    ## Table name
    __tablename__ = 'new_container'

    ## Primary key
    id = Column(Integer, Sequence('new_container_id_seq'), primary_key=True)

    ## Relationship link to container item
    link = Column(Integer, ForeignKey('container.id'))

