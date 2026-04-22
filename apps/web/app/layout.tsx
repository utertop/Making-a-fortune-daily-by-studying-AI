import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "AI Signal Radar",
  description: "Local-first AI signal radar and learning workspace",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
