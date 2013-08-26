#!/bin/sh
# Virtual ethernet configuration script
#  USAGE: vethup.sh [ veth name ] [ vm address ] [ gw address ]
#

ifconfig $1 $3
ip route add $2 dev $1

