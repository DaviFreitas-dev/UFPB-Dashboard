import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "NEXO",
  description: "Organização de estudos e rotina.",
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#0d0f12",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
