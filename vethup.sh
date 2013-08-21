#!/bin/sh
# Virtual ethernet configuration script
#  USAGE: vethup.sh [ veth name ] [ vm address ]
#

ifconfig $1 10.10.255.254/16
ip route add $2 dev $1

