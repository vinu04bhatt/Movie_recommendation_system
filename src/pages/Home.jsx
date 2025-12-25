import { useNavigate } from 'react-router-dom'

function Home() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50 flex items-center justify-center p-6">
      <div className="max-w-2xl text-center space-y-8">
        <div className="space-y-4">
          <h1 className="text-6xl md:text-7xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-600 via-pink-600 to-blue-600">
            CineMatch
          </h1>
          <div className="h-1 w-32 mx-auto bg-gradient-to-r from-purple-400 to-pink-400 rounded-full"></div>
        </div>

        <p className="text-xl md:text-2xl text-gray-700 leading-relaxed font-light">
          Your mood deserves the perfect story. Discover films and series tailored to how you feel, 
          who you're with, and what moves you.
        </p>

        <div className="flex flex-wrap justify-center gap-4 text-sm text-gray-600">
          <span className="px-4 py-2 bg-white/60 backdrop-blur-sm rounded-full border border-purple-200">
            🎭 Mood-Based
          </span>
          <span className="px-4 py-2 bg-white/60 backdrop-blur-sm rounded-full border border-pink-200">
            👥 Context-Aware
          </span>
          <span className="px-4 py-2 bg-white/60 backdrop-blur-sm rounded-full border border-blue-200">
            ✨ Personalized
          </span>
        </div>

        <button
          onClick={() => navigate('/recommend')}
          className="mt-8 px-12 py-4 bg-gradient-to-r from-purple-600 to-pink-600 text-white text-lg font-semibold rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-300"
        >
          Get Started
        </button>
      </div>
    </div>
  )
}

export default Home