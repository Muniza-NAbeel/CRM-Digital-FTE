"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import confetti from "canvas-confetti";
import { toast } from "sonner";
import {
  Send,
  Mail,
  User,
  FileText,
  MessageSquare,
  Tag,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Clipboard,
  Ticket,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";

import { submitTicket } from "@/lib/api";
import { FormStatus, SubmitTicketRequest } from "@/types";

const formSchema = z.object({
  name: z.string().optional(),
  customer_email: z.string().email("Please enter a valid email address"),
  subject: z.string().min(5, "Subject must be at least 5 characters"),
  category: z.enum(["general", "technical", "billing", "feedback", "bug_report"]),
  priority: z.enum(["low", "medium", "high"]),
  message: z.string().min(20, "Message must be at least 20 characters"),
});

type FormData = z.infer<typeof formSchema>;

interface SupportFormProps {
  onTicketSubmitted?: (requestId: string) => void;
}

export function SupportForm({ onTicketSubmitted }: SupportFormProps) {
  const [status, setStatus] = useState<FormStatus>("idle");
  const [requestId, setRequestId] = useState<string>("");

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      category: "general",
      priority: "medium",
    },
  });

  // Auto-save email to localStorage
  const email = watch("customer_email");
  useEffect(() => {
    if (email) {
      localStorage.setItem("support_email", email);
    }
  }, [email]);

  // Load saved email on mount
  useEffect(() => {
    const savedEmail = localStorage.getItem("support_email");
    if (savedEmail) {
      setValue("customer_email", savedEmail);
    }
  }, [setValue]);

  const onSubmit = async (data: FormData) => {
    setStatus("submitting");
    try {
      const payload: SubmitTicketRequest = {
        name: data.name || undefined,
        customer_email: data.customer_email,
        subject: data.subject,
        message: data.message,
        channel: "web_form",
        category: data.category,
        priority: data.priority,
      };

      const response = await submitTicket(payload);
      setRequestId(response.request_id);
      setStatus("success");

      // Trigger confetti
      confetti({
        particleCount: 150,
        spread: 70,
        origin: { y: 0.6 },
        colors: ["#6366f1", "#8b5cf6", "#a855f7", "#d946ef"],
      });

      toast.success("Ticket submitted successfully!", {
        description: `Your ticket number is ${response.request_id.slice(0, 8)}...`,
      });

      onTicketSubmitted?.(response.request_id);
    } catch (error) {
      setStatus("error");
      toast.error("Failed to submit ticket", {
        description: error instanceof Error ? error.message : "Please try again",
      });
    }
  };

  const handleCopyRequestId = () => {
    navigator.clipboard.writeText(requestId);
    toast.success("Copied to clipboard!");
  };

  const handleNewTicket = () => {
    reset();
    setStatus("idle");
    setRequestId("");
  };

  return (
    <AnimatePresence mode="wait">
      {status === "success" ? (
        <motion.div
          key="success"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.3 }}
        >
          <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-purple-500/5 dark:from-primary/10 dark:to-purple-500/10 shadow-2xl">
            <CardContent className="p-8 pt-12">
              <div className="text-center space-y-6">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 200, delay: 0.2 }}
                  className="mx-auto w-20 h-20 rounded-full bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center shadow-lg shadow-green-500/30"
                >
                  <CheckCircle2 className="w-10 h-10 text-white" />
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="space-y-2"
                >
                  <h2 className="text-3xl font-bold bg-gradient-to-r from-green-400 to-emerald-500 bg-clip-text text-transparent">
                    Ticket Submitted!
                  </h2>
                  <p className="text-muted-foreground">
                    We&apos;ve received your support request and will get back to you soon.
                  </p>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="bg-muted/50 rounded-lg p-6 max-w-md mx-auto border border-primary/20"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <Ticket className="w-5 h-5 text-primary" />
                      <span className="text-sm text-muted-foreground">Ticket Number</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <code className="text-lg font-mono font-semibold text-primary">
                        {requestId.slice(0, 8)}...
                      </code>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={handleCopyRequestId}
                        className="h-8 w-8"
                      >
                        <Clipboard className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                  className="flex flex-col sm:flex-row gap-3 justify-center pt-4"
                >
                  <Button onClick={handleNewTicket} variant="gradient" size="lg" className="shadow-lg">
                    <Sparkles className="w-4 h-4 mr-2" />
                    Submit Another Ticket
                  </Button>
                </motion.div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      ) : (
        <motion.div
          key="form"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
        >
          <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-purple-500/5 dark:from-primary/10 dark:to-purple-500/10 shadow-2xl backdrop-blur-sm">
            <CardContent className="p-6 sm:p-8">
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                {/* Name Field */}
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-sm font-medium flex items-center gap-2">
                    <User className="w-4 h-4 text-primary" />
                    Full Name <span className="text-muted-foreground font-normal">(optional)</span>
                  </Label>
                  <Input
                    id="name"
                    placeholder="John Doe"
                    {...register("name")}
                    className="bg-background/50 border-primary/10 focus:border-primary/30 transition-colors"
                  />
                </div>

                {/* Email Field */}
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-sm font-medium flex items-center gap-2">
                    <Mail className="w-4 h-4 text-primary" />
                    Email Address <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="john@example.com"
                    {...register("customer_email")}
                    className={`bg-background/50 border-primary/10 focus:border-primary/30 transition-colors ${
                      errors.customer_email ? "border-destructive focus:border-destructive" : ""
                    }`}
                  />
                  {errors.customer_email && (
                    <motion.p
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="text-sm text-destructive flex items-center gap-1"
                    >
                      <AlertCircle className="w-3 h-3" />
                      {errors.customer_email.message}
                    </motion.p>
                  )}
                </div>

                {/* Subject Field */}
                <div className="space-y-2">
                  <Label htmlFor="subject" className="text-sm font-medium flex items-center gap-2">
                    <FileText className="w-4 h-4 text-primary" />
                    Subject <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="subject"
                    placeholder="Brief description of your issue"
                    {...register("subject")}
                    className={`bg-background/50 border-primary/10 focus:border-primary/30 transition-colors ${
                      errors.subject ? "border-destructive focus:border-destructive" : ""
                    }`}
                  />
                  {errors.subject && (
                    <motion.p
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="text-sm text-destructive flex items-center gap-1"
                    >
                      <AlertCircle className="w-3 h-3" />
                      {errors.subject.message}
                    </motion.p>
                  )}
                </div>

                {/* Category and Priority Row */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Category */}
                  <div className="space-y-2">
                    <Label htmlFor="category" className="text-sm font-medium flex items-center gap-2">
                      <Tag className="w-4 h-4 text-primary" />
                      Category
                    </Label>
                    <Select
                      onValueChange={(value) => setValue("category", value as any)}
                      defaultValue={watch("category")}
                    >
                      <SelectTrigger className="bg-background/50 border-primary/10">
                        <SelectValue placeholder="Select category" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="general">General Inquiry</SelectItem>
                        <SelectItem value="technical">Technical Support</SelectItem>
                        <SelectItem value="billing">Billing</SelectItem>
                        <SelectItem value="feedback">Feedback</SelectItem>
                        <SelectItem value="bug_report">Bug Report</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Priority */}
                  <div className="space-y-2">
                    <Label htmlFor="priority" className="text-sm font-medium flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-primary" />
                      Priority
                    </Label>
                    <Select
                      onValueChange={(value) => setValue("priority", value as any)}
                      defaultValue={watch("priority")}
                    >
                      <SelectTrigger className="bg-background/50 border-primary/10">
                        <SelectValue placeholder="Select priority" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Message Field */}
                <div className="space-y-2">
                  <Label htmlFor="message" className="text-sm font-medium flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-primary" />
                    Message <span className="text-destructive">*</span>
                  </Label>
                  <Textarea
                    id="message"
                    placeholder="Please describe your issue in detail..."
                    className={`min-h-[150px] bg-background/50 border-primary/10 focus:border-primary/30 transition-colors resize-none ${
                      errors.message ? "border-destructive focus:border-destructive" : ""
                    }`}
                    {...register("message")}
                  />
                  {errors.message && (
                    <motion.p
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="text-sm text-destructive flex items-center gap-1"
                    >
                      <AlertCircle className="w-3 h-3" />
                      {errors.message.message}
                    </motion.p>
                  )}
                </div>

                {/* Submit Button */}
                <Button
                  type="submit"
                  variant="gradient"
                  size="lg"
                  className="w-full h-12 text-base font-semibold shadow-lg shadow-primary/25 hover:shadow-primary/40 transition-shadow"
                  disabled={status === "submitting"}
                >
                  {status === "submitting" ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <Send className="w-5 h-5 mr-2" />
                      Submit Ticket
                    </>
                  )}
                </Button>

                {/* Helper Text */}
                <p className="text-xs text-center text-muted-foreground">
                  Our support team typically responds within 24 hours. For urgent issues, please select &quot;High&quot; priority.
                </p>
              </form>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
