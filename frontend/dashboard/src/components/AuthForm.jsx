// frontend/dashboard/src/components/AuthForm.jsx

import React, { useState, useEffect } from "react";
import supabase from "../supabaseClient";

// Official Google button assets in public/dashboard
const GOOGLE_BUTTON_LIGHT = "/dashboard/web_light_sq_ctn.svg";
const GOOGLE_BUTTON_DARK = "/dashboard/web_dark_sq_ctn.svg";

function usePrefersDark() {
  const [isDark, setIsDark] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e) => setIsDark(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  return isDark;
}

export default function AuthForm({ showGoogle = true }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const isDarkMode = usePrefersDark();

  const handleGoogleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: window.location.origin + "/dashboard" },
      });
      if (error) throw error;
    } catch (err) {
      setError(err.message || "Google login failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");

    try {
      if (isSignUp) {
        const { error: signUpErr } = await supabase.auth.signUp({ email, password });
        if (signUpErr) throw signUpErr;
        setMessage("Sign up successful! Please check your email to confirm.");
      } else {
        const { error: signInErr } = await supabase.auth.signInWithPassword({ email, password });
        if (signInErr) throw signInErr;
        setMessage("Login successful! Redirecting...");
        setTimeout(() => (window.location.href = "/dashboard"), 1200);
      }
    } catch (err) {
      setError(err.message || "Authentication error. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="auth-form"
      style={{
        background: "var(--card-bg)",
        boxShadow: "var(--card-shadow)",
        borderRadius: 14,
        padding: "2rem",
        maxWidth: 380,
        width: "100%",
        margin: "2rem auto",
      }}
    >
      <h2 style={{ textAlign: "center", marginBottom: 18 }}>
        {isSignUp ? "Sign Up" : "Log In"}
      </h2>

      {showGoogle && (
        <div style={{ marginBottom: 18 }}>
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={loading}
            style={{
              border: "none",
              background: "none",
              padding: 0,
              width: "100%",
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            <img
              src={isDarkMode ? GOOGLE_BUTTON_DARK : GOOGLE_BUTTON_LIGHT}
              alt="Continue with Google"
              style={{ width: "100%", display: "block" }}
            />
          </button>
          <div style={{ textAlign: "center", marginTop: 8, color: "var(--subtext)" }}>
            or
          </div>
        </div>
      )}

      <label htmlFor="email" style={{ display: 'block', fontWeight: 600, marginBottom: 8 }}>
        Email
      </label>
      <input
        id="email"
        type="email"
        required
        autoComplete="email"
        placeholder="you@example.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        disabled={loading}
        style={{
          width: "100%",
          padding: "0.75rem 1rem",
          borderRadius: 8,
          border: "1px solid var(--muted)",
          marginBottom: 16,
          fontSize: "1rem",
        }}
      />

      <label htmlFor="password" style={{ display: 'block', fontWeight: 600, marginBottom: 8 }}>
        Password
      </label>
      <div style={{ position: "relative", marginBottom: 16 }}>
        <input
          id="password"
          type={showPass ? "text" : "password"}
          required
          autoComplete={isSignUp ? "new-password" : "current-password"}
          placeholder={isSignUp ? "Create a password" : "Your password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={loading}
          style={{
            width: "100%",
            padding: "0.75rem 1rem",
            borderRadius: 8,
            border: "1px solid var(--muted)",
            fontSize: "1rem",
          }}
        />
        <button
          type="button"
          onClick={() => setShowPass((v) => !v)}
          aria-label={showPass ? "Hide password" : "Show password"}
          style={{
            position: "absolute",
            right: 10,
            top: "50%",
            transform: "translateY(-50%)",
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--muted)",
            fontSize: "1.1rem",
          }}
          tabIndex={-1}
        >
          {showPass ? "🙈" : "👁️"}
        </button>
      </div>

      {error && <div style={{ color: "var(--error)", marginBottom: 16, textAlign: "center" }}>{error}</div>}
      {message && <div style={{ color: "var(--brand)", marginBottom: 16, textAlign: "center" }}>{message}</div>}

      <button
        type="submit"
        className="cta-button"
        disabled={loading}
        style={{ width: "100%", padding: "0.9em 1.5em" }}
      >
        {loading ? (isSignUp ? "Signing up..." : "Logging in...") : isSignUp ? "Sign Up" : "Log In"}
      </button>

      <div style={{ textAlign: "center", marginTop: 12 }}>
        {isSignUp ? (
          <>
            Already have an account?{' '}
            <button
              type="button"
              onClick={() => { setIsSignUp(false); setError(""); setMessage(""); }}
              disabled={loading}
              style={{
                background: "none",
                border: "none",
                color: "var(--brand)",
                textDecoration: "underline",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              Log In
            </button>
          </>
        ) : (
          <>
            New here?{' '}
            <button
              type="button"
              onClick={() => { setIsSignUp(true); setError(""); setMessage(""); }}
              disabled={loading}
              style={{
                background: "none",
                border: "none",
                color: "var(--brand)",
                textDecoration: "underline",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              Sign Up
            </button>
          </>
        )}
      </div>
    </form>
  );
}
