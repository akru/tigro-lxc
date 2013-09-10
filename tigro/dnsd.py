# -*- coding: utf-8 -*- 
## @package dnsd 
#  TIGRO DNS daemon configurator.
#
#  This package provide interface for DNS daemon.
from conf import DNSD_CONFIG
from subprocess import Popen
from db import Robot
import io

## DNS daemon class
#
#  This class provide methods for update DNS names.
class DNSDaemon:

    ## The constructor
    def __init__(s, logger, session):

        # Save logger
        s.log = logger

        # Save database connection session
        s.db = session

        # Init empty records list
        s.records = {}
        
        s._restart = False

    ## Append address to config
    def append(s, clients):

        # Create dns records for all connections
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

            # Append record
            s.log.info("Create DNS record for: lxc-{0}".format(key))
            s.records['lxc-{0}'.format(key)] = r.container.address

            # Up restart flag
            s._restart = True

    ## Remove address from config
    def delete(s, clients):

        # Create dns records for all connections
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
            
            # Drop record
            s.log.info("Delete DNS record for: lxc-{0}".format(key))
            s.records.pop('lxc-{0}'.format(key))

            # Up restart flag
            s._restart = True

    ## Restart DNS daemon with new config file
    def restart(s):

        if not s._restart:
            # No records changed
            return

        # Down restart flag
        s._restart = False

        # Generate new config
        config = s._gen_config()

        # Restart daemon
        dns = Popen(['/etc/init.d/dnsmasq', 'restart'])
        dns.wait()
        s.log.debug('DNS daemon restarted with hosts: {0}'.format(config))

    ## DNS config file generator
    def _gen_config(s):

        # Open config file
        try:
            config = io.open(DNSD_CONFIG, 'w')

        except OSError as e:
            s.log.critical('Can not open DNSD config file: {0}'.format(e))

        s.log.debug('DNS config open file: {0}'.format(config.name))

        # For any record from records
        for name in s.records:
            # Write formatted string
            config.write(unicode('{0}  {1}\n'.format(s.records[name], name)))
            s.log.debug('DNS config write item: {0}'.format(name))

        return config.name
