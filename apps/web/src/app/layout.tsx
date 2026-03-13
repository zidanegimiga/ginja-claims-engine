import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { DM_Sans, DM_Mono, Syne } from "next/font/google";
import { SessionProvider } from "@/components/providers/SessionProvider";
import "./globals.css";
import { ThemeProvider } from "@/components/providers/ThemeProvider";

export const metadata: Metadata = {
  title: "Ginja AI Insurance Intelligence",
  description: "AI-powered insurance intelligence platform",
};

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
});

const dmMono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-dm-mono",
});

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${dmSans.variable} ${dmMono.variable} ${syne.variable} font-sans antialiased`}
      >
        <ThemeProvider>
        <SessionProvider>
          <QueryProvider>{children}</QueryProvider>
        </SessionProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
