# ryu_multipath
Multipath Transmission in SDN.

This repository using ryu controller implement multipath transminssion in SDN.
For implement multipath transmission, we need to modify Open vSwitch(OvS) and remake it.
The Changing includes select function in group table.
Setting buckets transmission method to implement multipath transmission.

Reference: https://github.com/saeenali/openvswitch/wiki/Stochastic-Switching-using-Open-vSwitch-in-Mininet

# Environments
Ubuntu 14.04
OpenFlow v1.3
Open vSwitch 2.3.1
Ryu Controller 3.12
