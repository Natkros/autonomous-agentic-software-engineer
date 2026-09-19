import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ForgeAI",
  description: "An autonomous AI software engineer that plans, builds, tests, debugs, reviews, and ships software.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
