import type { Metadata } from "next"
import { JetBrains_Mono, Press_Start_2P } from "next/font/google"
import "./globals.css"

const mono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono-loaded",
})

const pixel = Press_Start_2P({
  subsets: ["latin"],
  weight: "400",
  display: "swap",
  variable: "--font-pixel",
})

export const metadata: Metadata = {
  metadataBase: new URL("https://minecraftbench.com"),
  title: "minecraftbench.com: Agentic Minecraft Benchmark Results",
  description:
    "Open agentic Minecraft benchmark results: frontier LLM agents surviving, crafting, and building in vanilla Minecraft, with transcripts and datasets.",
  authors: [{ name: "Elliot Arledge", url: "https://elliotarledge.com" }],
  creator: "Elliot Arledge",
  publisher: "minecraftbench.com",
  keywords: [
    "Minecraft",
    "benchmark",
    "coding agents",
    "LLM evaluation",
    "agentic Minecraft",
    "embodied agents",
  ],
  openGraph: {
    title: "minecraftbench.com: Agentic Minecraft Benchmark Results",
    description:
      "Open agentic Minecraft benchmark results: frontier LLM agents surviving, crafting, and building in vanilla Minecraft.",
    url: "https://minecraftbench.com",
    siteName: "minecraftbench.com",
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${mono.variable} ${pixel.variable}`} data-theme="dark">
      <body className="min-h-screen">
        <main className="container mx-auto px-4 sm:px-6 max-w-7xl py-10">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  )
}

function Footer() {
  return (
    <footer className="border-t border-[var(--color-border)] mt-16">
      <div className="container mx-auto max-w-7xl px-4 sm:px-6 py-6 text-xs text-[var(--color-fg-muted)] flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row gap-2 sm:items-center sm:justify-between">
          <span>
            built by <a href="https://elliotarledge.com">elliot arledge</a>
            {" · "}
            <a href="mailto:elliot@arledge.net">elliot@arledge.net</a>
          </span>
          <span>
            source:{" "}
            <a href="https://github.com/Infatoshi/minecraftbench.com">
              github.com/Infatoshi/minecraftbench.com
            </a>
          </span>
        </div>
        <p className="leading-relaxed">
          Disclaimer: This site is not affiliated with or endorsed by Mojang or
          Microsoft. Minecraft is a trademark of Mojang Synergies AB. This is
          an independent benchmark hub for agent runs made by Elliot Arledge (
          <a href="https://x.com/elliotarledge">x.com/elliotarledge</a>
          ).
        </p>
      </div>
    </footer>
  )
}
