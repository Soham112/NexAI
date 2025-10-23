'use client'

import React from 'react'
import { FaBars, FaEdit, FaCog } from 'react-icons/fa'

const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <div className="sidebar-item active">
        <FaBars />
      </div>
      <div className="sidebar-item">
        <FaEdit />
      </div>
      <div className="sidebar-item" style={{ marginTop: 'auto' }}>
        <FaCog />
      </div>
    </aside>
  )
}

export default Sidebar
