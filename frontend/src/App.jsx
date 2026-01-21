import { useState } from 'react'
import ChatInterface from './components/ChatInterface'
import Header from './components/Header'

function App() {
  return (
    <div className="min-h-screen">
      <Header />
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <ChatInterface />
      </div>
    </div>
  )
}

export default App
