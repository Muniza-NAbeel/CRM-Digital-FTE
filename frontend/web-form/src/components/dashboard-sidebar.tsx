"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Headphones,
  RefreshCw,
  CheckCircle2,
  Clock,
  Zap,
  Activity,
  FileText,
  MessageSquare,
  Mail,
  TrendingUp,
  MessageCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface DashboardData {
  overview: {
    total_requests_today: number;
    success_rate_today: number;
    avg_processing_time_session_ms: number;
    escalation_rate_today: number;
  };
  queue_status: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
  };
  worker: {
    running: boolean;
    processed_count: number;
    error_count: number;
  };
  kafka: {
    kafka_connected: boolean;
    fallback_active: boolean;
    fallback_queue_size: number;
    consumer_running: boolean;
  };
  channels: {
    breakdown: Array<{
      channel: string;
      name: string;
      count: number;
      percentage: number;
      completed: number;
      failed: number;
    }>;
  };
}

interface Activity {
  id: string;
  type: "email" | "whatsapp" | "webform";
  message: string;
  time: string;
}

export function DashboardSidebar() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [activities] = useState<Activity[]>([
    { id: "1", type: "webform", message: "Web Form submitted", time: "2 min ago" },
    { id: "2", type: "email", message: "Email received", time: "12 min ago" },
    { id: "3", type: "whatsapp", message: "WhatsApp message", time: "25 min ago" },
    { id: "4", type: "webform", message: "Ticket resolved", time: "1 hour ago" },
    { id: "5", type: "email", message: "New inquiry", time: "2 hours ago" },
  ]);

  const fetchDashboard = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/v1/dashboard");
      if (!response.ok) throw new Error("Failed to fetch");
      const dashboardData = await response.json();
      setData(dashboardData);
      setLastUpdated(new Date());
    } catch (error) {
      console.error("Dashboard fetch error:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 10000);
    return () => clearInterval(interval);
  }, []);

  const channelColors: any = {
    web_form: { bg: "bg-purple-500", from: "from-purple-500", to: "to-purple-600" },
    whatsapp: { bg: "bg-green-500", from: "from-green-500", to: "to-emerald-600" },
    gmail: { bg: "bg-blue-500", from: "from-blue-500", to: "to-cyan-600" },
  };

  const channelIcons: any = {
    web_form: FileText,
    whatsapp: MessageSquare,
    gmail: Mail,
  };

  return (
    <aside className="fixed left-0 top-0 h-full w-80 bg-[#0a0f1c] border-r border-blue-900/30 overflow-y-auto">
      {/* Logo Section */}
      <div className="sticky top-0 bg-[#0a0f1c] border-b border-blue-900/30 p-6 z-10">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Headphones className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">TechCorp</h1>
            <p className="text-xs text-blue-400">AI Customer Success</p>
          </div>
        </div>
        <div className="flex items-center justify-between mt-4">
          <div className="text-xs text-blue-400">
            {lastUpdated ? `Updated: ${lastUpdated.toLocaleTimeString()}` : 'Loading...'}
          </div>
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={fetchDashboard}
            className="p-1.5 rounded-lg hover:bg-blue-900/30 transition-colors"
          >
            <RefreshCw className={cn("w-4 h-4 text-blue-400", loading && "animate-spin")} />
          </motion.button>
        </div>
      </div>

      <div className="p-4 space-y-6">
        {/* Total Submissions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-800/50 rounded-xl p-5"
        >
          <p className="text-xs text-blue-400 mb-2">Total Submissions Today</p>
          <motion.p
            key={data?.overview.total_requests_today || 0}
            initial={{ scale: 1.2 }}
            animate={{ scale: 1 }}
            className="text-5xl font-bold text-white"
          >
            {data?.overview.total_requests_today || 0}
          </motion.p>
        </motion.div>

        {/* Quick Stats Row */}
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            label="Success Rate"
            value={`${data?.overview.success_rate_today.toFixed(1) || 0}%`}
            icon={CheckCircle2}
            color="text-green-500"
          />
          <StatCard
            label="Avg Time"
            value={`${((data?.overview.avg_processing_time_session_ms || 0) / 1000).toFixed(2)}s`}
            icon={Clock}
            color="text-blue-400"
          />
          <StatCard
            label="Escalations"
            value={`${data?.overview.escalation_rate_today.toFixed(1) || 0}%`}
            icon={TrendingUp}
            color="text-purple-400"
          />
          <StatCard
            label="Processed"
            value={data?.worker.processed_count || 0}
            icon={Zap}
            color="text-yellow-400"
          />
        </div>

        {/* Channel Breakdown */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-white">Channel Breakdown</h3>
          </div>
          {data?.channels.breakdown.map((channel) => {
            const colors = channelColors[channel.channel] || channelColors.web_form;
            const Icon = channelIcons[channel.channel] || FileText;

            return (
              <motion.div
                key={channel.channel}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={cn("w-6 h-6 rounded-md bg-gradient-to-br flex items-center justify-center", colors.from, colors.to)}>
                      <Icon className="w-3 h-3 text-white" />
                    </div>
                    <span className="text-sm text-blue-100">{channel.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-blue-400">{channel.count}</span>
                    <span className="text-xs font-medium text-blue-200">{channel.percentage.toFixed(1)}%</span>
                  </div>
                </div>
                <div className="h-1.5 bg-blue-900/30 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${channel.percentage}%` }}
                    transition={{ duration: 0.8 }}
                    className={cn("h-full rounded-full bg-gradient-to-r", colors.from, colors.to)}
                  />
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Queue Status */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-white">Queue Status</h3>
          </div>
          <div className="grid grid-cols-4 gap-2">
            <QueueStat label="Pending" value={data?.queue_status.pending || 0} color="text-yellow-500" />
            <QueueStat label="Processing" value={data?.queue_status.processing || 0} color="text-blue-400" />
            <QueueStat label="Done" value={data?.queue_status.completed || 0} color="text-green-500" />
            <QueueStat label="Failed" value={data?.queue_status.failed || 0} color="text-red-500" />
          </div>
        </div>

        {/* System Status */}
        <div className="bg-blue-900/20 border border-blue-800/30 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-white">System Status</h3>
          </div>
          <StatusRow label="Worker" active={data?.worker.running || false} />
          <StatusRow label="Kafka" active={data?.kafka.kafka_connected || false} />
          <StatusRow label="Consumer" active={data?.kafka.consumer_running || false} />
          {data?.kafka.fallback_active && (
            <div className="pt-2 border-t border-blue-800/30">
              <div className="flex justify-between items-center">
                <span className="text-xs text-blue-400">Fallback Queue</span>
                <span className="text-xs font-medium text-blue-200">{data.kafka.fallback_queue_size}</span>
              </div>
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <MessageCircle className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-white">Recent Activity</h3>
          </div>
          <div className="space-y-3">
            {activities.map((activity, idx) => {
              const icons = {
                email: Mail,
                whatsapp: MessageSquare,
                webform: FileText,
              };
              const colors = {
                email: "text-blue-400",
                whatsapp: "text-green-400",
                webform: "text-purple-400",
              };
              const Icon = icons[activity.type];

              return (
                <motion.div
                  key={activity.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="flex items-start gap-3"
                >
                  <div className={cn("w-7 h-7 rounded-lg bg-blue-900/30 flex items-center justify-center flex-shrink-0", colors[activity.type])}>
                    <Icon className="w-3.5 h-3.5 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-blue-100 truncate">{activity.message}</p>
                    <p className="text-xs text-blue-500 mt-0.5">{activity.time}</p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="sticky bottom-0 bg-[#0a0f1c] border-t border-blue-900/30 p-4">
        <motion.div
          className="inline-flex items-center justify-center w-full px-3 py-2 rounded-full bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 shadow-lg"
        >
          <span className="text-[10px] text-blue-400">v1.0.0</span>
          <motion.span
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            className="mx-2 text-green-500"
          >
            •
          </motion.span>
          <span className="text-[10px] text-blue-400">TechCorp</span>
          <span className="mx-2 text-blue-600">|</span>
          <span className="text-[10px] text-blue-500">Auto-refreshes every 10s</span>
        </motion.div>
      </div>
    </aside>
  );
}

function StatCard({ label, value, icon: Icon, color }: any) {
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="bg-blue-900/20 border border-blue-800/30 rounded-lg p-3 text-center"
    >
      <Icon className={cn("w-4 h-4 mx-auto mb-1.5", color)} />
      <p className={cn("text-lg font-bold", color)}>{value}</p>
      <p className="text-xs text-blue-400">{label}</p>
    </motion.div>
  );
}

function QueueStat({ label, value, color }: any) {
  return (
    <div className="bg-blue-900/20 border border-blue-800/30 rounded-lg p-2 text-center">
      <p className={cn("text-lg font-bold", color)}>{value}</p>
      <p className="text-xs text-blue-400">{label}</p>
    </div>
  );
}

function StatusRow({ label, active }: any) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-xs text-blue-400">{label}</span>
      <span
        className={cn(
          "px-2 py-0.5 rounded-full text-xs font-medium",
          active
            ? "bg-green-500/20 text-green-500"
            : "bg-red-500/20 text-red-500"
        )}
      >
        {active ? "Running" : "Stopped"}
      </span>
    </div>
  );
}
