import { useState, useEffect } from 'react';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Brain, Clapperboard, Search, Zap } from 'lucide-react';

// --- This component is now for REAL data ---
function InitialSuggestions({ movies, loading }) {
  if (loading) {
    // Show a clean loading state
    return <div className="text-center text-slate-400">Loading trending movies...</div>;
  }
  
  return (
    <div className="animate-in fade-in duration-500">
      <h2 className="text-2xl font-semibold text-center mb-6 text-slate-300">
        Trending Today
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {movies.map((movie, index) => (
          <MovieCard key={index} movie={movie} index={index} />
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);
  const [initialMovies, setInitialMovies] = useState([]);
  const [initialLoading, setInitialLoading] = useState(true);

  useEffect(() => {
    const fetchTrending = async () => {
      try {
        const response = await fetch("http://127.0.0.1:8000/trending");
        if (!response.ok) {
          throw new Error("Could not fetch trending movies.");
        }
        const data = await response.json();
        setInitialMovies(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setInitialLoading(false);
      }
    };

    fetchTrending();
  }, []);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResults([]);
    setSearched(true); 

    const params = new URLSearchParams({
      query: query,
      vector_limit: 4,
      graph_limit: 4,
    });
    const url = `http://127.0.0.1:8000/recommend?${params.toString()}`;

    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Error: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch recommendations.');
    } finally {
      setLoading(false);
    }
  };

  const renderSearchResults = () => {
    if (loading) {
      return <div className="text-center text-slate-400">Loading search results...</div>;
    }
    if (error) {
      return <div className="text-center text-red-500">Error: {error}</div>;
    }
    if (searched && results.length === 0) {
      return <div className="text-center text-slate-400">No movies found for that query.</div>;
    }
    
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {results.map((movie, index) => (
          <MovieCard key={index} movie={movie} index={index} />
        ))}
      </div>
    );
  };

  return (
    // This is the main full-height container
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      
      {/* --- THIS IS THE UPDATED HEADER --- */}
      {/* I changed "bg-background" to "bg-secondary" to give it a different tone */}
      <header className="sticky top-0 z-50 w-full bg-secondary border-b border-border/50">
        <div className="max-w-6xl mx-auto px-8 pt-8 pb-6">
          <div className="text-center mb-8">
            <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
              Hybrid Movie Recommender
            </h1>
            <p className="text-xl text-muted-foreground">
              Find movies by plot (Vector Search) + discover related films (Graph Search).
            </p>
          </div>

          <form onSubmit={handleSearch} className="flex gap-4">
            <Input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., 'a fun sci-fi movie about aliens visiting earth'"
              className="flex-grow text-lg p-6"
              disabled={loading}
            />
            <Button type="submit" size="lg" className="text-lg px-8" disabled={loading}>
              {loading ? 'Searching...' : <Search className="w-5 h-5 mr-2" />}
              {loading ? '' : 'Search'}
            </Button>
          </form>
        </div>
      </header>

      {/* --- This is the scrollable content area --- */}
      <main className="flex-grow overflow-y-auto p-8">
        <div className="max-w-6xl mx-auto">
          {searched ? (
            renderSearchResults() 
          ) : (
            <InitialSuggestions movies={initialMovies} loading={initialLoading} />
          )}
        </div>
      </main>

    </div>
  );
}

// --- Movie Card Component (No changes needed) ---
function MovieCard({ movie, index }) {
  const isVector = movie.source === 'vector';
  const isGraph = movie.source === 'graph';
  const isTrending = movie.source === 'trending';

  const placeholderText = movie.title ? movie.title.replace(/\s/g, '+') : 'Loading';
  let placeholderUrl = `https://placehold.co/500x750/1e293b/94a3b8?text=${placeholderText}`; // Default (Vector)
  
  if (isGraph) {
    placeholderUrl = `https://placehold.co/500x750/103a3a/a5f3fc?text=${placeholderText}`; // Amber/Teal
  } else if (isTrending) {
    placeholderUrl = `https://placehold.co/500x750/363328/fcd34d?text=${placeholderText}`; // Gold/Yellow
  }
  
  const CardContentWrapper = ({ children }) => (
    movie.imdb_url ? (
      <a
        href={movie.imdb_url}
        target="_blank"
        rel="noopener noreferrer"
        className="block group"
      >
        {children}
      </a>
    ) : (
      <div className="block group">{children}</div>
    )
  );

  return (
    <Card 
      className="animate-in fade-in duration-500 overflow-hidden transition-all ease-out hover:scale-[1.02] hover:shadow-xl hover:shadow-black/20"
      style={{ animationDelay: `${index * 50}ms`, animationFillMode: 'backwards' }}
    >
      <CardContentWrapper>
        <div className="aspect-[2/3] w-full overflow-hidden">
          <img
            src={movie.poster_url || placeholderUrl}
            onError={(e) => { e.currentTarget.src = placeholderUrl }}
            alt={`Poster for ${movie.title}`}
            className="w-full h-full object-cover transition-transform duration-300 ease-out group-hover:scale-105"
          />
        </div>

        <div className="p-6">
          <CardTitle className="text-2xl mb-2">{movie.title}</CardTitle>
          <CardDescription className="mb-4">
            {movie.genre || 'N/A'} • {movie.year || 'N/A'}
          </CardDescription>
          
          <div 
            className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${
              isVector 
                ? 'bg-primary/10 text-primary/90 border-primary/20' 
                : isGraph
                  ? 'bg-accent-amber-soft-bg/20 text-accent-amber-soft-fg border-accent-amber/20'
                  : 'bg-yellow-900/50 text-yellow-300 border-yellow-700/50' // Trending tag
            }`}
          >
            {isVector && <Brain className="w-4 h-4 mr-2" />}
            {isGraph && <Clapperboard className="w-4 h-4 mr-2" />}
            {isTrending && <Zap className="w-4 h-4 mr-2" />}
            
            {isVector && `Semantic Match (Score: ${movie.score.toFixed(3)})`}
            {isGraph && 'Graph Recommendation'}
            {isTrending && `Trending (Score: ${movie.score.toFixed(1)})`}
          </div>
        </div>
      </CardContentWrapper>
    </Card>
  );
}