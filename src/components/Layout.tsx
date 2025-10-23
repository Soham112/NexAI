'use client'

import React from 'react'
import TopNavigation from './TopNavigation'
import Sidebar from './Sidebar'

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="main-container">
      <TopNavigation />
      <Sidebar />
      {children}
    </div>
  )
}

export default Layout
