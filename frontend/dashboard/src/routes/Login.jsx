// frontend/dashboard/src/routes/Login.jsx
import React, { useState } from "react";
import { Link } from "react-router-dom";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  // ...handle login logic here...

  return (
    <section className="max-w-md mx-auto">
      <h1 className="text-3xl font-bold mb-4 text-gray-900 dark:text-white">Log In</h1>
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
          placeholder="Your password"
          autoComplete="current-password"
          value={password}
          onChange={e => setPassword(e.target.value)}
        />
        <button className="bg-blue-600 text-white font-bold py-2 rounded hover:bg-blue-700 transition">Log In</button>
      </form>
      <div className="text-sm mt-3">
        New here? <Link to="/signup" className="text-blue-600 hover:underline">Sign Up</Link>
      </div>
    </section>
  );
}
