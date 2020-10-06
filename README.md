# ryu_multipath
Multipath Transmission in SDN.

This repository using ryu controller implement multipath transminssion in SDN.  
For implement multipath transmission, we need to modify Open vSwitch(OvS) and remake it.  
The Changing includes select function in group table.  
Setting buckets transmission method to implement multipath transmission.  

Reference: https://github.com/saeenali/openvswitch/wiki/Stochastic-Switching-using-Open-vSwitch-in-Mininet

### Monitor Networks

You can use network monitoring tools(NetFlow, sFlow......) or LLDP Packet to monitor network performance.


## Environments
Ubuntu 14.04  
OpenFlow v1.3  
Open vSwitch 2.3.1  
Ryu Controller 3.12  
Mininet 2.2.1  

## install ryu controller
Quickly Install  
```
pip install ryu
```

installing from source code  
```
git clone git://github.com/osrg/ryu.git
cd ryu; python ./setup.py install
```


Reference: https://ryu-sdn.org/

## Commands
When you installed environment, you can run the cmd to experiment.
  
on ryu controller:  
```
sudo ryu-manager --observe-link multipath_controller_link_monitor.py
```
  
on mininet:  
```
sudo mn --custom multipath_topo.py --topo mytopo --controller=remote
```
