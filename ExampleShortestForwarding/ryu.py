from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import arp
from ryu.lib.packet import ipv4
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link, get_host
import networkx as nx


class SimpleShortestForwarding(app_manager.RyuApp):
    """docstring for SimpleShortestForwarding"""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleShortestForwarding, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        self.host_mac = []
        self.ip_host_mac = {}
        self.network=nx.DiGraph()
        self.mac_to_port = {}
        self.paths = {}
        self.datapaths = {}
        self.mac_to_dpid = {}
        self.initial = True
        self.show_or_not = True


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        # install the table-miss flow entry.
        match = ofp_parser.OFPMatch()
        actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)


    @set_ev_cls(ofp_event.EventOFPStateChange,[MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if not datapath.id in self.datapaths:
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                del self.datapaths[datapath.id]


    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                            actions)]
        mod = ofp_parser.OFPFlowMod(datapath=datapath, priority=priority,
                               match=match, instructions=inst)
        datapath.send_msg(mod)


    def get_topology( self ):

        # get switches and store them into self.network
        switch_list = get_switch(self.topology_api_app, None)   
        switches=[switch.dp.id for switch in switch_list]
        self.network.add_nodes_from(switches)

    
        # get links and store them into self.network
        links_list = get_link(self.topology_api_app, None)

        for link in links_list:
            self.network.add_edge(link.src.dpid,link.dst.dpid)
            self.network.add_edge(link.dst.dpid,link.src.dpid)
            self.mac_to_port[(link.src.dpid,link.dst.dpid)] = link.src.port_no
            self.mac_to_port[(link.dst.dpid,link.src.dpid)] = link.dst.port_no


		# get links and store them into self.network
        hosts_list = get_host(self.topology_api_app, None)

        self.host_mac = []
        for host in hosts_list:
            if host.mac not in self.host_mac:
                self.host_mac.append(host.mac)
            self.network.add_edge(host.port.dpid,host.mac)
            self.network.add_edge(host.mac,host.port.dpid)
            self.mac_to_port[(host.port.dpid,host.mac)] = host.port.port_no
            self.mac_to_dpid[host.mac] = host.port.dpid

        if self.show_or_not:
            print '**********************************topology*****************************************'
            print 'switches: ',self.network.nodes()
            print 'links: ',self.network.edges()
            print 'hosts: ',self.host_mac


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        #self.get_topology()
        #initial data
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        arp_pkt = pkt.get_protocol(arp.arp)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)

        in_port = msg.match['in_port']

        #Get the IP networks
        if arp_pkt:
            if self.initial:
            	self.get_topology()
            	self.initial = False

            arp_src_ip = arp_pkt.src_ip
            arp_dst_ip = arp_pkt.dst_ip
            if arp_pkt.src_ip not in self.ip_host_mac.keys():
                self.ip_host_mac[arp_pkt.src_ip] = arp_pkt.src_mac
                self.network.add_edge(arp_pkt.src_ip,datapath.id)
                self.network.add_edge(datapath.id,arp_pkt.src_ip)
                #if self.show_or_not:
	            #    print 'nodes: ',self.network.nodes()
	            #    print 'network: ',self.network.edges()


        #Forward IP packages
        if ip_pkt:
            if len(pkt.get_protocols(ethernet.ethernet)):
                eth_type = pkt.get_protocols(ethernet.ethernet)[0].ethertype
                self.ip_install_path(ip_pkt.src, ip_pkt.dst, ofp_parser, msg.buffer_id, eth_type)

        #Forward ARP packages
        if arp_pkt:
            arp_src_ip = arp_pkt.src_ip
            arp_dst_ip = arp_pkt.dst_ip
            if arp_src_ip in self.ip_host_mac.keys() and arp_dst_ip in self.ip_host_mac.keys():
            	self.arp_install_path(arp_src_ip, arp_dst_ip, ofp_parser, msg.buffer_id, datapath, in_port)
            else:
            	#self.show_varible()
            	self.flood(msg)


    def ip_install_path(self, src, dst, ofp_parser, buffer_id, eth_type):
    	print 'Processing IP package:'
        path = nx.shortest_path(self.network,src,dst) 
        print 'path: ',path
        path[0] = self.ip_host_mac[path[0]]
        path[len(path)-1] = self.ip_host_mac[path[len(path)-1]]
        print 'path: ',path

        for i in range(1,len(path)-1):
            dpid = path[i]
            out_port = self.mac_to_port[(dpid,path[i+1])]
            in_port = self.mac_to_port[(dpid,path[i-1])]
            datapath = self.datapaths[dpid]

            #install forward flow
            actions_forward = [ofp_parser.OFPActionOutput(out_port)]
            match_forward = ofp_parser.OFPMatch(in_port=in_port, eth_type=eth_type,
                    ipv4_src=src, ipv4_dst=dst)
            self.add_flow(datapath, 1, match_forward, actions_forward)

            #install backward flow
            actions_backward = [ofp_parser.OFPActionOutput(in_port)]
            match_backward = ofp_parser.OFPMatch(in_port=out_port, eth_type=eth_type,
                    ipv4_src=dst, ipv4_dst=src)
            self.add_flow(datapath, 1, match_backward, actions_backward)

            #send packages
            out = ofp_parser.OFPPacketOut(
                datapath=datapath,buffer_id=buffer_id,in_port=in_port,
                actions=actions_forward)
            datapath.send_msg(out)


    def arp_install_path(self, src, dst, ofp_parser, buffer_id, datapath ,in_port):
    	print 'Processing ARP package:'

    	dpid =datapath.id

        path = nx.shortest_path(self.network,src,dst) 
        print 'path: ',path
        path[0] = self.ip_host_mac[path[0]]
        path[len(path)-1] = self.ip_host_mac[path[len(path)-1]]
        #print 'path: ',path,'dpid: ',dpid,'next_hop index: ',path.index(dpid)+1
        print 'path: ',path,'dpid: ',dpid

        if dpid in path:
            next_hop = path[path.index(dpid)+1]

            out_port = self.mac_to_port[(dpid,next_hop)]

            actions = [ofp_parser.OFPActionOutput(out_port)]
            out = ofp_parser.OFPPacketOut(
                datapath=datapath,buffer_id=buffer_id,in_port=in_port,
                actions=actions)
            datapath.send_msg(out)


    def flood(self, msg):

        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        for mac in self.host_mac:
        	port = 1
        	#print 'all: ',self.host_mac
        	#print 'part: ',self.ip_host_mac.values()
        	if mac not in self.ip_host_mac.values():
        		#print 'mac: ',mac
        		datapath = self.datapaths[self.mac_to_dpid[mac]]
        		#print 'dpid: ',self.mac_to_dpid[mac]

        		port = self.mac_to_port[(self.mac_to_dpid[mac],mac)]


        		print 'dpid: ',datapath.id,'port: ',port

                out = self._build_packet_out(datapath, ofproto.OFP_NO_BUFFER, ofproto.OFPP_CONTROLLER, port, msg.data)
                datapath.send_msg(out)




    def _build_packet_out(self, datapath, buffer_id, src_port, dst_port, data):
        """
            Build packet out object.
        """
        actions = []
        if dst_port:
            actions.append(datapath.ofproto_parser.OFPActionOutput(dst_port))

        msg_data = None
        if buffer_id == datapath.ofproto.OFP_NO_BUFFER:
            if data is None:
                return None
            msg_data = data

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=buffer_id,
            data=msg_data, in_port=src_port, actions=actions)
        return out

    def show_varible(self):
    	print 'host_mac: ',self.host_mac
    	print 'ip_host_mac: ',self.ip_host_mac
    	print 'network_edges: ',self.network.edges()
    	print 'network_nodes: ',self.network.nodes()
    	print 'mac_to_port: ',self.mac_to_port
    	print 'paths: ',self.paths
    	print 'datapaths: ',self.datapaths
    	print 'mac_to_dpid: ',self.mac_to_dpid

