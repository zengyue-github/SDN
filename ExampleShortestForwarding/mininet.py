#!/usr/bin/python

"""
Create a 1024-host network, and run the CLI on it.
If this fails because of kernel limits, you may have
to adjust them, e.g. by adding entries to /etc/sysctl.conf
and running sysctl -p. Check util/sysctl_addon.
"""
from mininet.node import Controller, RemoteController
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.node import OVSSwitch
from mininet.link import Link, Intf, TCLink
from mininet.topo import Topo

class TreeTopo( Topo ):

    def build( self, pod ,bw_core ,bw_agg ,bw_edge ):
        self.Test( pod ,bw_core ,bw_agg ,bw_edge )

    def Test( self ,pod ,bw_core ,bw_agg ,bw_edge ):
        H_num = pod**3/4
        C_num = pod**2/4
        A_num = pod**2/2
        E_num = pod**2/2
        S_num = C_num + A_num + E_num
        P_num = pod/2
        Link_list = []

        for i in range(0 ,H_num ):
            self.addHost('h'+str(i+1))

        for i in range(0 ,S_num ):
            self.addSwitch('s'+str(i+1))


        for i in range(0 ,P_num ):
            for j in range(1 ,P_num+1 ):
                for k in range(0 ,pod ):
                    self.addLink('s'+str(i*(pod/2)+j),'s'+str(C_num+k*(pod/2)+i+1), bw=bw_core )

        for i in range(0 ,pod):
            for j in range(0 ,P_num):
                for k in range(0 ,P_num):
                    self.addLink('s'+str(C_num+j+i*P_num+1),'s'+str(C_num+A_num+k+i*P_num+1), bw=bw_agg)

        for i in range(0 ,E_num ):
            for j in range(1,P_num+1):
                self.addLink('s'+str(C_num + A_num + i +1),'h'+str(2*i+j), bw=bw_edge)


if __name__ == '__main__':
    setLogLevel( 'info' )
    network = TreeTopo(pod=4 ,bw_core=1 ,bw_agg=1 ,bw_edge=1 )

    net = Mininet(topo=network, link=TCLink, controller=None)
    net.addController('controller', controller=RemoteController, ip='0.0.0.0', port=6653)
    net.start()

    CLI(net)
    net.stop()
