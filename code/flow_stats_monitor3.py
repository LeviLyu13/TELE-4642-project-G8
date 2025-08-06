#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Ryu Flow Statistics Monitor - Enhanced Analysis Version with Smoothed Multi-User Trend

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub

import os
import csv
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

# ======== Output Directories ========
OUTPUT_DIR = os.path.expanduser("~/flow_stats_output")
EXTERNAL_DIR = os.path.join(OUTPUT_DIR, "externalFlow")
SUMMARY_DIR = os.path.join(OUTPUT_DIR, "summary")

# Create directories
os.makedirs(EXTERNAL_DIR, exist_ok=True)
os.makedirs(SUMMARY_DIR, exist_ok=True)


class FlowStatsMonitor(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]  # Must match your forwarding app

    def __init__(self, *args, **kwargs):
        super(FlowStatsMonitor, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.total_usage = {}  # Cumulative total usage
        self.monitor_thread = hub.spawn(self._monitor)

    # ======== Switch State Change ========
    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info(f"Switch {datapath.id} connected")
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.info(f"Switch {datapath.id} disconnected")
                del self.datapaths[datapath.id]

    # ======== Monitoring Thread ========
    def _monitor(self):
        while True:
            for dp in list(self.datapaths.values()):
                self._request_stats(dp)
            hub.sleep(10)  # Every 10 seconds

    def _request_stats(self, datapath):
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    # ======== Handle FlowStats Reply ========
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        # Save current snapshot
        csv_path = os.path.join(EXTERNAL_DIR, f"flowstats_{timestamp}.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Src", "Dst", "Packets", "Bytes", "Duration_sec"])
            for stat in body:
                match = stat.match
                ipv4_src = match.get('ipv4_src', 'N/A')
                ipv4_dst = match.get('ipv4_dst', 'N/A')
                bytes_count = stat.byte_count

                # Update cumulative usage
                key = (ipv4_src, ipv4_dst)
                self.total_usage[key] = self.total_usage.get(key, 0) + bytes_count

                writer.writerow([ipv4_src, ipv4_dst,
                                 stat.packet_count, bytes_count,
                                 stat.duration_sec])

        # Save and analyze total usage
        self._save_total_usage()

    # ======== Save and Plot All Analysis ========
    def _save_total_usage(self):
        csv_path = os.path.join(SUMMARY_DIR, "total_usage.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Src", "Dst", "Total_Bytes"])
            for (src, dst), total_bytes in self.total_usage.items():
                writer.writerow([src, dst, total_bytes])
        self.logger.info(f"Total usage updated: {csv_path}")

        try:
            df = pd.read_csv(csv_path)
            if df.empty:
                return

            # ===== 1. 总量饼图 =====
            total_dir = os.path.join(SUMMARY_DIR, "total_usage")
            os.makedirs(total_dir, exist_ok=True)
            usage_by_pair = df.groupby(['Src', 'Dst'])['Total_Bytes'].sum().reset_index()
            labels = [f"{row['Src']}->{row['Dst']}" for _, row in usage_by_pair.iterrows()]
            sizes = usage_by_pair['Total_Bytes']
            plt.figure(figsize=(6, 6))
            plt.pie(sizes, labels=labels, autopct='%.2f%%')
            plt.axis('equal')
            plt.title("Total Flow Usage (From Start to Now)")
            plt.savefig(os.path.join(total_dir, "total_usage_chart.png"), bbox_inches='tight')
            plt.close()

            # ===== 2. 用户聚合 =====
            user_dir = os.path.join(SUMMARY_DIR, "user_aggregation")
            os.makedirs(user_dir, exist_ok=True)
            usage_by_user = df.groupby('Src')['Total_Bytes'].sum().sort_values(ascending=False)
            usage_by_user.to_csv(os.path.join(user_dir, "usage_by_user.csv"))
            usage_by_user.plot(kind='bar')
            plt.title("Total Usage by User")
            plt.ylabel("Bytes")
            plt.tight_layout()
            plt.savefig(os.path.join(user_dir, "usage_by_user_chart.png"))
            plt.close()

            # ===== 3. 服务聚合 =====
            service_dir = os.path.join(SUMMARY_DIR, "service_aggregation")
            os.makedirs(service_dir, exist_ok=True)
            usage_by_service = df.groupby('Dst')['Total_Bytes'].sum().sort_values(ascending=False)
            usage_by_service.to_csv(os.path.join(service_dir, "usage_by_service.csv"))
            usage_by_service.plot(kind='bar')
            plt.title("Total Usage by Service")
            plt.ylabel("Bytes")
            plt.tight_layout()
            plt.savefig(os.path.join(service_dir, "usage_by_service_chart.png"))
            plt.close()

            # ===== 4. 堆叠柱状图 =====
            stacked_dir = os.path.join(SUMMARY_DIR, "stacked_bar")
            os.makedirs(stacked_dir, exist_ok=True)
            pivot_df = df.pivot_table(index='Src', columns='Dst', values='Total_Bytes', aggfunc='sum').fillna(0)
            pivot_df.to_csv(os.path.join(stacked_dir, "user_service_matrix.csv"))
            pivot_df.plot(kind='bar', stacked=True, figsize=(10, 6))
            plt.title("User-Service Traffic (Stacked Bar)")
            plt.ylabel("Bytes")
            plt.tight_layout()
            plt.savefig(os.path.join(stacked_dir, "stacked_bar_chart.png"))
            plt.close()

            # ===== 5. 时间序列折线图（总量 + 多用户，颜色固定，曲线平滑） =====
            ts_dir = os.path.join(SUMMARY_DIR, "time_series")
            os.makedirs(ts_dir, exist_ok=True)

            # (a) 多用户时间序列
            usage_by_user_now = df.groupby('Src')['Total_Bytes'].sum()
            ts_csv_users = os.path.join(ts_dir, "time_series_users.csv")
            if os.path.exists(ts_csv_users):
                ts_df = pd.read_csv(ts_csv_users)
            else:
                ts_df = pd.DataFrame(columns=["Time"] + list(usage_by_user_now.index))

            new_row = {"Time": datetime.now().strftime("%H:%M:%S")}
            for user in usage_by_user_now.index:
                new_row[user] = usage_by_user_now[user]
            ts_df = pd.concat([ts_df, pd.DataFrame([new_row])], ignore_index=True)
            ts_df.to_csv(ts_csv_users, index=False)

            # 绘制平滑多用户曲线
            plt.figure(figsize=(10, 6))
            colors = plt.cm.tab10.colors
            for idx, user in enumerate(usage_by_user_now.index):
                if user in ts_df.columns:
                    y_values = ts_df[user].astype(float)
                    y_smooth = y_values.rolling(window=3, center=True, min_periods=1).mean()
                    plt.plot(ts_df["Time"], y_smooth,
                             marker='o',
                             label=str(user),
                             color=colors[idx % len(colors)])
            plt.title("Traffic Over Time by User (Smoothed)")
            plt.xlabel("Time")
            plt.ylabel("Bytes")
            plt.xticks(rotation=45)
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(ts_dir, "traffic_over_time_by_user.png"))
            plt.close()

            # (b) 总流量时间序列（平滑）
            ts_csv_total = os.path.join(ts_dir, "time_series_total.csv")
            total_sum = df['Total_Bytes'].sum()
            with open(ts_csv_total, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now().strftime("%H:%M:%S"), total_sum])

            total_df = pd.read_csv(ts_csv_total, names=['Time', 'Bytes'])
            total_df['Bytes_smooth'] = total_df['Bytes'].rolling(window=3, center=True, min_periods=1).mean()
            plt.plot(total_df['Time'], total_df['Bytes_smooth'], marker='o', color='red')
            plt.title("Total Traffic Over Time (Smoothed)")
            plt.xlabel("Time")
            plt.ylabel("Bytes")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(ts_dir, "traffic_over_time_total.png"))
            plt.close()

            self.logger.info("All analysis charts updated successfully.")

        except Exception as e:
            self.logger.error(f"Failed to plot analysis charts: {e}")
