import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/hooks/useAuth";
import Auth from "@/pages/Auth";
import Dashboard from "@/pages/Dashboard";
import Scan from "@/pages/Scan";
import Collection from "@/pages/Collection";
import Layout from "@/components/Layout";
import "./index.css";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth();
  if (loading) return <div className="flex h-screen items-center justify-center text-gray-400">Loading…</div>;
  return token ? <>{children}</> : <Navigate to="/auth" replace />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/auth" element={<Auth />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="scan" element={<Scan />} />
            <Route path="collection" element={<Collection />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>
);
