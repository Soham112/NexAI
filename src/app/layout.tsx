import { Inter } from 'next/font/google'
import './globals.css'
import { ChatProvider } from '../components/ChatContext'
import Layout from '../components/Layout'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'NextAI - Intelligent Assistant',
  description: 'AI-powered assistant for courses, jobs, and learning resources',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ChatProvider>
          <Layout>
            {children}
          </Layout>
        </ChatProvider>
      </body>
    </html>
  )
}
