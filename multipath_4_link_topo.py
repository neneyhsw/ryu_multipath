#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.util import dumpNodeConnections

class MyTopo(Topo):
    "Simple topology example."

    def __init__(self):
        "Create custom topo."

        # Initialize topology
        Topo.__init__(self)

        # Add hosts and switches
        Host1 = self.addHost('h1', mac='00:00:00:00:00:01')
        Host2 = self.addHost('h2', mac='00:00:00:00:00:02')
        Host3 = self.addHost('h3', mac="00:00:00:00:00:03")
        Switch1 = self.addSwitch('s1')
        Switch2 = self.addSwitch('s2')
        Switch3 = self.addSwitch('s3')
        Switch4 = self.addSwitch('s4')
        Switch5 = self.addSwitch('s5')
        Switch6 = self.addSwitch('s6')

        # Add links
        self.addLink(Switch1, Host1, 1)#, cls=TCLink, bw=200)
        self.addLink(Switch1, Host2, 6)#, cls=TCLink, bw=200)
        self.addLink(Switch1, Switch2, 2, 1, cls=TCLink, bw=40,
                                             loss=5, delay='5ms') 
        self.addLink(Switch1, Switch3, 3, 1, cls=TCLink, bw=30,
                                             loss=5, delay='10ms')
        self.addLink(Switch1, Switch4, 4, 1, cls=TCLink, bw=20,
                                             loss=10, delay='5ms')
        self.addLink(Switch1, Switch5, 5, 1, cls=TCLink, bw=10,
                                             loss=10, delay='10ms')

        self.addLink(Switch2, Switch6, 2, 2)#, cls=TCLink, bw=200)
        self.addLink(Switch3, Switch6, 2, 3)#, cls=TCLink, bw=200)
        self.addLink(Switch4, Switch6, 2, 4)#, cls=TCLink, bw=200)
        self.addLink(Switch5, Switch6, 2, 5)#, cls=TCLink, bw=200)
        self.addLink(Switch6, Host3, 1)#, cls=TCLink, bw=200)


topos = {'mytopo': (lambda: MyTopo() ) }

