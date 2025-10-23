'use client'

import React from 'react'
import { FaBars, FaGem, FaUser } from 'react-icons/fa'

const TopNavigation: React.FC = () => {
  return (
    <nav className="top-nav">
      <div className="nav-left">
        <button className="hamburger-menu">
          <FaBars />
        </button>
        <div className="logo">
          <h1>NextAI</h1>
        </div>
      </div>
      <div className="nav-right">
        <button className="upgrade-btn">
          <FaGem />
          Upgrade
        </button>
        <div className="user-avatar">C</div>
      </div>
    </nav>
  )
}

export default TopNavigation
