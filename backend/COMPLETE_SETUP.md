# ✅ Complete Setup - API + Worker Running Together

## 🎯 **Single Command to Start Everything**

```bash
cd D:\assignments\hackathon_five\backend
python run_both.py
```

---

## **What This Starts:**

1. **🌐 API Server** (port 8000)
   - Handles web form submissions
   - Handles Gmail webhooks
   - Handles WhatsApp webhooks
   - Serves frontend

2. **⚙️ Message Worker** (background)
   - Processes pending messages
   - Generates AI responses
   - **Sends actual emails via Gmail API**
   - **Sends actual WhatsApp messages via Twilio**

---

## **Expected Output:**

```
============================================================
🎯 Customer Success FTE - Starting All Services
============================================================

Services starting:
  1. 🌐 API Server (port 8000)
  2. ⚙️  Message Worker (email/WhatsApp delivery)

Press Ctrl+C to stop all services
============================================================

============================================================
🚀 Starting API Server on http://0.0.0.0:8000
============================================================

============================================================
⚙️  Starting Message Worker...
============================================================
✓ Worker started - processing inbound messages

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

❤️  Worker heartbeat - Processed: 0, Errors: 0
```

---

## **How to Test:**

### **Test 1: Send Email**
1. Send email to: `support@techcorp.example.com`
2. Wait for worker to process (check terminal)
3. **Response should arrive in your Gmail!**

### **Test 2: Send WhatsApp**
1. Send WhatsApp to: `+14155238886`
2. Wait for worker to process
3. **Response should arrive on WhatsApp!**

### **Test 3: Web Form**
1. Open frontend: `http://localhost:3000`
2. Submit support form
3. **Email notification should arrive!**

---

## **Worker Logs (What to Look For):**

When email/WhatsApp arrives, worker will log:

```
👤 Step 1/6: Identifying customer: user@example.com
   ✓ Customer identified: abc123-def456
🎫 Step 2/6: Creating ticket
   ✓ Ticket created with ticket_number: CS-2026-12345
🤖 Step 3/6: Running AI agent
   ✓ AI response generated: 250 chars
📊 Step 4/6: Analyzing sentiment
✓ Sentiment analyzed: positive (score: 0.8)
⚠️ Step 5/6: Checking escalation
   ✓ Escalation check: OK
💾 Step 6/6: Saving results
✓ Results saved: ticket=CS-2026-12345, conversation=xyz789
📤 Step 7/7: Sending response via gmail
   ✓ Gmail response sent to user@example.com
   ✓ Response sent successfully via gmail
```

**If you see Step 7 with ✓, response was sent!** 🎉

---

## **Troubleshooting:**

### **Issue: Email not received**

**Check 1:** Worker running?
```bash
# Look for worker heartbeat in terminal
❤️  Worker heartbeat - Processed: X, Errors: 0
```

**Check 2:** Gmail credentials configured?
```bash
# In .env file, verify:
APP_GMAIL_CLIENT_ID=808858868409-jg8al2i7k8iqgv9dr5ilbpji0ulju0ti.apps.googleusercontent.com
APP_GMAIL_CLIENT_SECRET=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
APP_GMAIL_REFRESH_TOKEN=1//0gLZtXoQw5c2-CgYIARAAGBASNwF-L9IrVqU8bX9qjN1u5v3zjv7mM8
APP_GMAIL_SENDER_EMAIL=support@techcorp.example.com
```

**Check 3:** Worker logs show errors?
```bash
# Look for these in terminal:
✗ Failed to send response via gmail
# or
✗ Gmail send failed: [error message]
```

---

## **Stop Services:**

Press **`Ctrl+C`** in terminal to stop both:
```
^C
⏹️  Stopping worker...
✓ Database connection closed
✓ Worker stopped

✅ All services stopped successfully!
```

---

## **Quick Reference:**

| Task | Command |
|------|---------|
| **Start Everything** | `python run_both.py` |
| **Stop Everything** | `Ctrl+C` |
| **Test API** | `curl http://localhost:8000/health` |
| **Test Dashboard** | `curl http://localhost:8000/api/v1/dashboard` |
| **Check Worker** | Look for heartbeat in terminal |

---

## **✅ Success Indicators:**

- ✅ API Server listening on port 8000
- ✅ Worker heartbeat showing every 30 seconds
- ✅ No errors in terminal
- ✅ Emails actually being sent (check Gmail)
- ✅ WhatsApp messages being sent (check phone)

---

**Ab tumhara FTE complete hai!** 🚀

**Email bhejo → Worker process karega → Response wapis aayega!** 🎉
