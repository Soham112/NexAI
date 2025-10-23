'use client'

import React from 'react'
import { FaGraduationCap, FaBriefcase, FaBook, FaProjectDiagram, FaLightbulb } from 'react-icons/fa'

interface WelcomeSectionProps {
  onStartChat: () => void
}

const WelcomeSection: React.FC<WelcomeSectionProps> = ({ onStartChat }) => {
  const actionButtons = [
    {
      icon: FaGraduationCap,
      text: 'Courses',
      prompt: 'Show me available courses'
    },
    {
      icon: FaBriefcase,
      text: 'Recent Jobs',
      prompt: 'Show recent job opportunities'
    },
    {
      icon: FaBook,
      text: 'Terms & Concepts',
      prompt: 'Explain technical terms and concepts'
    },
    {
      icon: FaProjectDiagram,
      text: 'Project Planning',
      prompt: 'Help with project planning and management'
    },
    {
      icon: FaLightbulb,
      text: 'Learning Resources',
      prompt: 'Provide learning resources and tutorials'
    }
  ]

  return (
    <>
      <div className="welcome-section">
        <h1 className="welcome-title">Hello Comet!</h1>
      </div>

      <div className="action-buttons">
        {actionButtons.map((button, index) => {
          const IconComponent = button.icon
          return (
            <button
              key={index}
              className="action-btn"
              onClick={() => onStartChat()}
            >
              <IconComponent />
              {button.text}
            </button>
          )
        })}
      </div>
    </>
  )
}

export default WelcomeSection
