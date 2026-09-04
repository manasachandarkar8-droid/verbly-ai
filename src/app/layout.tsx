import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "@/styles/globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Verbly AI",
    template: "%s | Verbly AI",
  },
  description:
    "AI-powered website content analysis and optimization platform.",
  applicationName: "Verbly AI",
  keywords: [
    "AI content analysis",
    "website content optimization",
    "SEO analysis",
    "content readability",
    "Verbly AI",
  ],
  openGraph: {
    title: "Verbly AI",
    description:
      "AI-powered website content analysis and optimization platform.",
    type: "website",
    siteName: "Verbly AI",
  },
  twitter: {
    card: "summary",
    title: "Verbly AI",
    description:
      "AI-powered website content analysis and optimization platform.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}
      >
        {children}
      </body>
    </html>
  );
}