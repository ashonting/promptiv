// frontend/dashboard/src/AuthForm.jsx

import React, { useState, useEffect } from "react";
import supabase from "./supabaseClient";

// NOTE: these SVGs live in your dist root (copied from public/) under /dashboard
const GOOGLE_BUTTON_LIGHT = "/dashboard/web_light_sq_ctn.svg";
const GOOGLE_BUTTON_DARK  = "/dashboard/web_dark_sq_ctn.svg";

function getPrefersDark() {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );
}

const AuthForm = ({
  showGoogle = true, // allow login/signup page to hide if needed
}) => {
  const [email, setEmail]         = useState("");
  const [password, setPassword]   = useState("");
  const [isSignUp, setIsSignUp]   = useState(false);
  const [error, setError]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [message, setMessage]     = useState("");
  const [isDarkMode, setIsDarkMode] = useState(getPrefersDark());
  const [showPass, setShowPass]   = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = e => setIsDarkMode(e.matches);
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  const handleGoogleLogin = async e => {
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

  const handleSubmit = async e => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");
    try {
      if (isSignUp) {
        const { error: signUpError } = await supabase.auth.signUp({
          email,
          password,
        });
        if (signUpError) throw signUpError;
        setMessage("Sign up successful! Please check your email to confirm.");
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (signInError) throw signInError;
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
        background: "#fff",
        borderRadius: 14,
        boxShadow: "0 2px 12px rgba(40,54,100,0.09)",
        padding: "2rem 2rem 1.5rem 2rem",
        maxWidth: 380,
        width: "100%",
        margin: "2rem auto",
      }}
    >
      <h2 style={{ textAlign: "center", marginBottom: 18 }}>
        {isSignUp ? "Sign Up" : "Log In"}
      </h2>

      {showGoogle && (
        <>
          <button
            type="button"
            className="google-btn"
            onClick={handleGoogleLogin}
            disabled={loading}
            style={{
              width: "100%",
              border: "1.5px solid #d1d5db",
              borderRadius: 8,
              padding: "0.7rem 0",
              background: "#fff",
              color: "#333",
              fontWeight: 600,
              fontSize: "1.09rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "12px",
              marginBottom: 18,
              boxShadow: "0 1px 4px #e0e7ef4d",
            }}
          >
            <img
              src={isDarkMode ? GOOGLE_BUTTON_DARK : GOOGLE_BUTTON_LIGHT}
              alt="Continue with Google"
              style={{
                height: 26,
                width: 26,
                borderRadius: 5,
                marginRight: 12,
                background: "#fff",
              }}
            />
            Continue with Google
          </button>
          <div
            style={{
              textAlign: "center",
              fontSize: "1rem",
              margin: "0 0 10px 0",
            }}
          >
            or
          </div>
        </>
      )}

      <label htmlFor="email" style={{ fontWeight: 600 }}>
        Email
      </label>
      <input
        id="email"
        type="email"
        required
        autoComplete="email"
        placeholder="you@example.com"
        value={email}
        onChange={e => setEmail(e.target.value)}
        style={{
          display: "block",
          marginBottom: 14,
          width: "100%",
          padding: "0.75rem 1.1rem",
          borderRadius: 8,
          border: "1px solid #ccc",
          fontSize: "1rem",
        }}
        disabled={loading}
      />

      <label htmlFor="password" style={{ fontWeight: 600 }}>
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
          onChange={e => setPassword(e.target.value)}
          style={{
            display: "block",
            width: "100%",
            padding: "0.75rem 1.1rem",
            borderRadius: 8,
            border: "1px solid #ccc",
            fontSize: "1rem",
          }}
          disabled={loading}
        />
        <button
          type="button"
          aria-label={showPass ? "Hide password" : "Show password"}
          onClick={() => setShowPass(v => !v)}
          style={{
            position: "absolute",
            right: 10,
            top: "50%",
            transform: "translateY(-50%)",
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: "1rem",
            color: "#666",
          }}
          tabIndex={-1}
        >
          {showPass ? "🙈" : "👁️"}
        </button>
      </div>

      {error && (
        <div
          style={{
            color: "#c0392b",
            marginBottom: 10,
            textAlign: "center",
            fontWeight: 500,
          }}
        >
          {error}
        </div>
      )}
      {message && (
        <div
          style={{
            color: "#198754",
            marginBottom: 10,
            textAlign: "center",
            fontWeight: 500,
          }}
        >
          {message}
        </div>
      )}

      <button
        type="submit"
        className="cta-button"
        style={{ width: "100%", marginBottom: 12 }}
        disabled={loading}
      >
        {loading
          ? isSignUp
            ? "Signing up..."
            : "Logging in..."
          : isSignUp
          ? "Sign Up"
          : "Log In"}
      </button>

      <div style={{ textAlign: "center", fontSize: "1rem", marginTop: 10 }}>
        {isSignUp ? (
          <>
            Already have an account?{" "}
            <button
              type="button"
              style={{
                color: "#3b82f6",
                background: "none",
                border: "none",
                textDecoration: "underline",
                cursor: "pointer",
                fontWeight: 600,
                padding: 0,
              }}
              onClick={() => {
                setIsSignUp(false);
                setError("");
                setMessage("");
              }}
              disabled={loading}
            >
              Log In
            </button>
          </>
        ) : (
          <>
            New here?{" "}
            <button
              type="button"
              style={{
                color: "#3b82f6",
                background: "none",
                border: "none",
                textDecoration: "underline",
                cursor: "pointer",
                fontWeight: 600,
                padding: 0,
              }}
              onClick={() => {
                setIsSignUp(true);
                setError("");
                setMessage("");
              }}
              disabled={loading}
            >
              Sign Up
            </button>
          </>
        )}
      </div>
    </form>
  );
};

export default AuthForm;
