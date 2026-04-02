"use client";

import { DashboardSidebar } from "@/components/dashboard-sidebar";
import { BarChart3 } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-[#0a0f1c]">
      {/* Dashboard Sidebar */}
      <DashboardSidebar />

      {/* Main Content */}
      <main className="ml-80 min-h-screen">
        {/* Top Bar */}
        <div className="sticky top-0 bg-[#0a0f1c]/80 backdrop-blur-lg border-b border-blue-900/30 z-10">
          <div className="flex items-center justify-between px-8 py-4">
            <div>
              <h1 className="text-xl font-bold text-white">Dashboard</h1>
              <p className="text-sm text-blue-400 mt-0.5">
                Real-time support analytics
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/">
                <button className="px-4 py-2 rounded-lg bg-blue-900/30 hover:bg-blue-900/50 transition-colors border border-blue-800/30 text-sm text-blue-400 hover:text-blue-200">
                  ← Back to Form
                </button>
              </Link>
            </div>
          </div>
        </div>

        {/* Dashboard Content Placeholder */}
        <div className="p-8">
          <div className="max-w-4xl mx-auto">
            <div className="bg-blue-900/20 border border-blue-800/30 rounded-xl p-8 text-center">
              <BarChart3 className="w-16 h-16 text-blue-400 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-white mb-2">
                Full Dashboard View
              </h2>
              <p className="text-blue-400">
                The sidebar contains all essential real-time metrics.
                <br />
                This area can be used for detailed analytics, charts, or reports.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
