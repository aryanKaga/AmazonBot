import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Amazon Bot Assistant",
  description:
    "AI-powered customer support assistant with RAG, semantic reranking, and human escalation — built on FastAPI, LangGraph, and PostgreSQL.",
  openGraph: {
    title: "Amazon Bot Assistant",
    description: "AI customer support with human-in-the-loop escalation.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.variable}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
