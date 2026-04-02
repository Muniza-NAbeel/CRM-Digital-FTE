"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mail,
  MessageSquare,
  Globe,
  Send,
  Clock,
  Sparkles,
  Shield,
  Zap,
  Ticket,
  Menu,
  X,
} from "lucide-react";
import { DashboardSidebar } from "@/components/dashboard-sidebar";
import { SupportForm } from "@/components/support-form";
import { TicketStatusChecker } from "@/components/ticket-status";
import { ThemeToggle } from "@/components/theme-toggle";
import { WhatsAppIntegration } from "@/components/whatsapp-integration";
import { EmailIntegration } from "@/components/email-integration";
import { cn } from "@/lib/utils";

type ChannelType = "email" | "whatsapp" | "web";
type ViewType = "form" | "status";

export default function Home() {
  const [activeChannel, setActiveChannel] = useState<ChannelType | null>(null);
  const [view, setView] = useState<ViewType>("form");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [requestIdToTrack, setRequestIdToTrack] = useState<string>("");

  const handleChannelClick = (channelId: ChannelType) => {
    setActiveChannel(channelId);
  };

  // Function to switch to status view with request ID
  const goToStatusCheck = (requestId: string) => {
    setRequestIdToTrack(requestId);
    setView("status");
  };

  // Close sidebar on route change (mobile)
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setSidebarOpen(false);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const channels = [
    {
      id: "email" as ChannelType,
      icon: Mail,
      title: "Email",
      description: "Send us an email",
      gradient: "from-blue-500 to-cyan-500",
      color: "text-blue-400",
      bgColor: "bg-blue-500/10",
      borderColor: "border-blue-500/20",
    },
    {
      id: "whatsapp" as ChannelType,
      icon: MessageSquare,
      title: "WhatsApp",
      description: "Chat instantly",
      gradient: "from-green-500 to-emerald-500",
      color: "text-green-400",
      bgColor: "bg-green-500/10",
      borderColor: "border-green-500/20",
    },
    {
      id: "web" as ChannelType,
      icon: Globe,
      title: "Web Form",
      description: "Fill our form",
      gradient: "from-purple-500 to-pink-500",
      color: "text-purple-400",
      bgColor: "bg-purple-500/10",
      borderColor: "border-purple-500/20",
      active: true,
    },
  ];

  const features = [
    {
      icon: Sparkles,
      title: "AI-Powered",
      description: "Instant responses powered by advanced AI",
    },
    {
      icon: Shield,
      title: "Secure & Private",
      description: "Your data is encrypted and protected",
    },
    {
      icon: Zap,
      title: "Fast Response",
      description: "Get answers within minutes, not days",
    },
    {
      icon: Clock,
      title: "24/7 Support",
      description: "Always available, any time of day",
    },
  ];

  return (
    <div className="min-h-screen bg-[#0a0f1c]">
      {/* Dashboard Sidebar - Desktop */}
      <div className="hidden lg:block">
        <DashboardSidebar />
      </div>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25 }}
              className="fixed left-0 top-0 h-full z-50 lg:hidden"
            >
              <DashboardSidebar />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main className={cn(
        "min-h-screen transition-all duration-300",
        "lg:ml-80"
      )}>
        {/* Top Bar */}
        <div className="sticky top-0 bg-background/80 dark:bg-[#0a0f1c]/80 backdrop-blur-lg border-b border-border dark:border-blue-900/30 z-30">
          <div className="flex items-center justify-between px-4 sm:px-6 lg:px-8 py-4">
            {/* Mobile Menu Button */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 rounded-lg bg-secondary hover:bg-muted dark:bg-blue-900/30 dark:hover:bg-blue-900/50 transition-colors border border-border dark:border-blue-800/30"
            >
              {sidebarOpen ? (
                <X className="w-5 h-5 text-foreground dark:text-blue-400" />
              ) : (
                <Menu className="w-5 h-5 text-foreground dark:text-blue-400" />
              )}
            </button>

            {/* Right Side Actions */}
            <div className="flex items-center gap-3 ml-auto">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setView(view === "form" ? "status" : "form")}
                className="flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg bg-secondary hover:bg-muted dark:bg-blue-900/30 dark:hover:bg-blue-900/50 transition-colors border border-border dark:border-blue-800/30 text-sm text-foreground dark:text-blue-400 dark:hover:text-blue-200"
              >
                {view === "form" ? (
                  <>
                    <Ticket className="w-4 h-4" />
                    <span className="hidden sm:inline">Check Status</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span className="hidden sm:inline">New Ticket</span>
                  </>
                )}
              </motion.button>
              <ThemeToggle />
            </div>
          </div>
        </div>

        {/* Content Area */}
        <div className="p-4 sm:p-6 lg:p-8">
          <div className="max-w-5xl mx-auto space-y-8 lg:space-y-12">
            <AnimatePresence mode="wait">
              {view === "form" ? (
                <motion.div
                  key="form"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="space-y-8 lg:space-y-12"
                >
                  {/* Hero Section */}
                  <div className="text-center space-y-4 sm:space-y-6">
                    {/* Name & Tag - Single Line */}
                    <motion.div
                      initial={{ opacity: 0, y: -20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="inline-block px-4 sm:px-5 py-2 sm:py-2.5 rounded-full bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 shadow-lg shadow-blue-500/10"
                    >
                      <span className="text-xs sm:text-sm font-semibold text-foreground dark:text-white">Muniza Nabeel</span>
                      <motion.span
                        animate={{ opacity: [0.4, 1, 0.4] }}
                        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                        className="mx-2 text-green-500"
                      >
                        •
                      </motion.span>
                      <span className="text-xs sm:text-sm text-muted-foreground dark:text-blue-300 whitespace-nowrap">AI-Powered Customer Success Support</span>
                    </motion.div>

                    {/* Main Heading */}
                    <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground leading-tight">
                      Customer Success{" "}
                      <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                        FTE
                      </span>
                    </h1>

                    {/* Sub Heading */}
                    <p className="text-sm sm:text-base text-muted-foreground max-w-2xl mx-auto px-4">
                      24/7 AI-powered support across email, WhatsApp, and web.
                      Get instant help with your questions.
                    </p>
                  </div>

                  {/* Features - Compact Pill Style */}
                  <div className="flex flex-wrap justify-center gap-2 sm:gap-3 lg:gap-4">
                    {features.map((feature, idx) => {
                      const Icon = feature.icon;
                      const colors = [
                        { bg: "from-yellow-500/10 to-orange-500/10", border: "border-yellow-500/30", text: "text-yellow-400", icon: "text-yellow-500" },
                        { bg: "from-purple-500/10 to-pink-500/10", border: "border-purple-500/30", text: "text-purple-400", icon: "text-purple-500" },
                        { bg: "from-green-500/10 to-emerald-500/10", border: "border-green-500/30", text: "text-green-400", icon: "text-green-500" },
                        { bg: "from-red-500/10 to-rose-500/10", border: "border-red-500/30", text: "text-red-400", icon: "text-red-500" },
                      ];
                      const color = colors[idx % colors.length];

                      return (
                        <motion.div
                          key={feature.title}
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: idx * 0.1 }}
                          className={cn(
                            "inline-flex items-center gap-2 px-3 sm:px-4 py-2 sm:py-2.5 rounded-full border shadow-lg",
                            color.bg,
                            color.border
                          )}
                        >
                          <Icon className={cn("w-3.5 h-3.5 sm:w-4 sm:h-4", color.icon)} />
                          <div className="flex flex-col">
                            <span className="text-[10px] sm:text-xs font-semibold text-foreground dark:text-white leading-tight">
                              {feature.title}
                            </span>
                            <span className={cn("text-[10px] sm:text-xs", color.text)}>
                              {feature.description}
                            </span>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>

                  {/* Channel Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 lg:gap-8">
                    {channels.map((channel) => {
                      const Icon = channel.icon;

                      return (
                        <motion.button
                          key={channel.id}
                          whileHover={{ scale: 1.03, y: -6 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => handleChannelClick(channel.id)}
                          className={cn(
                            "relative p-6 sm:p-8 rounded-3xl border transition-all duration-300 group cursor-pointer",
                            activeChannel === channel.id
                              ? `${channel.bgColor} ${channel.borderColor} shadow-2xl shadow-${channel.color}/20`
                              : "bg-secondary/50 border-border hover:bg-secondary hover:border-primary/30 hover:shadow-xl hover:shadow-primary/10 dark:bg-blue-900/10 dark:border-blue-800/30 dark:hover:bg-blue-900/20 dark:hover:border-blue-700/50 dark:hover:shadow-xl dark:hover:shadow-blue-500/10"
                          )}
                        >
                          {/* Gradient Background on Active */}
                          {activeChannel === channel.id && (
                            <div
                              className={cn(
                                "absolute inset-0 rounded-3xl bg-gradient-to-br opacity-10",
                                channel.gradient
                              )}
                            />
                          )}

                          <div className="relative z-10 flex flex-col items-center text-center">
                            <div
                              className={cn(
                                "w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br flex items-center justify-center mb-4 sm:mb-5 shadow-lg",
                                channel.gradient
                              )}
                            >
                              <Icon className="w-7 h-7 sm:w-8 sm:h-8 text-white" />
                            </div>

                            <h3 className="text-lg sm:text-xl font-semibold text-foreground dark:text-white mb-2">
                              {channel.title}
                            </h3>
                            <p className="text-xs sm:text-sm text-muted-foreground dark:text-blue-300 mb-3">
                              {channel.description}
                            </p>
                          </div>
                        </motion.button>
                      );
                    })}
                  </div>

                  {/* Form Section - Show based on selected channel */}
                  <AnimatePresence>
                    {activeChannel && (
                      <motion.div
                        initial={{ opacity: 0, y: 40 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ delay: 0.2 }}
                        className="bg-gradient-to-br from-blue-900/20 to-purple-900/10 border border-blue-800/30 rounded-2xl sm:rounded-3xl p-4 sm:p-6 lg:p-8"
                      >
                        {activeChannel === "web" && (
                          <>
                            <div className="text-center mb-6 sm:mb-8">
                              <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">
                                Submit Your Question
                              </h2>
                              <p className="text-xs sm:text-sm text-blue-400">
                                Fill out the form below and we'll get back to you shortly
                              </p>
                            </div>
                            <SupportForm />
                          </>
                        )}
                        {activeChannel === "whatsapp" && (
                          <>
                            <div className="text-center mb-6 sm:mb-8">
                              <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">
                                WhatsApp Support
                              </h2>
                              <p className="text-xs sm:text-sm text-green-400">
                                Chat with us instantly on WhatsApp
                              </p>
                            </div>
                            <WhatsAppIntegration onGoToStatus={goToStatusCheck} />
                          </>
                        )}
                        {activeChannel === "email" && (
                          <>
                            <div className="text-center mb-6 sm:mb-8">
                              <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">
                                Email Support
                              </h2>
                              <p className="text-xs sm:text-sm text-blue-400">
                                Send us an email for detailed assistance
                              </p>
                            </div>
                            <EmailIntegration onGoToStatus={goToStatusCheck} />
                          </>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              ) : (
                <motion.div
                  key="status"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="max-w-2xl mx-auto"
                >
                  <div className="text-center mb-6 sm:mb-8">
                    <h2 className="text-2xl sm:text-3xl font-bold text-white mb-2">
                      Check Ticket Status
                    </h2>
                    <p className="text-sm sm:text-base text-blue-400">
                      Track your support ticket in real-time
                    </p>
                  </div>
                  <TicketStatusChecker initialRequestId={requestIdToTrack} />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Footer */}
            <footer className="mt-16 pt-8 border-t border-blue-900/30">
              <div className="text-center">
                <p className="text-xs text-blue-500">
                  Made with <motion.span animate={{ scale: [1, 1.2, 1] }} transition={{ duration: 1, repeat: Infinity }}>❤️</motion.span> by <span className="text-white font-semibold">Muniza Nabeel</span> • Customer Success FTE • Hackathon Five • 2026
                </p>
              </div>
            </footer>
          </div>
        </div>
      </main>
    </div>
  );
}
