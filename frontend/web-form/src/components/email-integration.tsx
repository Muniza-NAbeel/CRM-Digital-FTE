"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  Mail,
  Send,
  Inbox,
  Clock,
  Shield,
  Zap,
  Paperclip,
  Sparkles,
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

export function EmailIntegration({ onGoToStatus }: { onGoToStatus?: (requestId: string) => void }) {
  const [customerName, setCustomerName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [copied, setCopied] = useState(false);
  const [submittedRequest, setSubmittedRequest] = useState<{
    requestId: string;
    status: string;
  } | null>(null);

  // Support email from .env
  const supportEmail = "support@techcorp.example.com";

  const handleSendEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email.trim() || !message.trim() || !subject.trim()) {
      toast.error("Please fill in all required fields");
      return;
    }

    setIsSending(true);
    try {
      const payload: SubmitTicketRequest = {
        name: customerName || undefined,
        customer_email: email,
        subject: subject,
        message: message,
        channel: "gmail",
        category: "general",
        priority: "medium",
      };

      console.log("Sending email:", payload);
      
      const result = await submitTicket(payload);
      
      console.log("Response received:", result);
      
      // Store the result for display
      setSubmittedRequest({
        requestId: result.request_id,
        status: result.status,
      });
      
      toast.success("✅ Email sent successfully!", {
        description: `Request ID: ${result.request_id}`,
        duration: 10000,
      });

      // Clear form
      setCustomerName("");
      setEmail("");
      setSubject("");
      setMessage("");
      
    } catch (error) {
      console.error("Error sending email:", error);
      toast.error("❌ Failed to send email", {
        description: error instanceof Error ? error.message : "Please try again",
        duration: 10000,
      });
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <Card className="border-blue-500/20 bg-gradient-to-br from-blue-500/5 to-cyan-500/5 dark:from-blue-500/10 dark:to-cyan-500/10 shadow-xl backdrop-blur-sm">
        <CardContent className="p-6">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg">
              <Mail className="w-8 h-8 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">Email Support</h2>
              <p className="text-sm text-blue-300">Send us an email for detailed assistance</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <Inbox className="w-5 h-5 text-blue-400" />
              <div>
                <p className="text-xs text-blue-300 font-semibold">Detailed</p>
                <p className="text-xs text-blue-400">For complex issues</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <Shield className="w-5 h-5 text-blue-400" />
              <div>
                <p className="text-xs text-blue-300 font-semibold">Secure</p>
                <p className="text-xs text-blue-400">Encrypted communication</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <Clock className="w-5 h-5 text-blue-400" />
              <div>
                <p className="text-xs text-blue-300 font-semibold">24/7</p>
                <p className="text-xs text-blue-400">Response within hours</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Send Email Form */}
      <Card className="border-blue-500/20 bg-blue-500/5 shadow-lg">
        <CardContent className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <Mail className="w-5 h-5 text-blue-400" />
            <h3 className="text-lg font-semibold text-white">Send Email</h3>
          </div>

          <form onSubmit={handleSendEmail} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-sm font-medium text-blue-300">
                  Your Name <span className="text-blue-500/50">(optional)</span>
                </Label>
                <Input
                  id="name"
                  placeholder="John Doe"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  className="bg-blue-500/10 border-blue-500/20 focus:border-blue-500/50 text-white"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium text-blue-300">
                  Email Address <span className="text-red-400">*</span>
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="john@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-blue-500/10 border-blue-500/20 focus:border-blue-500/50 text-white"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="subject" className="text-sm font-medium text-blue-300">
                Subject <span className="text-red-400">*</span>
              </Label>
              <Input
                id="subject"
                placeholder="Brief description of your issue"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="bg-blue-500/10 border-blue-500/20 focus:border-blue-500/50 text-white"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="message" className="text-sm font-medium text-blue-300">
                Message <span className="text-red-400">*</span>
              </Label>
              <Textarea
                id="message"
                placeholder="Describe your issue in detail..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={6}
                className="bg-blue-500/10 border-blue-500/20 focus:border-blue-500/50 text-white resize-none"
                required
              />
            </div>

            <div className="flex items-center gap-2 text-xs text-blue-300">
              <Paperclip className="w-4 h-4" />
              <span>For attachments, please send directly from your email client</span>
            </div>

            <Button
              type="submit"
              disabled={isSending}
              variant="gradient"
              className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600"
            >
              {isSending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Send Email
                </>
              )}
            </Button>
          </form>

          {/* Success Message with Request ID */}
          {submittedRequest && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 p-4 rounded-xl bg-blue-500/20 border border-blue-500/40"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-full bg-blue-500/30 flex items-center justify-center">
                  <CheckCircle2 className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <h4 className="font-semibold text-white">Email Sent Successfully!</h4>
                  <p className="text-xs text-blue-300">Save your Request ID for tracking</p>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-500/10 border border-blue-500/30">
                <div className="flex-1">
                  <p className="text-xs text-blue-300 mb-1">Request ID:</p>
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
                  className="h-10 w-10 hover:bg-blue-500/20 flex-shrink-0"
                >
                  {copied ? (
                    <Check className="w-5 h-5 text-blue-400" />
                  ) : (
                    <Copy className="w-5 h-5 text-blue-400" />
                  )}
                </Button>
              </div>

              <div className="mt-4 flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSubmittedRequest(null);
                    setCustomerName("");
                    setEmail("");
                    setSubject("");
                    setMessage("");
                  }}
                  className="text-xs border-blue-500/30 text-blue-300 hover:bg-blue-500/10"
                >
                  Send Another Email
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (onGoToStatus && submittedRequest) {
                      onGoToStatus(submittedRequest.requestId);
                    }
                  }}
                  className="text-xs border-blue-500/30 text-blue-300 hover:bg-blue-500/10"
                >
                  Track Status
                </Button>
              </div>
            </motion.div>
          )}
        </CardContent>
      </Card>

      {/* What to expect */}
      <Card className="border-blue-500/20 bg-blue-500/5">
        <CardContent className="p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-blue-400" />
            What to expect
          </h3>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-bold text-blue-400">1</span>
              </div>
              <div>
                <p className="text-sm text-blue-300">
                  <strong>Instant confirmation</strong> - Get a ticket ID immediately
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-bold text-blue-400">2</span>
              </div>
              <div>
                <p className="text-sm text-blue-300">
                  <strong>AI-powered response</strong> - Get intelligent help within minutes
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-bold text-blue-400">3</span>
              </div>
              <div>
                <p className="text-sm text-blue-300">
                  <strong>Email thread</strong> - Continue the conversation via email
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
