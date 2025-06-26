// frontend/dashboard/src/routes/NotFound.jsx
import React from "react";
import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="text-center py-20">
      <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">404</h1>
      <div className="mb-4 text-gray-600 dark:text-gray-400">Page not found.</div>
      <Link to="/" className="text-blue-600 hover:underline">Return Home</Link>
    </section>
  );
}
