"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  MessageSquare,
  Send,
  Clock,
  Shield,
  Zap,
  Globe,
  Loader2,
  CheckCircle2,
  Copy,
  Check,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

import { submitTicket } from "@/lib/api";
import { SubmitTicketRequest } from "@/types";

export function WhatsAppIntegration({ onGoToStatus }: { onGoToStatus?: (requestId: string) => void }) {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [copied, setCopied] = useState(false);
  const [submittedRequest, setSubmittedRequest] = useState<{
    requestId: string;
    status: string;
  } | null>(null);

  // Twilio WhatsApp number from .env
  const whatsappNumber = "+14155238886";

  const handleSendWhatsApp = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!phoneNumber.trim() || !message.trim()) {
      toast.error("Please fill in all fields");
      return;
    }

    setIsSending(true);
    try {
      // Submit to backend which will send via WhatsApp
      const payload: SubmitTicketRequest = {
        customer_email: `whatsapp_${phoneNumber.replace(/\D/g, '')}@channel.internal`,
        customer_phone: phoneNumber,
        subject: `WhatsApp: ${message.substring(0, 50)}...`,
        message: message,
        channel: "whatsapp",
        category: "general",
        priority: "medium",
      };

      console.log("Sending WhatsApp message:", payload);
      
      const result = await submitTicket(payload);
      
      console.log("Response received:", result);
      
      // Store the result for display
      setSubmittedRequest({
        requestId: result.request_id,
        status: result.status,
      });
      
      toast.success("✅ Message sent successfully!", {
        description: `Request ID: ${result.request_id}`,
        duration: 10000,
      });

      // Clear form
      setPhoneNumber("");
      setMessage("");
      
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error("❌ Failed to send message", {
        description: error instanceof Error ? error.message : "Please try again",
        duration: 10000,
      });
    } finally {
      setIsSending(false);
    }
  };

  const handleCopyNumber = () => {
    navigator.clipboard.writeText(whatsappNumber);
    setCopied(true);
    toast.success("WhatsApp number copied!");
    setTimeout(() => setCopied(false), 2000);
  };

  const openWhatsAppWeb = () => {
    const url = `https://wa.me/${whatsappNumber.replace(/\D/g, '')}`;
    window.open(url, '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <Card className="border-green-500/20 bg-gradient-to-br from-green-500/5 to-emerald-500/5 dark:from-green-500/10 dark:to-emerald-500/10 shadow-xl backdrop-blur-sm">
        <CardContent className="p-6">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center shadow-lg">
              <MessageSquare className="w-8 h-8 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">WhatsApp Support</h2>
              <p className="text-sm text-green-300">Chat with us instantly on WhatsApp</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
              <Zap className="w-5 h-5 text-green-400" />
              <div>
                <p className="text-xs text-green-300 font-semibold">Instant</p>
                <p className="text-xs text-green-400">Real-time chat</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
              <Shield className="w-5 h-5 text-green-400" />
              <div>
                <p className="text-xs text-green-300 font-semibold">Secure</p>
                <p className="text-xs text-green-400">End-to-end encrypted</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
              <Globe className="w-5 h-5 text-green-400" />
              <div>
                <p className="text-xs text-green-300 font-semibold">24/7</p>
                <p className="text-xs text-green-400">Always available</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Send Message Form */}
      <Card className="border-green-500/20 bg-green-500/5 shadow-lg">
        <CardContent className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <MessageSquare className="w-5 h-5 text-green-400" />
            <h3 className="text-lg font-semibold text-white">Send Message</h3>
          </div>

          <form onSubmit={handleSendWhatsApp} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="phone" className="text-sm font-medium text-green-300">
                WhatsApp Number
              </Label>
              <Input
                id="phone"
                placeholder="+1 (555) 123-4567"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                className="bg-green-500/10 border-green-500/20 focus:border-green-500/50 text-white"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="message" className="text-sm font-medium text-green-300">
                Your Message
              </Label>
              <Textarea
                id="message"
                placeholder="Type your message here..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={4}
                className="bg-green-500/10 border-green-500/20 focus:border-green-500/50 text-white resize-none"
              />
            </div>

            <Button
              type="submit"
              disabled={isSending}
              variant="gradient"
              className="w-full bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600"
            >
              {isSending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Send via WhatsApp
                </>
              )}
            </Button>
          </form>

          {/* Success Message with Request ID */}
          {submittedRequest && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 p-4 rounded-xl bg-green-500/20 border border-green-500/40"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-full bg-green-500/30 flex items-center justify-center">
                  <CheckCircle2 className="w-6 h-6 text-green-400" />
                </div>
                <div>
                  <h4 className="font-semibold text-white">Message Sent Successfully!</h4>
                  <p className="text-xs text-green-300">Save your Request ID for tracking</p>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/10 border border-green-500/30">
                <div className="flex-1">
                  <p className="text-xs text-green-300 mb-1">Request ID:</p>
                  <code className="text-sm font-mono text-white break-all">
                    {submittedRequest.requestId}
                  </code>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    navigator.clipboard.writeText(submittedRequest.requestId);
                    setCopied(true);
                    toast.success("Request ID copied!");
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  className="h-10 w-10 hover:bg-green-500/20 flex-shrink-0"
                >
                  {copied ? (
                    <Check className="w-5 h-5 text-green-400" />
                  ) : (
                    <Copy className="w-5 h-5 text-green-400" />
                  )}
                </Button>
              </div>

              <div className="mt-4 flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSubmittedRequest(null);
                    setPhoneNumber("");
                    setMessage("");
                  }}
                  className="text-xs border-green-500/30 text-green-300 hover:bg-green-500/10"
                >
                  Send Another Message
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (onGoToStatus && submittedRequest) {
                      onGoToStatus(submittedRequest.requestId);
                    }
                  }}
                  className="text-xs border-green-500/30 text-green-300 hover:bg-green-500/10"
                >
                  Track Status
                </Button>
              </div>
            </motion.div>
          )}
        </CardContent>
      </Card>

      {/* How it works */}
      <Card className="border-green-500/20 bg-green-500/5">
        <CardContent className="p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-green-400" />
            How it works
          </h3>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-bold text-green-400">1</span>
              </div>
              <div>
                <p className="text-sm text-green-300">
                  <strong>Fill the form</strong> - Enter your WhatsApp number and message
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-bold text-green-400">2</span>
              </div>
              <div>
                <p className="text-sm text-green-300">
                  <strong>Send message</strong> - Click send and get your Request ID
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-bold text-green-400">3</span>
              </div>
              <div>
                <p className="text-sm text-green-300">
                  <strong>Get AI response</strong> - Track your ticket status anytime
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
