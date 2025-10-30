import { useState } from 'react';
// --- Import shadcn/ui components ---
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

// --- Import icons ---
import { Brain, Clapperboard, Search } from 'lucide-react';

export default function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searched, setSearched] = useState(false);

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

  const renderResults = () => {
    if (loading) {
      return <div className="text-center text-slate-400">Loading...</div>;
    }
    if (error) {
      return <div className="text-center text-red-500">Error: {error}</div>;
    }
    
    // Empty state before any search
    if (!searched) {
      return (
        <div className="text-center text-slate-500 animate-in fade-in-0 duration-500">
          <Clapperboard className="w-16 h-16 mx-auto mb-4" />
          <h2 className="text-2xl font-semibold">Ready to find your next movie?</h2>
          <p>Type a plot, theme, or title above to get started.</p>
        </div>
      );
    }
    
    // Empty state after a search returns nothing
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

  // We are now using the default dark theme "slate" from shadcn
  return (
    <div className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-6xl mx-auto">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold mb-4">
            Hybrid Movie Recommender
          </h1>
          <p className="text-xl text-muted-foreground">
            Find movies by plot (Vector Search) + discover related films (Graph Search).
          </p>
        </header>

        {/* --- Use shadcn/ui components --- */}
        <form onSubmit={handleSearch} className="flex gap-4 mb-12">
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

        <main>
          {renderResults()}
        </main>
      </div>
    </div>
  );
}

// --- Movie Card Component (now with images and links) ---
function MovieCard({ movie, index }) {
  const isVector = movie.source === 'vector';
  
  // Create a placeholder URL for movies without a poster
  const placeholderUrl = `https://placehold.co/500x750/1f2937/9ca3af?text=${movie.title.replace(/\s/g, '+')}`;

  const CardContentWrapper = ({ children }) => (
    // If we have an IMDB link, make the whole card a clickable link
    // that opens in a new tab.
    movie.imdb_url ? (
      <a
        href={movie.imdb_url}
        target="_blank"
        rel="noopener noreferrer"
        className="block"
      >
        {children}
      </a>
    ) : (
      // If no link, just render the content
      <div className="block">{children}</div>
    )
  );

  return (
    <Card 
      className="animate-in fade-in-0 duration-500 overflow-hidden" // Added overflow-hidden
      style={{ animationDelay: `${index * 50}ms`, animationFillMode: 'backwards' }}
    >
      <CardContentWrapper>
        {/* --- IMAGE SECTION --- */}
        <div className="aspect-[2/3] w-full overflow-hidden">
          <img
            src={movie.poster_url || placeholderUrl}
            // Fallback to placeholder if the image link is broken
            onError={(e) => { e.currentTarget.src = placeholderUrl }}
            alt={`Poster for ${movie.title}`}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        </div>

        {/* --- TEXT CONTENT SECTION --- */}
        <div className="p-6">
          <CardTitle className="text-2xl mb-2">{movie.title}</CardTitle>
          <CardDescription className="mb-4">
            {movie.genre || 'N/A'} • {movie.year || 'N/A'}
          </CardDescription>
          
          <div 
            className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
              isVector 
                ? 'bg-blue-900 text-blue-100' 
                : 'bg-teal-900 text-teal-100'
            }`}
          >
            {isVector ? (
              <Brain className="w-4 h-4 mr-2" />
            ) : (
              <Clapperboard className="w-4 h-4 mr-2" />
            )}
            {isVector ? `Semantic Match (Score: ${movie.score.toFixed(3)})` : 'Graph Recommendation'}
          </div>
        </div>
      </CardContentWrapper>
    </Card>
  );
}