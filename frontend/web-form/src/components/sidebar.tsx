"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  BarChart3,
  FileText,
  MessageSquare,
  Mail,
  Ticket,
  BookOpen,
  Settings,
  Headphones,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: BarChart3 },
  { name: "Web Form", href: "/", icon: FileText },
  { name: "WhatsApp", href: "#", icon: MessageSquare },
  { name: "Gmail", href: "#", icon: Mail },
  { name: "Tickets", href: "#", icon: Ticket },
  { name: "Knowledge Base", href: "#", icon: BookOpen },
  { name: "Analytics", href: "#", icon: BarChart3 },
  { name: "Settings", href: "#", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="fixed left-0 top-0 h-full w-64 bg-[#0f0f0f] border-r border-zinc-800/50">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-6 border-b border-zinc-800/50">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
          <Headphones className="w-4 h-4 text-white" />
        </div>
        <div>
          <h1 className="text-sm font-semibold text-white">TechCorp</h1>
          <p className="text-xs text-zinc-500">Support</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-3 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link key={item.name} href={item.href}>
              <motion.div
                whileHover={{ x: 4 }}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all",
                  isActive
                    ? "bg-zinc-800/50 text-white font-medium border border-zinc-700/50"
                    : "text-zinc-400 hover:text-white hover:bg-zinc-800/30"
                )}
              >
                <Icon className="w-4 h-4" />
                {item.name}
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-zinc-800/50">
        <div className="text-xs text-zinc-600 text-center">
          <p>v1.0.0</p>
          <p className="mt-1">Hackathon Five</p>
        </div>
      </div>
    </div>
  );
}
