import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Recommend() {
  const navigate = useNavigate()

  // -----------------------------
  // State
  // -----------------------------
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [results, setResults] = useState(null)

  const [formData, setFormData] = useState({
    favorite_movie: '',
    favorite_genres: '',
    current_mood: 'happy',
    watching_context: 'alone',
    popularity_bias: 'mix'
  })

  // -----------------------------
  // Handlers
  // -----------------------------
  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const payload = {
        ...formData,
        favorite_genres: formData.favorite_genres
          .split(',')
          .map(g => g.trim())
          .filter(Boolean)
      }

      const response = await fetch('http://localhost:8000/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Server error (${response.status}): ${errorText}`)
      }

      const data = await response.json()

      if (!data.movies?.length && !data.tv?.length) {
        setError(
          'No recommendations available right now. The content source may be temporarily unavailable.'
        )
      } else {
        setResults(data)
      }
    } catch (err) {
      if (err.message.includes('Failed to fetch')) {
        setError(
          'Cannot connect to server. Please ensure the backend is running on http://localhost:8000'
        )
      } else if (err.message.includes('Server error')) {
        setError('The server encountered an issue. Please try again shortly.')
      } else {
        setError(`Unexpected error: ${err.message}`)
      }
    } finally {
      setLoading(false)
    }
  }

  // -----------------------------
  // UI
  // -----------------------------
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 p-6">
      <div className="max-w-7xl mx-auto">

        {/* Back Button */}
        <button
          onClick={() => navigate('/')}
          className="mb-6 text-purple-600 hover:text-purple-800 flex items-center gap-2 transition-colors"
        >
          ← Back to Home
        </button>

        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-600 to-pink-600 mb-2">
            Find Your Perfect Watch
          </h1>
          <p className="text-gray-600">
            Tell us about your vibe, and we’ll curate the perfect list
          </p>
        </div>

        {/* Form */}
        <div className="bg-white/70 backdrop-blur-lg rounded-3xl shadow-xl p-8 mb-8">
          <form onSubmit={handleSubmit} className="space-y-6">

            <div className="grid md:grid-cols-2 gap-6">
              <Input
                label="Favorite Movie"
                name="favorite_movie"
                value={formData.favorite_movie}
                onChange={handleChange}
                placeholder="e.g., Inception"
              />

              <Input
                label="Favorite Genres"
                name="favorite_genres"
                value={formData.favorite_genres}
                onChange={handleChange}
                placeholder="e.g., Sci-Fi, Thriller"
              />

              <Select
                label="Current Mood"
                name="current_mood"
                value={formData.current_mood}
                onChange={handleChange}
                options={[
                  ['happy', '😊 Happy'],
                  ['excited', '🎉 Excited'],
                  ['romantic', '💕 Romantic'],
                  ['sad', '😢 Sad'],
                  ['scared', '😱 Scared']
                ]}
              />

              <Select
                label="Watching With"
                name="watching_context"
                value={formData.watching_context}
                onChange={handleChange}
                options={[
                  ['alone', '🙋 Alone'],
                  ['friends', '👥 Friends'],
                  ['partner', '💑 Partner'],
                  ['family', '👨‍👩‍👧‍👦 Family']
                ]}
              />

              <Select
                label="Popularity Preference"
                name="popularity_bias"
                value={formData.popularity_bias}
                onChange={handleChange}
                options={[
                  ['popular', '⭐ Popular'],
                  ['underrated', '💎 Underrated'],
                  ['mix', '🎲 Mix']
                ]}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl hover:scale-[1.02] transition-all disabled:opacity-50"
            >
              {loading ? 'Finding perfect matches...' : 'Show Recommendations'}
            </button>
          </form>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-xl mb-8">
            ⚠️ {error}
          </div>
        )}

        {/* Loader */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-purple-200 border-t-purple-600"></div>
            <p className="mt-4 text-gray-600">Curating your personalized list...</p>
          </div>
        )}

        {/* Results */}
        {results && !loading && (
          <div className="grid md:grid-cols-2 gap-8">
            <ResultsColumn title="🎬 Movies" items={results.movies} />
            <ResultsColumn title="📺 TV Series" items={results.tv} />
          </div>
        )}
      </div>
    </div>
  )
}

/* -----------------------------
   Reusable Components
------------------------------ */

function Input({ label, ...props }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label}
      </label>
      <input
        {...props}
        className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-purple-500 outline-none"
      />
    </div>
  )
}

function Select({ label, options, ...props }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label}
      </label>
      <select
        {...props}
        className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-purple-500 outline-none"
      >
        {options.map(([value, text]) => (
          <option key={value} value={value}>{text}</option>
        ))}
      </select>
    </div>
  )
}

function ResultsColumn({ title, items }) {
  return (
    <div className="bg-white/70 backdrop-blur-lg rounded-3xl shadow-xl p-8">
      <h2 className="text-2xl font-bold mb-6">{title}</h2>

      {!items?.length ? (
        <p className="text-gray-500 text-center py-8">
          No results found matching your criteria
        </p>
      ) : (
        <div className="space-y-4">
          {items.map((item, idx) => (
            <div
              key={idx}
              className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl border hover:shadow-md transition-all"
            >
              <h3 className="font-semibold text-lg">{item.title}</h3>
              <div className="flex gap-4 mt-2 text-sm text-gray-600">
                <span>📅 {item.year}</span>
                <span>⭐ {item.popularity?.toFixed(1)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
