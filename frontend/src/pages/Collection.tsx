import { useEffect, useState } from "react";
import { Plus, Trash2, Search } from "lucide-react";
import {
  collection,
  Collection,
  CollectionCard,
  cards,
  CardSearchResult,
} from "@/lib/api";

export default function CollectionPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [cardEntries, setCardEntries] = useState<CollectionCard[]>([]);
  const [showSearch, setShowSearch] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    collection.list().then((data) => {
      setCollections(data);
      if (data.length > 0 && !activeId) setActiveId(data[0].id);
    });
  }, []);

  useEffect(() => {
    if (!activeId) return;
    collection.listCards(activeId).then(setCardEntries);
  }, [activeId]);

  async function createCollection() {
    if (!newName.trim()) return;
    const c = await collection.create(newName.trim());
    setCollections((prev) => [...prev, c]);
    setActiveId(c.id);
    setNewName("");
    setCreating(false);
  }

  async function removeCard(entryId: number) {
    await collection.removeCard(entryId);
    setCardEntries((prev) => prev.filter((e) => e.id !== entryId));
  }

  async function addCard(apiId: string) {
    if (!activeId) return;
    const entry = await collection.addCard(activeId, apiId);
    setCardEntries((prev) => [...prev, entry]);
    setShowSearch(false);
  }

  return (
    <div className="flex gap-6">
      {/* Collection sidebar */}
      <div className="w-48 shrink-0 space-y-1">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
            Collections
          </span>
          <button
            onClick={() => setCreating(true)}
            className="text-gray-400 hover:text-white"
            title="New collection"
          >
            <Plus size={14} />
          </button>
        </div>

        {creating && (
          <div className="flex gap-1">
            <input
              autoFocus
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && createCollection()}
              placeholder="Name…"
              className="flex-1 rounded border border-gray-700 bg-gray-800 px-2 py-1 text-xs focus:outline-none"
            />
            <button onClick={createCollection} className="text-xs text-blue-400">
              Save
            </button>
          </div>
        )}

        {collections.map((c) => (
          <button
            key={c.id}
            onClick={() => setActiveId(c.id)}
            className={`w-full truncate rounded-lg px-3 py-2 text-left text-sm transition-colors ${
              activeId === c.id
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            }`}
          >
            {c.name}
          </button>
        ))}
      </div>

      {/* Card grid */}
      <div className="flex-1 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">
            {collections.find((c) => c.id === activeId)?.name ?? "Collection"}
          </h2>
          <button
            onClick={() => setShowSearch((v) => !v)}
            className="flex items-center gap-1 rounded-lg bg-gray-800 px-3 py-1.5 text-sm hover:bg-gray-700 transition-colors"
          >
            <Plus size={14} /> Add card
          </button>
        </div>

        {showSearch && <CardSearch onSelect={addCard} />}

        {cardEntries.length === 0 && !showSearch && (
          <p className="py-10 text-center text-sm text-gray-500">
            No cards yet — scan some or add them manually.
          </p>
        )}

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {cardEntries.map((entry) => (
            <div
              key={entry.id}
              className="group relative rounded-xl border border-gray-800 bg-gray-900 p-2"
            >
              {entry.pokemon_card.image_small ? (
                <img
                  src={entry.pokemon_card.image_small}
                  alt={entry.pokemon_card.name}
                  className="w-full rounded"
                />
              ) : (
                <div className="flex h-32 items-center justify-center rounded bg-gray-800 text-xs text-gray-500">
                  No image
                </div>
              )}
              <div className="mt-2">
                <p className="truncate text-xs font-medium">{entry.pokemon_card.name}</p>
                <p className="truncate text-xs text-gray-500">
                  {entry.pokemon_card.set_name}
                </p>
                {entry.quantity > 1 && (
                  <span className="mt-1 inline-block rounded bg-blue-600/20 px-1.5 py-0.5 text-xs text-blue-400">
                    ×{entry.quantity}
                  </span>
                )}
              </div>
              <button
                onClick={() => removeCard(entry.id)}
                className="absolute right-2 top-2 hidden rounded bg-red-900/70 p-1 text-red-400 group-hover:block"
                title="Remove"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CardSearch({ onSelect }: { onSelect: (apiId: string) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CardSearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (query.length < 2) { setResults([]); return; }
    const t = setTimeout(async () => {
      setLoading(true);
      try { setResults(await cards.search(query)); }
      finally { setLoading(false); }
    }, 400);
    return () => clearTimeout(t);
  }, [query]);

  return (
    <div className="rounded-xl border border-gray-700 bg-gray-900 p-4 space-y-3">
      <div className="flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-800 px-3 py-2">
        <Search size={14} className="text-gray-500" />
        <input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search card name…"
          className="flex-1 bg-transparent text-sm focus:outline-none"
        />
      </div>
      {loading && <p className="text-xs text-gray-500">Searching…</p>}
      <div className="space-y-1 max-h-60 overflow-y-auto">
        {results.map((c) => (
          <button
            key={c.api_id}
            onClick={() => onSelect(c.api_id)}
            className="flex w-full items-center gap-3 rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-left text-sm hover:border-gray-600 transition-colors"
          >
            {c.image_small && (
              <img src={c.image_small} alt={c.name} className="h-10 w-auto rounded" />
            )}
            <div>
              <p className="font-medium">{c.name}</p>
              <p className="text-xs text-gray-400">
                {c.set_name} · #{c.collector_number}
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
