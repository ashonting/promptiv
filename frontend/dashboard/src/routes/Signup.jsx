// frontend/dashboard/src/routes/Signup.jsx
import React, { useState } from "react";
import { Link } from "react-router-dom";

export default function Signup() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  // ...handle signup logic here...

  return (
    <section className="max-w-md mx-auto">
      <h1 className="text-3xl font-bold mb-4 text-gray-900 dark:text-white">Sign Up</h1>
      <form className="flex flex-col gap-4">
        <input
          className="p-2 border rounded dark:bg-gray-800 dark:text-white"
          type="email"
          placeholder="you@example.com"
          autoComplete="username"
          value={email}
          onChange={e => setEmail(e.target.value)}
        />
        <input
          className="p-2 border rounded dark:bg-gray-800 dark:text-white"
          type="password"
          placeholder="Create a password"
          autoComplete="new-password"
          value={password}
          onChange={e => setPassword(e.target.value)}
        />
        <button className="bg-blue-600 text-white font-bold py-2 rounded hover:bg-blue-700 transition">Sign Up</button>
      </form>
      <div className="text-sm mt-3">
        Already have an account? <Link to="/login" className="text-blue-600 hover:underline">Log In</Link>
      </div>
    </section>
  );
}
