// frontend/dashboard/src/routes/Reset.jsx
import React from "react";

export default function Reset() {
  return (
    <section className="max-w-md mx-auto">
      <h1 className="text-2xl font-bold mb-2 text-gray-900 dark:text-white">Reset Password</h1>
      <form className="flex flex-col gap-4">
        <input className="p-2 border rounded dark:bg-gray-800 dark:text-white" type="email" placeholder="Enter your email" required />
        <button className="bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition" type="submit">
          Reset Password
        </button>
      </form>
    </section>
  );
}
