# -*- coding: utf-8 -*- 
## @package conf
#  TIGRO configuration file.
#
#  This file contain some configuration details.

## LXC-containers directory
LXC_DIR = '/lxc'

## LXC-container config template
#
#  This is template config file for LXC container.
#  Template accept two arguments: anchor and ipaddr for new container.
CONFIG_TEMPLATE = '{0}/config.template'.format(LXC_DIR)

## Database name
DB_NAME = 'tigro'

## Database user
DB_USER = 'akru'

## Database password
DB_PASSWORD = 'akru'

## Database host
DB_HOST = 'localhost'

## Database driver
DB_DRIVER = 'postgresql+psycopg2'
