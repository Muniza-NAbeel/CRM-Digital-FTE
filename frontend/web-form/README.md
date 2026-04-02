# TechCorp Support Form 🎨

A **premium, visually stunning** support ticket form built with Next.js 14, Tailwind CSS, and Framer Motion. Designed to win hackathons with its beautiful glassmorphism design and smooth animations.

![TechCorp Support](https://img.shields.io/badge/Next.js-14-black?logo=next.js&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38B2AC?logo=tailwind-css&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.4-3178C6?logo=typescript&logoColor=white)

## ✨ Features

- 🎨 **Beautiful Glassmorphism Design** - Modern, premium UI with gradient accents
- 🌓 **Dark/Light Mode** - Toggle between themes seamlessly
- 🎭 **Smooth Animations** - Powered by Framer Motion
- ✅ **Real-time Validation** - Beautiful error messages with Zod
- 💾 **Auto-save** - Email saved to localStorage
- 🎊 **Confetti Success** - Celebratory animation on ticket submission
- 📱 **Mobile-First** - Fully responsive design
- 🔔 **Toast Notifications** - Sonner for beautiful toasts
- 📊 **Ticket Status Checker** - Track your support tickets

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ installed
- Backend running at `http://localhost:8000`

### Installation

```bash
# Navigate to the project directory
cd frontend/web-form

# Install dependencies
npm install

# Start the development server
npm run dev
```

The app will be available at **http://localhost:3000**

## 📁 Project Structure

```
frontend/web-form/
├── src/
│   ├── app/
│   │   ├── globals.css      # Global styles & CSS variables
│   │   ├── layout.tsx       # Root layout with providers
│   │   └── page.tsx         # Main page component
│   ├── components/
│   │   ├── ui/              # Reusable UI components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── label.tsx
│   │   │   ├── select.tsx
│   │   │   └── textarea.tsx
│   │   ├── support-form.tsx # Main support form component
│   │   ├── ticket-status.tsx # Ticket status checker
│   │   ├── theme-toggle.tsx # Dark/light mode toggle
│   │   └── theme-provider.tsx # Theme context provider
│   ├── lib/
│   │   ├── api.ts           # API client functions
│   │   └── utils.ts         # Utility functions
│   └── types/
│       └── index.ts         # TypeScript type definitions
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── next.config.js
```

## 🎨 Design Highlights

### Color Palette
- **Primary**: Indigo (#6366f1) - Main brand color
- **Accent**: Purple gradients for depth
- **Dark Mode**: Deep blue-black background
- **Light Mode**: Clean white with subtle grays

### Visual Effects
- Glassmorphism cards with backdrop blur
- Animated gradient backgrounds
- Smooth scale and fade transitions
- Glowing shadows on interactive elements
- Custom scrollbars

## 🔌 API Integration

The form connects to your backend at `http://localhost:8000`:

### Submit Ticket
```typescript
POST /api/v1/messages/submit
Headers: {
  "Content-Type": "application/json",
  "X-API-Key": "dev-api-key-12345"
}
```

### Check Status
```typescript
GET /api/v1/messages/status/{request_id}
```

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| Next.js 14 | App Router, SSR |
| Tailwind CSS | Styling |
| Framer Motion | Animations |
| shadcn/ui | Component primitives |
| Radix UI | Accessible components |
| React Hook Form | Form handling |
| Zod | Schema validation |
| Sonner | Toast notifications |
| Canvas Confetti | Success animation |
| Lucide React | Icons |
| next-themes | Theme management |

## 📝 Form Fields

| Field | Type | Required |
|-------|------|----------|
| Full Name | Text | No |
| Email | Email | Yes |
| Subject | Text | Yes |
| Category | Select | Yes |
| Priority | Select | Yes |
| Message | Textarea | Yes |

## 🎯 Running with Backend

1. **Start your backend** (in a separate terminal):
   ```bash
   # Navigate to your backend directory and start it
   # Example:
   cd backend
   uvicorn main:app --reload --port 8000
   ```

2. **Start the frontend**:
   ```bash
   cd frontend/web-form
   npm run dev
   ```

3. **Open** http://localhost:3000 in your browser

## 🎨 Customization

### Change Brand Colors
Edit `tailwind.config.js`:
```js
colors: {
  primary: {
    DEFAULT: "#your-color", // Change this
  }
}
```

### Modify API Endpoint
Edit `src/lib/api.ts`:
```typescript
const API_BASE_URL = "http://your-backend-url";
const API_KEY = "your-api-key";
```

## 📱 Responsive Breakpoints

- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

## 🏆 Hackathon Tips

1. **First Impression**: The hero section and gradient backgrounds grab attention
2. **Micro-interactions**: Hover states, focus rings, and smooth transitions
3. **Success Moment**: Confetti animation creates a memorable experience
4. **Professional Touch**: Status checker shows completeness
5. **Accessibility**: Proper labels, focus states, and semantic HTML

## 📄 License

MIT License - Feel free to use in your hackathon!

---

Built with ❤️ for **Hackathon Five**
*TechCorp Support - Premium Customer Experience*
