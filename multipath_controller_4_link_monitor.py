from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import arp

from ryu.lib import hub
import json

from collections import defaultdict
from ryu.topology import event
from ryu import utils
from ryu.ofproto import ether


class My_Multipath_13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(My_Multipath_13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.s1_datapath = {}
        self.datapath = {}
        self.datapaths = {}
        self.datapath_list = {}
        self.switches = []
        self.adjacency = defaultdict(dict)
        self.error_link = False
        self.FLAGS = True
        self.i = 0
        self.switch_error = False
        self.error_switch_number = 0
        self.monitor_thread = hub.spawn(self._monitor)
        self.count_thread = hub.spawn(self._count)

    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        switch = ev.switch.dp
        ofp_parser = switch.ofproto_parser

        if switch.id not in self.switches:
            self.switches.append(switch.id)
            self.datapath_list[switch.id] = switch

            # Request port/link descriptions, useful for obtaining bandwidth
            req = ofp_parser.OFPPortDescStatsRequest(switch)
            switch.send_msg(req)

            self.switch_error = False  # switch enter, so flag False
            self.error_switch_number = 0  # setting 0 represent no switch error
            print "Switch", switch.id, "Turn on"
            print "Error Flag is", self.switch_error

    @set_ev_cls(event.EventSwitchLeave, MAIN_DISPATCHER)
    def switch_leave_handler(self, ev):
        print ev
        switch = ev.switch.dp.id
        if switch in self.switches:
            self.switches.remove(switch)
            del self.datapath_list[switch]
            del self.adjacency[switch]

            self.switch_error = True  # switch leave, so flag is True
            if switch == 1:
                self.FLAGS = True  # when s1 enter topology, it can add group
            self.error_switch_number = switch  # assign dpid for recording
            print "Error Flag is", self.switch_error

    @set_ev_cls(event.EventLinkAdd, MAIN_DISPATCHER)
    def link_add_handler(self, ev):
        s1 = ev.link.src
        s2 = ev.link.dst
        self.adjacency[s1.dpid][s2.dpid] = s1.port_no
        self.adjacency[s2.dpid][s1.dpid] = s2.port_no

        self.error_link = False
        print "link_add", s1, s2;

    @set_ev_cls(event.EventLinkDelete, MAIN_DISPATCHER)
    def link_delete_handler(self, ev):
        s1 = ev.link.src
        s2 = ev.link.dst

        self.error_link = True
        print "link delete", s1, s2;

        self.send_group_mod(self.s1_datapath)

        # Exception handling if switch already deleted
        try:
            del self.adjacency[s1.dpid][s2.dpid]
            del self.adjacency[s2.dpid][s1.dpid]
        except KeyError:
            pass

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath

                print "Switch", datapath.id, "Turn on"
                if self.error_switch_number == 2 or \
                   self.error_switch_number == 3 or \
                   self.error_switch_number == 4 or \
                   self.error_switch_number == 5:
                    self.error_switch_number = 0

        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:

                if datapath.id == 1:
                    self.FLAGS = True
                self.switch_error = True
                self.error_switch_number = datapath.id
                print "Switch", datapath.id, "Turn off"

                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self.send_group_mod(dp)
                break
            hub.sleep(20)

    def _count(self):
        while True:
            self.i += 1
            print self.i, "s"
            hub.sleep(1)

    def send_group_mod(self, datapath):
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        ### weight calculation area START ###

        # packet loss calculation
        # set path 1 packet loss is 10%,
        # path 2 is 15%, path 3 is 10%
        WL1 = (1/0.05) / ((1/0.05)+(1/0.05)+(1/0.1)+(1/0.1))
        WL2 = (1/0.05) / ((1/0.05)+(1/0.05)+(1/0.1)+(1/0.1))
        WL3 = (1/0.1) / ((1/0.05)+(1/0.05)+(1/0.1)+(1/0.1))
        WL4 = (1/0.1) / ((1/0.05)+(1/0.05)+(1/0.1)+(1/0.1))
        print "WL1:", WL1, " WL2:", WL2, " WL3:", WL3, " WL4:", WL4;

        WD1 = (1.0/5.0) / ((1.0/5.0)+(1.0/10.0)+(1.0/5.0)+(1.0/10.0))
        WD2 = (1.0/10.0) / ((1.0/5.0)+(1.0/10.0)+(1.0/5.0)+(1.0/10.0))
        WD3 = (1.0/5.0) / ((1.0/5.0)+(1.0/10.0)+(1.0/5.0)+(1.0/10.0))
        WD4 = (1.0/10.0) / ((1.0/5.0)+(1.0/10.0)+(1.0/5.0)+(1.0/10.0))
        print "WD1:", WD1, " WD2:", WD2, " WD3:", WD3, " WD4:", WD4;

        # available bandwidth calculation
        with open("utilization.json", "r") as load_B, \
             open("utilization2.json", "r") as load_B2, \
             open("utilization3.json", "r") as load_B3, \
             open("utilization4.json", "r") as load_B4:

            # load file
            BF1 = json.load(load_B)
            BF2 = json.load(load_B2)
            BF3 = json.load(load_B3)
            BF4 = json.load(load_B4)

            # set path 1 available bandwidth is 100M,
            # path 2 is 60M, path 3 is 50M

            # check which switch is failed
            if self.error_switch_number == 2:
                BF1[0]["metricValue"] = 0.4
                WL1 = (1/1) / ((1/1)+(1/0.05)+(1/0.1)+(1/0.1))
                WL2 = (1/0.05) / ((0)+(1/0.05)+(1/0.1)+(1/0.1))
                WL3 = (1/0.1) / ((0)+(1/0.05)+(1/0.1)+(1/0.1))
                WL4 = (1/0.1) / ((0)+(1/0.05)+(1/0.1)+(1/0.1))
                WL1 = 0

                #WD1 = (1/5) / ((1/5)+(1/10)+(1/5)+(1/10))
                WD1 = 0
                WD2 = (1.0/10.0) / ((0)+(1.0/10.0)+(1.0/5.0)+(1.0/10.0))
                WD3 = (1.0/5.0) / ((0)+(1.0/10.0)+(1.0/5.0)+(1.0/10.0))
                WD4 = (1.0/10.0) / ((0)+(1.0/10.0)+(1.0/5.0)+(1.0/10.0))

            if self.error_switch_number == 3:
                BF2[0]["metricValue"] = 0.3
                WL1 = (1/0.1) / ((1/0.1)+(1/0.15)+(1/0.1)+(1/0.15))
                WL2 = (1/1) / ((1/0.1)+(1/1)+(1/0.1)+(1/0.15))
                WL3 = (1/0.1) / ((1/0.1)+(1/0.15)+(1/0.1)+(1/0.15))
                WL4 = (1/0.15) / ((1/0.1)+(1/0.15)+(1/0.1)+(1/0.15))

            if self.error_switch_number == 4:
                BF3[0]["metricValue"] = 0.2
                WL1 = (1/0.1) / ((1/0.1)+(1/0.15)+(1/0.1)+(1/0.15))
                WL2 = (1/0.15) / ((1/0.1)+(1/0.15)+(1/0.1)+(1/0.15))
                WL3 = (1/1) / ((1/0.1)+(1/0.15)+(1/1)+(1/0.15))
                WL4 = (1/0.15) / ((1/0.1)+(1/0.15)+(1/0.1)+(1/0.15))

            if self.error_switch_number == 5:
                BF4[0]["metricValue"] = 0.1
                WL1 = (1/0.1) / ((1/0.1)+(1/0.15)+(1/0.1)+(1/0.15))
                WL2 = (1/0.15) / ((1/0.1)+(1/0.15)+(1/0.1)+(1/0.15))
                WL3 = (1/0.1) / ((1/0.1)+(1/0.15)+(1/0.1)+(1/0.15))
                WL4 = (1/1) / ((1/0.1)+(1/0.15)+(1/0.1)+(1/1))

            # if link is down
            if self.error_link == True:
                BF1[0]["metricValue"] = 0.4
                WL1 = (1/1) / ((1/1)+(1/0.05)+(1/0.1)+(1/0.1))
                WL2 = (1/0.05) / ((0)+(1/0.05)+(1/0.1)+(1/0.1))
                WL3 = (1/0.1) / ((0)+(1/0.05)+(1/0.1)+(1/0.1))
                WL4 = (1/0.1) / ((0)+(1/0.05)+(1/0.1)+(1/0.1))
                WL1 = 0

                #WD1 = (1/5) / ((1/5)+(1/10)+(1/5)+(1/10))
                WD1 = 0
                WD2 = (1.0/10.0) / ((0)+(1.0/10.0)+(1.0/5.0)+(1.0/10.0))
                WD3 = (1.0/5.0) / ((0)+(1.0/10.0)+(1.0/5.0)+(1.0/10.0))
                WD4 = (1.0/10.0) / ((0)+(1.0/10.0)+(1.0/5.0)+(1.0/10.0))

            WB1 = (0.4-BF1[0]["metricValue"]) / \
                    ((0.4-BF1[0]["metricValue"]) + \
                    (0.3-BF2[0]["metricValue"]) + \
                    (0.2-BF3[0]["metricValue"]) + \
                    (0.1-BF4[0]["metricValue"]))

            WB2 = (0.3-BF2[0]["metricValue"]) / \
                    ((0.4-BF1[0]["metricValue"]) + \
                    (0.3-BF2[0]["metricValue"]) + \
                    (0.2-BF3[0]["metricValue"]) + \
                    (0.1-BF4[0]["metricValue"]))

            WB3 = (0.2-BF3[0]["metricValue"]) / \
                    ((0.4-BF1[0]["metricValue"]) + \
                    (0.3-BF2[0]["metricValue"]) + \
                    (0.2-BF3[0]["metricValue"]) + \
                    (0.1-BF4[0]["metricValue"]))

            WB4 = (0.1-BF4[0]["metricValue"]) / \
                    ((0.4-BF1[0]["metricValue"]) + \
                    (0.3-BF2[0]["metricValue"]) + \
                    (0.2-BF3[0]["metricValue"]) + \
                    (0.1-BF4[0]["metricValue"]))

            print "WB1:", WB1, " WB2:", WB2, " WB3:", WB3, " WB4:", WB4;

        # link weight calculation
        # set weight ratio (WB and WL and WD) is 70/20/10
        W1 = WB1*0.7 + WL1*0.2 + WD1*0.1
        W2 = WB2*0.7 + WL2*0.2 + WD2*0.1
        W3 = WB3*0.7 + WL3*0.2 + WD3*0.1
        W4 = WB4*0.7 + WL4*0.2 + WD4*0.1

        # modify the final link weights
        if self.error_switch_number == 2:
            W1 = 0
            W2 = (int)(W2*100)
            W3 = (int)(W3*100)
            W4 = 100 - (W1+W2+W3)
        if self.error_switch_number == 3:
            W1 = (int)(W1*100)
            W2 = 0
            W3 = (int)(W3*100)
            W4 = 100 - (W1+W2+W3)
        if self.error_switch_number == 4:
            W1 = (int)(W1*100)
            W2 = (int)(W2*100)
            W3 = 0
            W4 = 100 - (W1+W2+W3)
        if self.error_switch_number == 5:
            W4 = 0
            W1 = (int)(W1*100)
            W2 = (int)(W2*100)
            W3 = 100 - (W1+W2+W4)
        if self.error_switch_number == 0:
            if self.error_link == True:
                W1 = 0
                W2 = (int)(W2*100)
                W3 = (int)(W3*100)
                W4 = 100 - (W1+W2+W3)
            else:
                W1 = (int)(W1*100)
                W2 = (int)(W2*100)
                W3 = (int)(W3*100)
                W4 = 100 - (W1+W2+W3)


        print "W1:", W1, " W2:", W2, " W3:", W3, " W4:", W4;
        ### weight calculation area END ###

        # set group table
        port_1 = 2 # origin 3
        queue_1 = ofp_parser.OFPActionSetQueue(0)
        actions_1 = [queue_1, ofp_parser.OFPActionOutput(port_1)]

        port_2 = 3 # origin 2
        queue_2 = ofp_parser.OFPActionSetQueue(0)
        actions_2 = [queue_2, ofp_parser.OFPActionOutput(port_2)]

        port_3 = 4 # adding
        queue_3 = ofp_parser.OFPActionSetQueue(0)
        actions_3 = [queue_3, ofp_parser.OFPActionOutput(port_3)]

        port_4 = 5 # adding
        queue_4 = ofp_parser.OFPActionSetQueue(0)
        actions_4 = [queue_4, ofp_parser.OFPActionOutput(port_4)]

        weight_1 = W1#38 # origin 60
        weight_2 = W2#20 # origin 40
        weight_3 = W3#25 # adding
        weight_4 = W4#17

        watch_port = ofproto_v1_3.OFPP_ANY
        watch_group = ofproto_v1_3.OFPQ_ALL

        buckets = [
            ofp_parser.OFPBucket(weight_1, watch_port, watch_group, actions_1),
            ofp_parser.OFPBucket(weight_2, watch_port, watch_group, actions_2),
            ofp_parser.OFPBucket(weight_3, watch_port, watch_group, actions_3),
            ofp_parser.OFPBucket(weight_4, watch_port, watch_group, actions_4)]

        group_id = 50

        # group table add rule at first
        if self.FLAGS == True:
            req = ofp_parser.OFPGroupMod(datapath, ofproto.OFPFC_ADD,
                                         ofproto.OFPGT_SELECT, group_id,
                                         buckets)
            self.logger.info("ADD_group_mod")
        # after adding rule, group table modify rule
        else:
            req = ofp_parser.OFPGroupMod(datapath, ofproto.OFPFC_MODIFY,
                                         ofproto.OFPGT_SELECT, group_id,
                                         buckets)
            self.logger.info("MODIFY_group_mod")

        datapath.send_msg(req)
        print "weight_1:", weight_1, " weight_2:", weight_2, " weight_3:", weight_3, " weight_4:", weight_4;

    # aware switches originally
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        if self.FLAGS == True and dpid == 1:
            self.send_group_mod(datapath)
            self.FLAGS = False
            self.s1_datapath = datapath
 
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)


        ###add rule for multipath transmission in s1
        if ev.msg.datapath.id == 1:
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser

            match = parser.OFPMatch(in_port=1, eth_type=0x0800,
                                    ipv4_src="10.0.0.1", ipv4_dst="10.0.0.3")
                                    #ip_proto=17, udp_dst=5555)
            actions = [datapath.ofproto_parser.OFPActionGroup(50)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = datapath.ofproto_parser.OFPFlowMod(
                datapath=datapath, match=match, cookie=0,
                command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
                priority=3, instructions=inst)

            datapath.send_msg(mod)

            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=6, eth_type=0x0800,
                                    ipv4_src="10.0.0.2", ipv4_dst="10.0.0.3")
                                    #ip_proto=17, udp_dst=5555)
            actions = [datapath.ofproto_parser.OFPActionGroup(50)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = datapath.ofproto_parser.OFPFlowMod(
                datapath=datapath, match=match, cookie=0,
                command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
                priority=3, instructions=inst)

            datapath.send_msg(mod)
            print "s1 FlowMod is sent"

        ###add rule for multipath transmission in s2     
        if ev.msg.datapath.id == 2:

            #in_port=1,dst=10.0.0.3--->output port:2
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=1, eth_type=0x0800,
                                    ipv4_dst="10.0.0.3")
                                    #ip_proto=17, udp_dst=5555)
            actions = [parser.OFPActionOutput(2)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = datapath.ofproto_parser.OFPFlowMod(
                datapath=datapath, match=match, cookie=0,
                command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
                priority=3, instructions=inst)

            datapath.send_msg(mod)
            print "s2 FlowMod is sent"

        ###add rule for multipath transmission in s3
        if ev.msg.datapath.id == 3:

            #in_port=1,dst=10.0.0.3--->output port:2
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=1, eth_type=0x0800,
                                    ipv4_dst="10.0.0.3")
                                    #ip_proto=17, udp_dst=5555)
            actions = [parser.OFPActionOutput(2)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = datapath.ofproto_parser.OFPFlowMod(
                datapath=datapath, match=match, cookie=0,
                command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
                priority=3, instructions=inst)

            datapath.send_msg(mod)
            print "s3 FlowMod is sent"

        ###add rule for multipath transmission in s4
        if ev.msg.datapath.id == 4:

            #in_port=1,dst=10.0.0.3--->output port:2
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=1, eth_type=0x0800,
                                    ipv4_dst="10.0.0.3")
                                    #ip_proto=17, udp_dst=5555)
            actions = [parser.OFPActionOutput(2)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = datapath.ofproto_parser.OFPFlowMod(
                datapath=datapath, match=match, cookie=0,
                command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
                priority=3, instructions=inst)

            datapath.send_msg(mod)
            print "s4 FlowMod is sent"

        if ev.msg.datapath.id == 5:

            #in_port=1,src=10.0.0.1,dst=10.0.0.3--->output port:2
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=1, eth_type=0x0800,
                                    ipv4_dst="10.0.0.3")
                                    #ip_proto=17, udp_dst=5555)
            actions = [parser.OFPActionOutput(2)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = datapath.ofproto_parser.OFPFlowMod(
                datapath=datapath, match=match, cookie=0,
                command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
                priority=3, instructions=inst)

            datapath.send_msg(mod)
            print "s5 FlowMod is sent"

        if ev.msg.datapath.id == 6:

            #in_port=2,dst=10.0.0.2--->output port:1
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=2, eth_type=0x0800,
                                    ipv4_dst="10.0.0.3")
                                    #ip_proto=17, udp_dst=5555)
            actions = [parser.OFPActionOutput(1)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = datapath.ofproto_parser.OFPFlowMod(
                datapath=datapath, match=match, cookie=0,
                command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
                priority=3, instructions=inst)

            datapath.send_msg(mod)

            #in_port=3,dst=10.0.0.3--->output port:1
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=3, eth_type=0x0800,
                                    ipv4_dst="10.0.0.3")
                                    #ip_proto=17, udp_dst=5555)
            actions = [parser.OFPActionOutput(1)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = datapath.ofproto_parser.OFPFlowMod(
                datapath=datapath, match=match, cookie=0,
                command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
                priority=3, instructions=inst)

            datapath.send_msg(mod)

            #in_port=4,dst=10.0.0.3--->output port:1
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=4, eth_type=0x0800,
                                    ipv4_dst="10.0.0.3")
                                    #ip_proto=17, udp_dst=5555)
            actions = [parser.OFPActionOutput(1)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = datapath.ofproto_parser.OFPFlowMod(
                datapath=datapath, match=match, cookie=0,
                command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
                priority=3, instructions=inst)

            datapath.send_msg(mod)

            #in_port=5,dst=10.0.0.3--->output port:1
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(in_port=5, eth_type=0x0800,
                                    ipv4_dst="10.0.0.3")
                                    #ip_proto=17, udp_dst=5555)
            actions = [parser.OFPActionOutput(1)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
            mod = datapath.ofproto_parser.OFPFlowMod(
                datapath=datapath, match=match, cookie=0,
                command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
                priority=3, instructions=inst)

            datapath.send_msg(mod)
            print "s6 FlowMod is sent"

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
 
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
 
        if buffer_id:
          mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                             priority=priority, match=match,
                             instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                             match=match, instructions=inst)
        datapath.send_msg(mod)

    # mac learning
    def mac_learning(self, dpid, src, in_port):
        self.mac_to_port.setdefault(dpid, {})
        # learn a mac address to avoid FLOOD next time.
        if src in self.mac_to_port[dpid]:
            if in_port != self.mac_to_port[dpid][src]:
                return False
        else:
            self.mac_to_port[(dpid)][src] = in_port
            return True
 
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
 
        pkt = packet.Packet(msg.data)
 
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            match = parser.OFPMatch(eth_type=eth.ethertype)
            actions = []
            self.add_flow(datapath, 1, match, actions)
            return

        if eth.ethertype == ether_types.ETH_TYPE_IPV6:
            match = parser.OFPMatch(eth_type=eth.ethertype)
            actions = []
            self.add_flow(datapath, 1, match, actions)
            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id


        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
        self.mac_learning(dpid, src, in_port)

        arp_pkt = pkt.get_protocol(arp.arp)
        if isinstance(arp_pkt, arp.arp):
            self.logger.debug("ARP processing")
            if self.mac_learning(dpid, src, in_port) is False:
                self.logger.debug("ARP packet enter in different ports")
                return

            out_port = self.mac_to_port[dpid].get(dst)
            if out_port is not None:
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst,
                                        eth_type=eth.ethertype)
                actions = [parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 1, match, actions)

                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out = parser.OFPPacketOut(datapath=datapath,
                                          buffer_id=msg.buffer_id,
                                          in_port=in_port, actions=actions,
                                          data=data)
                datapath.send_msg(out)
                self.logger.debug("Reply ARP to knew host")
                return
            else:
                out_port = ofproto.OFPP_FLOOD
                match = parser.OFPMatch(in_port=in_port, eth_dst=dst,
                                        eth_type=eth.ethertype)
                actions = [parser.OFPActionOutput(out_port)]

                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out = parser.OFPPacketOut(datapath=datapath,
                                          buffer_id=msg.buffer_id,
                                          in_port=in_port, actions=actions,
                                          data=data)
                datapath.send_msg(out)
                return

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD
 
        actions = [parser.OFPActionOutput(out_port)]
 
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
 
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

