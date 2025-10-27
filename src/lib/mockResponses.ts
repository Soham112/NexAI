export async function getMockResponse(prompt: string): Promise<string> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000))
  
  const responses = {
    'courses': `**Available Courses**

Here are some courses that might interest you:

• **AI & Machine Learning Fundamentals**
  Duration: 8 weeks | Level: Beginner
  Covers: Python, TensorFlow, Neural Networks

• **Cloud Computing with AWS**
  Duration: 12 weeks | Level: Intermediate  
  Covers: EC2, S3, Lambda, API Gateway

• **Data Science & Analytics**
  Duration: 10 weeks | Level: Intermediate
  Covers: Statistics, Visualization, Big Data

• **Web Development Full Stack**
  Duration: 16 weeks | Level: Beginner to Advanced
  Covers: React, Node.js, Databases

Would you like more details about any specific course?`,

    'recent jobs': `**Recent Job Opportunities**

Here are some recent job postings that match your profile:

• **Senior AI Engineer** - TechCorp
  Location: Remote | Salary: $120k - $150k
  Requirements: 5+ years ML experience

• **Cloud Solutions Architect** - CloudTech
  Location: San Francisco, CA | Salary: $140k - $180k
  Requirements: AWS certification, 7+ years experience

• **Full Stack Developer** - StartupXYZ
  Location: Austin, TX | Salary: $90k - $120k
  Requirements: React, Node.js, 3+ years experience

• **Data Scientist** - DataCorp
  Location: New York, NY | Salary: $110k - $140k
  Requirements: Python, SQL, Statistics

Would you like me to help you prepare for any of these positions?`,

    'terms': `**Technical Terms & Concepts**

Here are some important technical terms explained:

• **API Gateway**: A service that acts as a single entry point for multiple backend services, handling routing, authentication, and rate limiting.

• **Microservices**: An architectural approach where applications are built as a collection of loosely coupled, independently deployable services.

• **Containerization**: The process of packaging applications and their dependencies into lightweight, portable containers using tools like Docker.

• **CI/CD**: Continuous Integration/Continuous Deployment - automated processes for building, testing, and deploying code changes.

• **Load Balancing**: Distributing incoming network traffic across multiple servers to ensure high availability and performance.

Would you like me to explain any of these concepts in more detail?`,

    'project planning': `**Project Planning & Management**

Here's how I can help with your project planning:

• **Project Scope Definition**: Clearly define objectives, deliverables, and constraints
• **Timeline Creation**: Break down tasks and create realistic schedules
• **Resource Allocation**: Identify required team members, tools, and budget
• **Risk Assessment**: Identify potential challenges and mitigation strategies
• **Progress Tracking**: Set up monitoring and reporting systems

**Popular Project Management Tools:**
- Jira for issue tracking
- Trello for task management
- Asana for team collaboration
- Microsoft Project for complex planning

What type of project are you planning? I can provide more specific guidance.`,

    'learning resources': `**Learning Resources & Tutorials**

Here are some excellent learning resources:

• **Online Platforms:**
  - Coursera: University-level courses
  - Udemy: Practical, project-based learning
  - edX: Free courses from top universities
  - Pluralsight: Technology-focused training

• **Documentation & Guides:**
  - Official documentation for frameworks
  - GitHub repositories with examples
  - Stack Overflow for problem-solving
  - Medium articles for insights

• **Hands-on Practice:**
  - LeetCode for coding challenges
  - HackerRank for skill assessment
  - Kaggle for data science projects
  - CodePen for frontend experimentation

What specific skill or technology would you like to learn more about?`
  }
  
  // Find matching response
  const lowerPrompt = prompt.toLowerCase()
  for (const [keyword, response] of Object.entries(responses)) {
    if (lowerPrompt.includes(keyword)) {
      return response
    }
  }
  
  // Generic response
  const genericResponses = [
    `Thank you for your question: "${prompt}". I'm NexAI, your intelligent assistant. I can help you with courses, job opportunities, technical concepts, project planning, and learning resources. What specific area would you like to explore?`,
    `I understand you're asking about "${prompt}". NexAI is here to assist you with various topics including professional development, technical learning, and career guidance. How can I help you further?`,
    `That's an interesting query about "${prompt}". NexAI specializes in providing comprehensive assistance across multiple domains. What would you like to know more about?`
  ]
  
  return genericResponses[Math.floor(Math.random() * genericResponses.length)]
}
