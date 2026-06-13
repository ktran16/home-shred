import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { BottomNav } from "@/components/nav";
import { Providers } from "@/components/providers";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "HomeShred",
  description: "Self-hosted rule-based personal trainer",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-zinc-50 dark:bg-black">
        <Providers>
          <main className="mx-auto w-full max-w-md flex-1 px-4 py-6">{children}</main>
          <BottomNav />
        </Providers>
      </body>
    </html>
  );
}
