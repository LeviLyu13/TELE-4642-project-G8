#!/usr/bin/python
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import irange, dumpNodeConnections
from mininet.log import setLogLevel
from mininet.cli import CLI
import time
import random

class CustomTopo(Topo):
    "Simple Data Center Topology"

    "linkopts - (1:core, 2:aggregation, 3: edge) parameters"
    "fanout - number of child switch per parent switch"

    def __init__(self, linkopts1, linkopts2, linkopts3, fanout=2, **opts):
        
        Topo.__init__(self, **opts)
        k = fanout
        Switch1 = self.addSwitch('s1')
        Switch2 = self.addSwitch('s2')
        self.addLink(Switch1, Switch2, **linkopts1)

        Host1 = self.addHost('h1', cpu=.5 / k)
        self.addLink(Switch1, Host1, **linkopts3)

        Host2 = self.addHost('h2', cpu=.5 / k)
        self.addLink(Switch1, Host2, **linkopts3)
        Host3 = self.addHost('h3', cpu=.5 / k)
        self.addLink(Switch1, Host3, **linkopts3)
        Host4 = self.addHost('h4', cpu=.5 / k)
        self.addLink(Switch1, Host4, **linkopts3)

        Server1 = self.addHost('ser1', cpu=.5 / k)
        self.addLink(Switch2, Server1, **linkopts3)
        Server2 = self.addHost('ser2', cpu=.5 / k)
        self.addLink(Switch2, Server2, **linkopts3)
        Server3 = self.addHost('ser3', cpu=.5 / k)
        self.addLink(Switch2, Server3, **linkopts3)


def perfTest():
    "Create network and run simple performance test"
    linkCore = dict(bw=1000, delay='1ms', loss=1, max_queue_size=4000, use_htb=True)
    linkAgg = dict(bw=100, delay='2ms', loss=1, max_queue_size=2000, use_htb=True)
    linkEdge = dict(bw=10, delay='4ms', loss=1, max_queue_size=1000, use_htb=True)

    topo = CustomTopo(linkCore, linkAgg, linkEdge, fanout=2)
    net = Mininet(topo=topo, build=False, host=CPULimitedHost, link=TCLink, autoSetMacs=True)
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    net.build()
    net.start()
    
    ser1 = net.get('ser1')
    ser1.setIP('10.46.42.1')
    ser2 = net.get('ser2')
    ser2.setIP('10.123.123.123')
    ser3 = net.get('ser3')
    ser3.setIP('10.46.42.3')

    h1 = net.get('h1')
    h2 = net.get('h2')
    h3 = net.get('h3')
    h4 = net.get('h4')

    print("Dumping host connections")
    dumpNodeConnections(net.hosts)

    print("Testing network connectivity")

    seconds = 5       
    rounds = 3       
    Minimum_number_of_tasks_perround = 4

    base_patterns = [
        (h1, ser1, 80), (h1, ser2, 443), (h1, ser3, 443),
        (h2, ser1, 80), (h2, ser2, 80), (h2, ser3, 443),
        (h3, ser1, 443), (h3, ser2, 80), (h3, ser3, 80),
        (h4, ser1, 443), (h4, ser2, 80), (h4, ser3, 80)
    ]
    
    for r in range(rounds):
        print(f"\n=== Round {r + 1} ===")

        access_patterns = base_patterns.copy()
        random.shuffle(access_patterns)

        num_to_run = random.randint(Minimum_number_of_tasks_perround, len(access_patterns))
        access_patterns = access_patterns[:num_to_run]

        for src, dst, port in access_patterns:
            delay = random.uniform(0, 2) 
            print(f"Waiting {delay:.2f}s before {src} -> {dst} (port {port})")
            time.sleep(delay)
            net.iperf([src, dst], port=port, seconds=seconds)

    CLI(net)
    # net.interact()
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    perfTest()

