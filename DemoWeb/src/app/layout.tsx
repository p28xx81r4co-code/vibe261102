import type { Metadata } from "next"
import Link from "next/link"
import { Geist_Mono, Noto_Sans_KR } from "next/font/google"
import "./globals.css"

const notoSansKr = Noto_Sans_KR({
  variable: "--font-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "DemoWeb 게시판",
  description: "Next.js, shadcn/ui, TypeScript로 만든 게시판",
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${notoSansKr.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-muted/30 font-sans">
        <header className="border-b bg-background">
          <div className="mx-auto flex h-14 w-full max-w-4xl items-center justify-between px-4">
            <Link href="/posts" className="text-lg font-bold tracking-tight">
              DemoWeb 게시판
            </Link>
            <nav className="text-sm text-muted-foreground">
              <Link href="/posts/new" className="hover:text-foreground">
                글쓰기
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8">{children}</main>
        <footer className="border-t bg-background py-4 text-center text-xs text-muted-foreground">
          DemoWeb · Next.js + shadcn/ui
        </footer>
      </body>
    </html>
  )
}
