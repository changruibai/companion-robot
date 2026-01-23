import ThemeToggle from './ThemeToggle'

const Header = () => {
  return (
    <header className="glass-effect sticky top-0 z-40 border-b border-base-300 bg-base-100/95 backdrop-blur">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary to-secondary rounded-xl flex items-center justify-center shadow-lg">
              <svg className="w-6 h-6 text-primary-content" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-bold gradient-text">VikingDB 智能记忆助手</h1>
              <p className="text-sm text-base-content/70">基于 AI 的智能记忆查询系统</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <div className="badge badge-primary badge-lg">在线</div>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header
