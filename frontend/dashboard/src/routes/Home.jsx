// frontend/dashboard/src/routes/Home.jsx
import React, { useState } from "react";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [usedFree, setUsedFree] = useState(
    localStorage.getItem("promptiv_free_used") === "true"
  );
  const [error, setError] = useState(null);

  const handleRewrite = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      // POST to your API endpoint
      const response = await fetch("/api/rewrite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) throw new Error("Rewrite failed.");
      const data = await response.json();
      setResult(data.rewrite || data.result || "No result returned.");
      setUsedFree(true);
      localStorage.setItem("promptiv_free_used", "true");
    } catch (err) {
      setError(err.message || "An error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section>
      <div className="bg-red-500 text-white p-10">
        If you see a big red box, Tailwind is working.
      </div>

      <h1 className="text-3xl sm:text-4xl font-bold mb-2 text-gray-900 dark:text-white">
        Instantly Rewrite Your Prompt—<span className="text-blue-600">Free</span>
      </h1>
      <p className="mb-6 text-gray-700 dark:text-gray-300">
        Test our AI rewrite tool in one click.
        <span className="inline-block ml-1">No signup required for your first try.</span>
      </p>
      <form
        className="flex gap-2 mb-4"
        onSubmit={handleRewrite}
        autoComplete="off"
      >
        <input
          type="text"
          placeholder="Paste your prompt here…"
          className="flex-1 px-4 py-2 rounded border border-gray-300 focus:ring-2 focus:ring-blue-400 dark:bg-gray-800 dark:text-white dark:border-gray-600 transition"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={loading || usedFree}
          required
        />
        <button
          type="submit"
          className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition font-semibold disabled:bg-gray-400"
          disabled={!prompt || loading || usedFree}
        >
          {loading ? "Rewriting…" : usedFree ? "Limit Reached" : "Rewrite"}
        </button>
      </form>
      {error && (
        <div className="mb-2 text-red-500 font-medium">{error}</div>
      )}
      {usedFree && (
        <div className="mb-2 text-sm text-gray-600 dark:text-gray-400">
          <span className="font-medium">Free trial used.</span> Sign up to unlock more expert rewrites.
        </div>
      )}
      {result && (
        <div className="mt-6 bg-white dark:bg-gray-800 rounded shadow p-4 border border-blue-200 dark:border-blue-900">
          <div className="text-gray-700 dark:text-gray-200 font-semibold mb-2">
            <span className="text-blue-600">Your rewritten prompt:</span>
          </div>
          <pre className="whitespace-pre-wrap text-sm">{result}</pre>
        </div>
      )}
    </section>
  );
}
