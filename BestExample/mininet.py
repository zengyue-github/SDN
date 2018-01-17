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

    def build( self, pod, bw_core, bw_agg, bw_edge ):
        self.switch_num = 1
        self.host_num = 1

        x = input("Please choose a topology: 0.Test; 1.Tree; 2.FatTree; 3.VL2; 4.Bcube; 5.Dcell\n:")

        if x == 0:
        	self.FatTree( 4, 1, 1, 1 )
        if x == 1:
        	depth = input("depth: ")
        	fanout = input("fanout: ")
        	tbw = input("bandwidth: ")
        	self.Tree( depth, fanout, tbw )

        if x == 2:
        	pod = input("pod: ")
        	bw_core = input("bw_core: ")
        	bw_agg = input("bw_agg: ")
        	bw_edge = input("bw_edge: ")
        	self.FatTree( pod, bw_core, bw_agg, bw_edge )

        if x == 3:
        	DA = input("DA: ")
        	DI = input("DI: ")
        	density = input("density: ")
        	bw_switch = input("bw_switch: ")
        	bw_host = input("bw_host: ")
        	self.VL2( DA, DI, density, bw_switch, bw_host )

        if x == 4:
        	n = input("n: ")
        	k = input("k: ")
        	bw_all = input("bw_all: ")
        	self.Bcube( n, k, bw_all )

        if x == 5:
        	n = input("n: ")
        	k = input("k: ")
        	bw_all = input("bw_all: ")
        	self.Dcell( n, k, bw_all )

    def Tree( self, depth, fanout, tbw, switch=None ):
        if depth ==0 :
            for i in range(0,fanout):
                h_temp = self.addHost('h'+str(self.host_num))
                self.addLink(switch,h_temp, bw=tbw)
                self.host_num += 1
            #return
        else:
            if self.switch_num == 1:
                s_temp = self.addSwitch('s'+str(self.switch_num))
                self.switch_num += 1
                self.Tree(depth-1, fanout, tbw, s_temp)
            else:
                for i in range(0,fanout):
                    s_temp = self.addSwitch('s'+str(self.switch_num))
                    self.switch_num += 1
                    self.addLink(switch,s_temp,bw=tbw)
                    self.Tree(depth-1, fanout, tbw,s_temp)

    def FatTree( self, pod, bw_core, bw_agg, bw_edge ):
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
                    self.addLink('s'+str(i*P_num+j),'s'+str(C_num+k*(pod/2)+i+1), bw=bw_core )

        for i in range(0 ,pod):
            for j in range(0 ,P_num):
                for k in range(0 ,P_num):
                    self.addLink('s'+str(C_num+j+i*P_num+1),'s'+str(C_num+A_num+k+i*P_num+1), bw=bw_agg)

        for i in range(0 ,E_num ):
            for j in range(1 ,P_num+1):
                self.addLink('s'+str(C_num + A_num + i +1),'h'+str(P_num*i+j), bw=bw_edge)
        
        print 'Core switches: 1--',str(C_num),' ; Aggrevation switches: '+str(C_num+1)+'--'+str(C_num+A_num)+' ; Edge switches: '+str(C_num+A_num+1)+'--'+str(C_num+A_num+E_num)+''

    def VL2( self, DA, DI, density, bw_switch, bw_host):
    	I_num = DA/2
    	A_num = DI
    	T_num = DI*DA/4
    	H_num = T_num*density
    	Total_switch = I_num + A_num + T_num

        for i in range( 0 ,Total_switch ):
            self.addSwitch('s'+str(i+1))

    	for i in range( 0 ,H_num ):
    		self.addHost('h'+str(i+1))

    	for i in range( 0, I_num ):
    		for j in range( 0, A_num):
    			self.addLink( 's'+str(i+1), 's'+str(I_num+j+1), bw=bw_switch )

    	for i in range( 0, A_num/2 ):
    		for j in range( 0, DA/2 ):
    			self.addLink( 's'+str(I_num+2*i+1), 's'+str(I_num+A_num+i*DA/2+j+1), bw=bw_switch )
    			self.addLink( 's'+str(I_num+2*i+2), 's'+str(I_num+A_num+i*DA/2+j+1), bw=bw_switch )

    	for i in range( 0, T_num ):
    		for j in range( 0, density ):
    			self.addLink( 's'+str(I_num+A_num+i+1), 'h'+str(i*density+j+1), bw=bw_host )

    def Bcube( self, n, k, bw_all ):
        ls_num = n**k
    	s_num = (n**k)*(k+1)
        h_num = n**(k+1)

        for i in range( 0, s_num ):
            self.addSwitch('s'+str(i+1))

        for i in range( 0, h_num ):
            self.addSwitch('h'+str(i+1))

        for i in range( 0, h_num ):
            self.addHost('c'+str(i+1))

        for i in range( 0, n**k ):
            self.addLink( 'h'+str(i+1), 'c'+str(i+1), bw=bw_all )


        for i in range( 0, ls_num ):
            for j in range( 0, n ):
                self.addLink('s'+str(i+1),'h'+str(i*n+j+1), bw=bw_all )

        if k > 0:
            self.bcube_links(n, k, 1, bw_all)

    def bcube_links( self, n, k, level, bw_all):

        ls_num = n**k
        bp_num = n**(k-level)
        pod = n**level

        for i in range(0, bp_num):
            for j in range(0, pod):
                for k in range(0, n):
                    self.addLink('s'+str(level*ls_num+i*pod+j+1),'h'+str(i*pod*n+k*pod+j+1), bw=bw_all )

        if level<k:
            self.bcube_links(n, k, level+1, bw_all)



    def Dcell( self, n, k, bw_all):
        s_num = 1
        h_num = n
        for i in range( 0, k ):
            s_num = s_num*(h_num+1)
            h_num = h_num*(h_num+1)

        for i in range( 0, s_num ):
            self.addSwitch('s'+str(i+1))

        for i in range( 0, h_num ):
            self.addSwitch('h'+str(i+1))

        for i in range( 0, h_num ):
            self.addHost('c'+str(i+1))

        for i in range( 0, h_num ):
            self.addLink( 'h'+str(i+1), 'c'+str(i+1), bw=bw_all )


        for i in range( 0, s_num ):
            for j in range( 0, n ):
                self.addLink('s'+str(i+1),'h'+str(i*n+j+1), bw=bw_all )

        self.dcell_links( n, k, bw_all)

    def dcell_links( self, h_num, n, k, bw_all ):
        pod = n*(n+1)
        p_num = h_num/pod
        for i in range( 0, p_num ):
            for j in range( 0, n ):
                self.addLink('h'+str(i*pod+j+1),'h'+str(i*pod+j*n+1), bw=bw_all )

        if p_num > 1:
            dcell_links( h_num, pod, k-1, bw_all )






if __name__ == '__main__':
    setLogLevel( 'info' )
    network = TreeTopo(pod=4 ,bw_core=1 ,bw_agg=1 ,bw_edge=1 )

    net = Mininet(topo=network, link=TCLink, controller=None)
    net.addController('controller', controller=RemoteController, ip='0.0.0.0', port=6653)
    net.start()

    CLI(net)
    net.stop()
