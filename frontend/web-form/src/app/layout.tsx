import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "sonner";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "TechCorp Support - Customer Service Portal",
  description: "Submit support tickets and track their status with our AI-powered support system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          {children}
          <Toaster
            position="top-right"
            richColors
            closeButton
            toastOptions={{
              classNames: {
                toast: "border-primary/20 bg-background",
                title: "text-foreground",
                description: "text-muted-foreground",
                success: "border-green-500/50",
                error: "border-red-500/50",
              },
            }}
          />
        </ThemeProvider>
      </body>
    </html>
  );
}
