"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  Search,
  Ticket,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
  Mail,
  FileText,
  Tag,
  TrendingUp,
  MessageCircle,
  ChevronDown,
  ChevronUp,
  Clipboard,
  User,
  Calendar,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";

import { checkTicketStatus } from "@/lib/api";
import { TicketStatusResponse } from "@/types";

const statusColors: Record<string, string> = {
  completed: "from-green-400 to-emerald-500",
  processing: "from-blue-400 to-indigo-500",
  pending: "from-yellow-400 to-orange-500",
  received: "from-purple-400 to-pink-500",
};

const statusIcons: Record<string, React.ReactNode> = {
  completed: <CheckCircle2 className="w-5 h-5" />,
  processing: <RefreshCw className="w-5 h-5 animate-spin" />,
  pending: <Clock className="w-5 h-5" />,
  received: <Ticket className="w-5 h-5" />,
};

const statusLabels: Record<string, string> = {
  completed: "Completed",
  processing: "Processing",
  pending: "Pending",
  received: "Received",
};

export function TicketStatusChecker({ initialRequestId }: { initialRequestId?: string }) {
  const [requestId, setRequestId] = useState(initialRequestId || "");
  const [loading, setLoading] = useState(false);
  const [ticket, setTicket] = useState<TicketStatusResponse | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  // Update requestId when initialRequestId changes
  useEffect(() => {
    if (initialRequestId) {
      setRequestId(initialRequestId);
    }
  }, [initialRequestId]);

  // Auto-polling: Refresh status every 3 seconds if not completed
  useEffect(() => {
    // Clear any existing interval
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }

    // Only poll if we have a ticket and it's not completed
    if (ticket && ticket.status?.toLowerCase() !== 'completed' && requestId) {
      const interval = setInterval(async () => {
        try {
          const data = await checkTicketStatus(requestId.trim());
          setTicket(data);
          
          // Stop polling if status is completed
          if (data.status?.toLowerCase() === 'completed') {
            clearInterval(interval);
            setPollingInterval(null);
            toast.success("Ticket completed! Check your email/WhatsApp for response.");
          }
        } catch (error) {
          console.error("Polling error:", error);
        }
      }, 3000); // Check every 3 seconds

      setPollingInterval(interval);
    }

    // Cleanup on unmount
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [ticket?.status, requestId]);

  const handleCheckStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!requestId.trim()) {
      toast.error("Please enter a request ID or ticket number");
      return;
    }

    setLoading(true);
    try {
      const data = await checkTicketStatus(requestId.trim());
      setTicket(data);
      toast.success("Ticket status retrieved");
    } catch (error) {
      toast.error("Ticket not found", {
        description: error instanceof Error ? error.message : "Please check the ID and try again",
      });
      setTicket(null);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setRequestId("");
    setTicket(null);
    setExpanded(false);
  };

  const copyToClipboard = async (text: string, label: string) => {
    await navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard!`);
  };

  // Extract customer name from email if not available in response
  const getCustomerName = () => {
    // If backend provides customer_name directly, use it
    if (ticket && 'customer_name' in ticket && ticket.customer_name) {
      return ticket.customer_name;
    }
    
    // Fallback: derive name from email
    if (ticket?.customer_email) {
      const emailPrefix = ticket.customer_email.split("@")[0];
      // Handle special cases like whatsapp_1234567890
      if (emailPrefix.startsWith('whatsapp_')) {
        return `WhatsApp User (${emailPrefix.replace('whatsapp_', '')})`;
      }
      // Convert camelCase or underscore to readable name
      return emailPrefix
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (l) => l.toUpperCase());
    }
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Search Card */}
      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-purple-500/5 dark:from-primary/10 dark:to-purple-500/10 shadow-xl backdrop-blur-sm">
        <CardContent className="p-6">
          <form onSubmit={handleCheckStatus} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="request-id" className="text-sm font-medium flex items-center gap-2">
                <Search className="w-4 h-4 text-primary" />
                Request ID or Ticket Number
              </Label>
              <div className="flex gap-2">
                <Input
                  id="request-id"
                  placeholder="Enter your request ID (e.g., CS-2026-XXXXX)"
                  value={requestId}
                  onChange={(e) => setRequestId(e.target.value)}
                  className="flex-1 bg-background/50 border-primary/10 focus:border-primary/30 transition-colors font-mono"
                />
                <Button
                  type="submit"
                  variant="gradient"
                  disabled={loading}
                  className="shrink-0"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Search className="w-4 h-4" />
                  )}
                </Button>
                {ticket && (
                  <Button type="button" variant="outline" onClick={handleClear}>
                    Clear
                  </Button>
                )}
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="border-primary/20 overflow-hidden">
              <CardContent className="p-8">
                <div className="flex items-center justify-center gap-3 text-muted-foreground">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  <span>Fetching ticket status...</span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {ticket && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="space-y-4"
          >
            {/* Main Ticket Details Card */}
            <Card className="border-primary/20 overflow-hidden shadow-xl">
              {/* Status Color Bar */}
              <div className={`h-1 bg-gradient-to-r ${statusColors[ticket.status.toLowerCase()] || "from-gray-400 to-gray-500"}`} />
              
              <CardContent className="p-6 sm:p-8">
                {/* Header: Status Badge + Ticket Number */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-8">
                  <div className="flex items-start gap-4">
                    <div className={`w-14 h-14 rounded-full bg-gradient-to-br ${statusColors[ticket.status.toLowerCase()] || "from-gray-400 to-gray-500"} flex items-center justify-center shadow-lg flex-shrink-0`}>
                      {statusIcons[ticket.status.toLowerCase()] || <Ticket className="w-7 h-7 text-white" />}
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold capitalize bg-gradient-to-r ${statusColors[ticket.status.toLowerCase()] || "from-gray-400 to-gray-500"} text-white shadow`}>
                          {statusLabels[ticket.status.toLowerCase()] || ticket.status}
                        </span>
                      </div>
                      
                      {/* Ticket Number - PRIMARY (Large, Bold, with Copy) */}
                      <div className="flex items-center gap-3">
                        <h2 className="text-2xl sm:text-3xl font-bold text-foreground">
                          {ticket.ticket_number || "N/A"}
                        </h2>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => copyToClipboard(ticket.ticket_number, "Ticket number")}
                          className="h-8 w-8 hover:bg-primary/10"
                          title="Copy ticket number"
                        >
                          <Clipboard className="w-4 h-4" />
                        </Button>
                      </div>
                      
                      {/* Request ID - SECONDARY (Smaller, Muted) */}
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span className="text-xs">Request ID:</span>
                        <code className="text-xs bg-muted/50 px-2 py-0.5 rounded font-mono max-w-[200px] truncate">
                          {ticket.request_id}
                        </code>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => copyToClipboard(ticket.request_id, "Request ID")}
                          className="h-6 w-6 hover:bg-primary/10"
                          title="Copy request ID"
                        >
                          <Clipboard className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                  
                  {/* Created Date */}
                  <div className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/30 px-4 py-2 rounded-lg">
                    <Calendar className="w-4 h-4" />
                    <div>
                      <p className="text-xs">Created</p>
                      <p className="font-medium">
                        {ticket.created_at && ticket.created_at !== '1970-01-01T00:00:00Z' ? (
                          new Date(ticket.created_at).toLocaleDateString("en-US", {
                            year: "numeric",
                            month: "long",
                            day: "numeric"
                          })
                        ) : (
                          'N/A'
                        )}
                      </p>
                    </div>
                  </div>
                  
                  {/* Auto-refresh indicator */}
                  {ticket.status?.toLowerCase() !== 'completed' && (
                    <div className="flex items-center gap-2 text-xs text-primary bg-primary/10 px-3 py-2 rounded-lg">
                      <RefreshCw className="w-3 h-3 animate-spin" />
                      <span>Auto-refreshing...</span>
                    </div>
                  )}
                </div>

                {/* Customer Information Section */}
                <div className="mb-8 p-5 rounded-xl bg-gradient-to-br from-primary/5 to-purple-500/5 border border-primary/10">
                  <div className="flex items-center gap-2 mb-4">
                    <User className="w-4 h-4 text-primary" />
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Customer Information</h3>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Customer Name */}
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center flex-shrink-0">
                        <User className="w-5 h-5 text-primary" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-muted-foreground mb-0.5">Customer Name</p>
                        <p className="text-base font-semibold text-foreground truncate">
                          {getCustomerName() || "Not provided"}
                        </p>
                      </div>
                    </div>
                    
                    {/* Customer Email */}
                    {ticket.customer_email && (
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center flex-shrink-0">
                          <Mail className="w-5 h-5 text-primary" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-xs text-muted-foreground mb-0.5">Email Address</p>
                          <p className="text-base font-medium text-foreground truncate">
                            {ticket.customer_email}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Ticket Details Grid - Subject, Category, Priority */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
                  {ticket.subject && (
                    <div className="sm:col-span-2 flex items-start gap-3 p-4 rounded-xl bg-muted/30 border border-primary/10">
                      <FileText className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-muted-foreground mb-1">Subject</p>
                        <p className="text-sm font-medium text-foreground break-words">{ticket.subject}</p>
                      </div>
                    </div>
                  )}
                  {ticket.category && (
                    <div className="flex items-start gap-3 p-4 rounded-xl bg-muted/30 border border-primary/10">
                      <Tag className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-muted-foreground mb-1">Category</p>
                        <p className="text-sm font-semibold capitalize text-foreground">{ticket.category}</p>
                      </div>
                    </div>
                  )}
                  {ticket.priority && (
                    <div className="flex items-start gap-3 p-4 rounded-xl bg-muted/30 border border-primary/10">
                      <TrendingUp className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-muted-foreground mb-1">Priority</p>
                        <p className={`text-sm font-semibold capitalize ${
                          ticket.priority === "high" ? "text-red-500" :
                          ticket.priority === "medium" ? "text-yellow-500" :
                          "text-green-500"
                        }`}>
                          {ticket.priority}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* AI Response Section */}
                {ticket.response && (
                  <div className="mb-8">
                    <div className="flex items-center gap-2 mb-3">
                      <MessageCircle className="w-5 h-5 text-primary" />
                      <h3 className="text-lg font-semibold">AI Response</h3>
                    </div>
                    <div className="p-5 rounded-xl bg-gradient-to-br from-primary/10 to-purple-500/10 border border-primary/20">
                      <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">{ticket.response}</p>
                    </div>
                  </div>
                )}

                {/* Sentiment Analysis */}
                {ticket.sentiment && (
                  <div className="flex items-center gap-3 p-4 rounded-xl bg-muted/30 border border-primary/10 inline-block">
                    <TrendingUp className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">Sentiment:</span>
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold capitalize ${
                      ticket.sentiment === "positive" ? "bg-green-500/20 text-green-400" :
                      ticket.sentiment === "negative" ? "bg-red-500/20 text-red-400" :
                      "bg-yellow-500/20 text-yellow-400"
                    }`}>
                      {ticket.sentiment}
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Messages History Toggle */}
            {ticket.messages && ticket.messages.length > 0 && (
              <Card className="border-primary/20">
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="w-full p-4 flex items-center justify-between hover:bg-muted/30 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <MessageCircle className="w-4 h-4 text-primary" />
                    <span className="font-medium">Message History ({ticket.messages.length})</span>
                  </div>
                  {expanded ? (
                    <ChevronUp className="w-4 h-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-muted-foreground" />
                  )}
                </button>
                <AnimatePresence>
                  {expanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      <CardContent className="pt-0 space-y-3">
                        {ticket.messages.map((msg, idx) => (
                          <div
                            key={idx}
                            className={`p-4 rounded-xl ${
                              msg.role === "assistant"
                                ? "bg-primary/10 border border-primary/20"
                                : "bg-muted/50"
                            }`}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs font-semibold capitalize text-primary flex items-center gap-1.5">
                                {msg.role === "assistant" && <MessageCircle className="w-3 h-3" />}
                                {msg.role}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {new Date(msg.timestamp).toLocaleString("en-US", {
                                  year: "numeric",
                                  month: "short",
                                  day: "numeric",
                                  hour: "2-digit",
                                  minute: "2-digit"
                                })}
                              </span>
                            </div>
                            <p className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
                              {msg.content}
                            </p>
                          </div>
                        ))}
                      </CardContent>
                    </motion.div>
                  )}
                </AnimatePresence>
              </Card>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
