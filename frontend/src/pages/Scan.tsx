import { useCallback, useState } from "react";
import { Upload, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { scan, ScanSession, ScanResult, CardSearchResult } from "@/lib/api";
import { useScanSession } from "@/hooks/useScanSession";
import { cn } from "@/lib/utils";

export default function Scan() {
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);

  const session = useScanSession(sessionId);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setError("");
    setUploading(true);

    try {
      const arr = Array.from(files);
      const isVideo = arr[0].type.startsWith("video/");
      const result = isVideo
        ? await scan.uploadVideo(arr[0])
        : await scan.uploadImages(arr);
      setSessionId(result.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }, []);

  function reset() {
    setSessionId(null);
    setError("");
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Scan Cards</h2>
        <p className="mt-1 text-gray-400">
          Upload one or more card photos, or a video of flipping through a binder.
        </p>
      </div>

      {!sessionId && (
        <label
          className={cn(
            "flex cursor-pointer flex-col items-center gap-4 rounded-xl border-2 border-dashed p-12 text-center transition-colors",
            dragOver
              ? "border-blue-500 bg-blue-500/10"
              : "border-gray-700 bg-gray-900 hover:border-gray-600"
          )}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
        >
          <input
            type="file"
            className="hidden"
            multiple
            accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/webm"
            onChange={(e) => handleFiles(e.target.files)}
          />
          {uploading ? (
            <Loader2 size={32} className="animate-spin text-blue-400" />
          ) : (
            <Upload size={32} className="text-gray-500" />
          )}
          <div>
            <p className="font-medium">{uploading ? "Uploading…" : "Drop files here or click to browse"}</p>
            <p className="mt-1 text-sm text-gray-500">
              JPEG, PNG, WebP images or MP4/MOV video
            </p>
          </div>
        </label>
      )}

      {error && (
        <p className="rounded-lg bg-red-900/30 px-3 py-2 text-sm text-red-400">{error}</p>
      )}

      {session && <SessionResults session={session} onReset={reset} />}
    </div>
  );
}

function SessionResults({ session, onReset }: { session: ScanSession; onReset: () => void }) {
  const isProcessing = session.status === "pending" || session.status === "processing";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isProcessing && <Loader2 size={16} className="animate-spin text-blue-400" />}
          {session.status === "complete" && <CheckCircle size={16} className="text-green-400" />}
          {session.status === "failed" && <XCircle size={16} className="text-red-400" />}
          <span className="text-sm font-medium capitalize">{session.status}</span>
        </div>
        {!isProcessing && (
          <button onClick={onReset} className="text-sm text-blue-400 hover:underline">
            Scan more
          </button>
        )}
      </div>

      {session.results.length === 0 && isProcessing && (
        <p className="text-sm text-gray-500">Analyzing cards…</p>
      )}

      {session.results.map((result) => (
        <ResultCard key={result.id} result={result} />
      ))}
    </div>
  );
}

function ResultCard({ result }: { result: ScanResult }) {
  const card = result.pokemon_card;
  const hasLowConfidence = !card && result.candidates.length > 0;

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
      {card ? (
        <div className="flex items-start gap-4">
          {card.image_small && (
            <img src={card.image_small} alt={card.name} className="h-24 w-auto rounded" />
          )}
          <div>
            <p className="font-semibold">{card.name}</p>
            <p className="text-sm text-gray-400">{card.set_name} · #{card.collector_number}</p>
            {card.rarity && <p className="text-xs text-gray-500 mt-1">{card.rarity}</p>}
            {result.confidence != null && (
              <p className="text-xs text-gray-600 mt-1">
                Confidence: {Math.round(result.confidence * 100)}%
              </p>
            )}
          </div>
        </div>
      ) : hasLowConfidence ? (
        <CandidateSelect result={result} />
      ) : (
        <div className="text-sm text-gray-500">
          Could not identify card
          {result.raw_ocr_name && (
            <span className="ml-1 text-gray-600">(read: "{result.raw_ocr_name}")</span>
          )}
        </div>
      )}
    </div>
  );
}

function CandidateSelect({ result }: { result: ScanResult }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);

  async function confirm(apiId: string) {
    setSelected(apiId);
    await scan.confirm(result.id, apiId);
    setConfirmed(true);
  }

  if (confirmed) {
    return <p className="text-sm text-green-400">Card confirmed.</p>;
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-yellow-400">Low confidence — which card is this?</p>
      {result.raw_ocr_name && (
        <p className="text-xs text-gray-500">OCR read: "{result.raw_ocr_name}"</p>
      )}
      <div className="space-y-1">
        {result.candidates.map((c: CardSearchResult) => (
          <button
            key={c.api_id}
            onClick={() => confirm(c.api_id)}
            className={cn(
              "flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left text-sm transition-colors",
              selected === c.api_id
                ? "border-blue-500 bg-blue-500/10"
                : "border-gray-700 bg-gray-800 hover:border-gray-600"
            )}
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
