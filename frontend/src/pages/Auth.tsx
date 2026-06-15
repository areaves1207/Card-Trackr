import { useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { auth } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

export default function Auth() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res =
        mode === "login"
          ? await auth.login(email, password)
          : await auth.register(email, username, password);
      login(res.access_token);
      navigate("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-screen items-center justify-center">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold">CardTrackr</h1>
          <p className="mt-1 text-sm text-gray-400">Pokemon card collection tracker</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-gray-800 bg-gray-900 p-6">
          <h2 className="text-lg font-semibold">{mode === "login" ? "Sign in" : "Create account"}</h2>

          {error && (
            <p className="rounded-lg bg-red-900/30 px-3 py-2 text-sm text-red-400">{error}</p>
          )}

          <label className="block space-y-1">
            <span className="text-xs text-gray-400">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </label>

          {mode === "register" && (
            <label className="block space-y-1">
              <span className="text-xs text-gray-400">Username</span>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </label>
          )}

          <label className="block space-y-1">
            <span className="text-xs text-gray-400">Password</span>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </label>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition-colors"
          >
            {loading ? "…" : mode === "login" ? "Sign in" : "Create account"}
          </button>

          <p className="text-center text-xs text-gray-500">
            {mode === "login" ? "No account?" : "Already have one?"}{" "}
            <button
              type="button"
              onClick={() => setMode(mode === "login" ? "register" : "login")}
              className="text-blue-400 hover:underline"
            >
              {mode === "login" ? "Register" : "Sign in"}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}
