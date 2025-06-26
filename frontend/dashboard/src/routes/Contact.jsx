// frontend/dashboard/src/routes/Contact.jsx
import React, { useState } from "react";

export default function Contact() {
  const [sent, setSent] = useState(false);

  // Demo form handler
  const handleSubmit = e => {
    e.preventDefault();
    setSent(true); // In production, handle with backend API.
  };

  return (
    <section className="max-w-lg mx-auto">
      <h1 className="text-3xl font-bold mb-2 text-gray-900 dark:text-white">Contact Us</h1>
      <p className="mb-4 text-gray-700 dark:text-gray-300">
        For support, email <a href="mailto:support@promptiv.io" className="text-blue-600 hover:underline">support@promptiv.io</a>.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 bg-white dark:bg-gray-800 rounded p-6 shadow">
        <input className="p-2 border rounded dark:bg-gray-900 dark:text-white" placeholder="Your Name" required />
        <input className="p-2 border rounded dark:bg-gray-900 dark:text-white" placeholder="you@email.com" required type="email" />
        <textarea className="p-2 border rounded dark:bg-gray-900 dark:text-white" placeholder="Your message…" rows={4} required />
        <button className="bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition" type="submit">
          Send Message
        </button>
        {sent && (
          <div className="text-green-600 font-medium mt-2 animate-pulse">Thanks for reaching out! We'll respond soon.</div>
        )}
      </form>
    </section>
  );
}
