import React from "react";
import { Link } from "react-router-dom";

export default function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900 transition-colors">
      {/* GLOBAL TAILWIND TEST BLOCK (debug only) */}
      <div className="fixed top-8 left-8 z-[9999] bg-red-600 text-white p-4 text-2xl rounded-xl shadow-xl border-4 border-black">
        TAILWIND REACT TEST BLOCK
      </div>
      {/* Header */}
      <header className="w-full border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2 text-xl font-bold text-blue-700 dark:text-blue-300">
            <span className="rounded-full bg-blue-600 text-white px-3 py-1 text-lg">P</span>
            Promptiv
          </Link>
        </div>
        <nav className="flex gap-6">
          <Link to="/pricing" className="hover:underline">Pricing</Link>
          <Link to="/login" className="hover:underline">Log In</Link>
          <Link to="/signup" className="hover:underline">Sign Up</Link>
        </nav>
      </header>
      {/* Main content */}
      <main className="flex-1 w-full max-w-2xl mx-auto px-4 py-10">
        {children}
      </main>
      {/* Global Footer */}
      <footer className="w-full text-center text-sm text-gray-500 dark:text-gray-400 py-4 border-t border-gray-200 dark:border-gray-700">
        <nav className="space-x-4">
          <Link to="/">Home</Link>
          <Link to="/pricing">Pricing</Link>
          <Link to="/terms">Terms of Service</Link>
          <Link to="/privacy">Privacy Policy</Link>
          <Link to="/refund-policy">Refund Policy</Link>
          <Link to="/contact">Contact</Link>
        </nav>
        <div className="mt-2">&copy; 2025 Promptiv. All rights reserved.</div>
      </footer>
    </div>
  );
}
