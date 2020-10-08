# ryu_multipath
Multipath Transmission in SDN.

This repository using ryu controller implement multipath transminssion in SDN.  
For implement multipath transmission, we need to modify Open vSwitch(OvS) and remake it.  
The Changing includes select function in group table.  
Setting buckets transmission method to implement multipath transmission.  

Reference: https://github.com/saeenali/openvswitch/wiki/Stochastic-Switching-using-Open-vSwitch-in-Mininet

This repository provide ryu controller file and mininet topo file to implement multipath transmission in SDN.  
Before you try this repository, you need to install the environments. (ryu, mininet, openvswitch)  

## Environments
Ubuntu 14.04  
OpenFlow v1.3  
Open vSwitch 2.3.1  
Ryu Controller 3.12  
Mininet 2.2.1 

## Monitor Networks
This repository use sFlow to monitor network performance.  
Using curl cmd to catch the parameter for multipath weights.  
You can use network monitoring tools(NetFlow, sFlow......) or LLDP Packet to monitor network performance.  

The topology has six switch.  

####          --- s2 ---  
#### h2 --    --- s3 ---  
#### h1 -- s1 --- s4 --- s6 -- h3
####          --- s5 ---  
   

## install Ryu Controller
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


## install Open vSwitch

## install Mininet

## Commands
When you installed environment, you can run the cmd to experiment.
  
on ryu controller:  
```
sudo ryu-manager --observe-link multipath_controller_4_link_monitor.py
```
  
on mininet:  
```
sudo mn --custom multipath__topo.py --topo mytopo --controller=remote
```
