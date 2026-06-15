import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ScanLine, BookOpen, TrendingUp } from "lucide-react";
import { collection, Collection } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

export default function Dashboard() {
  const { user } = useAuth();
  const [collections, setCollections] = useState<Collection[]>([]);

  useEffect(() => {
    collection.list().then(setCollections).catch(console.error);
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold">Welcome back, {user?.username}</h2>
        <p className="mt-1 text-gray-400">Here's your collection at a glance.</p>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Link
          to="/scan"
          className="flex items-center gap-4 rounded-xl border border-gray-800 bg-gray-900 p-5 hover:border-blue-700 transition-colors"
        >
          <div className="rounded-lg bg-blue-600/20 p-3">
            <ScanLine size={20} className="text-blue-400" />
          </div>
          <div>
            <p className="font-medium">Scan Cards</p>
            <p className="text-sm text-gray-400">Upload photos or a video</p>
          </div>
        </Link>

        <Link
          to="/collection"
          className="flex items-center gap-4 rounded-xl border border-gray-800 bg-gray-900 p-5 hover:border-blue-700 transition-colors"
        >
          <div className="rounded-lg bg-purple-600/20 p-3">
            <BookOpen size={20} className="text-purple-400" />
          </div>
          <div>
            <p className="font-medium">Browse Collection</p>
            <p className="text-sm text-gray-400">
              {collections.length} collection{collections.length !== 1 ? "s" : ""}
            </p>
          </div>
        </Link>
      </div>

      {/* Collections list */}
      {collections.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-medium text-gray-400 uppercase tracking-wider">
            Your Collections
          </h3>
          <div className="space-y-2">
            {collections.map((c) => (
              <Link
                key={c.id}
                to={`/collection?id=${c.id}`}
                className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-900 px-4 py-3 hover:border-gray-700 transition-colors"
              >
                <span className="font-medium">{c.name}</span>
                <span className="text-sm text-gray-500">
                  {new Date(c.created_at).toLocaleDateString()}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {collections.length === 0 && (
        <div className="rounded-xl border border-dashed border-gray-700 p-10 text-center">
          <TrendingUp size={32} className="mx-auto mb-3 text-gray-600" />
          <p className="font-medium">No collections yet</p>
          <p className="mt-1 text-sm text-gray-500">
            Start by scanning some cards to build your inventory.
          </p>
          <Link
            to="/scan"
            className="mt-4 inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 transition-colors"
          >
            Scan your first card
          </Link>
        </div>
      )}
    </div>
  );
}
