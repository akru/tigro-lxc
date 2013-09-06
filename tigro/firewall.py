# -*- coding: utf-8 -*- 
## @package firewall 
#  TIGRO firewall package.
#
#  This package makes firewall rules for LXC-containers.
from netfilter.rule import Rule, Match, Target
from netfilter.table import Table
from db import Robot, DB_CONN_STRING
from conf import GATEWAY_ADDRESS, WS_START_PORT

## WebSocket port generator
class PortGenerator:

    ## The constructor
    def __init__(s, start_port):

        # Init zero count of ports
        s.ports = 0

        # Save start port
        s.start = start_port

    def gen(s):

        # Inc count of ports
        s.ports += 1

        return  s.start + s.ports

## Firewall controller class
class Firewall:

    ## The constructor
    def __init__(s, logger, session):

        # Save logger
        s.log = logger

        # Save database connection session
        s.db = session

        # Purge NAT table
        s.log.debug('Init NAT firewall table')
        s.table = Table('nat')
        s.table.flush_chain()
        s.table.delete_chain()

        # Init port generator
        s.ws_port = PortGenerator(WS_START_PORT)

        # Init rules dictionary
        s.rules = {}

    ## Firewall rule creator method
    def createRules(s, clients):

        # Create firewall rules for all connections
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

            # Get virtual address of client from dict
            vaddress = clients[key]['Virtual Address']

            # Gen WebSocket port
            r.wsport = s.ws_port.gen()
            s.log.debug('Gen WebSocket port {0} for robot {1}'
                            .format(r.wsport, key))

            # Save container external WebSocket port in database
            s.db.add(r)
            s.db.commit()

            # Make client firewall rules
            s.log.info('Create firewall rule for: {0} -> {1}'
                            .format(vaddress, r.container.address))
            client_rule = Rule(
                protocol     = 'tcp',
                destination  = r.container.address,
                source       = vaddress,
                in_interface = 'tun0',
                jump         = Target('DNAT', '--to-destination {0}'.format(r.container.address))
            )

            # Make container firewall rules
            s.log.info('Create firewall rule for: {0} <- {1}'
                            .format(vaddress, r.container.address))
            container_rule = Rule(
                protocol     = 'tcp',
                source       = r.container.address,
                destination  = vaddress,
                in_interface = 'veth.{0}'.format(r.anchor),
                jump         = Target('DNAT', '--to-destination {0}'.format(vaddress))
            )
            master_rule = Rule(
                protocol     = 'tcp',
                source       = r.container.address,
                destination  = GATEWAY_ADDRESS,
                in_interface = 'veth.{0}'.format(r.anchor),
                matches      = [ Match('tcp', '--dport 11311') ],
                jump         = Target('DNAT', '--to-destination {0}:11311'.format(vaddress))
            )

            s.log.info('Create firewall rule for: WebSocket -> {0}'
                            .format(r.container.address))
            websock_rule = Rule(
                protocol     = 'tcp',
                matches      = [ Match('tcp', '--dport {0}'
                                                .format(r.wsport)) ],
                jump         = Target('DNAT', '--to-destination {0}:9090'
                                                .format(r.container.address))
            )

            # Append rules to table
            s.table.append_rule('PREROUTING', client_rule)
            s.table.append_rule('PREROUTING', container_rule)
            s.table.append_rule('PREROUTING', master_rule)
            s.table.append_rule('PREROUTING', websock_rule)

            # Append rules to internal list
            s.rules[r.anchor] = {
                            'client': client_rule,
                            'container': container_rule,
                            'master': master_rule,
                            'websock': websock_rule }


    ## Firewall rule remover method
    def deleteRules(s, clients):

        # Delete firewall rules for clients in list
        for key in clients:

            # Delete rules from table
            s.log.info('Delete firewall rule for: {0} -> {1}'
                            .format(s.rules[key]['client'].source,
                                    s.rules[key]['client'].destination))
            s.table.delete_rule('PREROUTING', s.rules[key]['client'])

            s.log.info('Delete firewall rule for: {0} <- {1}'
                            .format(s.rules[key]['container'].destination,
                                    s.rules[key]['container'].source))
            s.table.delete_rule('PREROUTING', s.rules[key]['container'])
            s.table.delete_rule('PREROUTING', s.rules[key]['master'])

            s.log.info('Delete firewall rule for: WebSocket -> {0}'
                                    .format(s.rules[key]['container'].source))
            s.table.delete_rule('PREROUTING', s.rules[key]['websock'])

            # Delete rules from internal list
            s.rules.pop(key)

