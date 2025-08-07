Project Structure and Module Description
1. “ProjTopo_20250730_useful_with_ryu2.py”
Function: Builds and runs a virtual Mininet network topology.
Topology Structure is above:
2 core switches: s1, s2
4 hosts (h1–h4) connected to s1
3 servers (ser1–ser3) connected to s2
Features:
Uses TCLink to configure link parameters including bandwidth, delay, and packet loss rate.
Simulates realistic HTTP/HTTPS traffic (via ports 80 and 443) using iperf.
Traffic patterns involve multiple randomized access rounds, where a random set of hosts communicate with servers, with a randomized delay before each transmission.
Supports Mininet CLI for further manual testing and interaction after automated tests.

2. “simple_forwarding.py”
Function: A Ryu controller module that implements intelligent forwarding based on TCP port identification.
Behavior:
Default behavior is FLOOD forwarding with MAC learning.When TCP traffic is detected (e.g., on port 80 or 443), the controller installs high-priority flow entries matching:
ipv4_src, ipv4_dst, and tcp_dstEnables precise forwarding and improves data path efficiency.Unknown flows are initially sent to the controller for decision-making.


3. flow_stats.py (Flow Stats with Comments)
Function: A standalone traffic monitoring module used to collect real-time flow statistics from all switches.
Features:
Polls all connected switches every 10 seconds to retrieve FlowStats.
Automatically generates:
Real-time snapshot CSV files
Cumulative traffic statistics CSV
Pie chart images (PNG format) illustrating current and total traffic proportions
Output Directories:
Real-time snapshots: ~/flow_stats_output/externalFlow/
Total statistics summary: ~/flow_stats_output/summary/
