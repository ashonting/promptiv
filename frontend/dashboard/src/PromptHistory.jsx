// frontend/dashboard/src/PromptHistory.jsx

import React, { useEffect, useState } from "react";
import Modal from "./components/Modal";
import supabase from "./supabaseClient";

function PromptHistory({ user, isPaidUser, quotaUsed, quotaAvailable, onUpgrade }) {
  const [promptInput, setPromptInput] = useState("");
  const [results, setResults] = useState([]);
  const [error, setError] = useState("");
  const [quotaExceeded, setQuotaExceeded] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);

  // Generate or retrieve device_hash for anonymous users
  useEffect(() => {
    if (!localStorage.getItem("device_hash")) {
      try {
        const hash = crypto.randomUUID();
        localStorage.setItem("device_hash", hash);
      } catch (_e) {
        console.warn("crypto.randomUUID not supported");
      }
    }
  }, []);

  useEffect(() => {
    if (quotaExceeded) setShowUpgradeModal(true);
  }, [quotaExceeded]);

  const handlePromptSubmit = async () => {
    setError("");
    setQuotaExceeded(false);
    try {
      const headers = { "Content-Type": "application/json" };
      // Include auth header if logged in
      if (user && localStorage.getItem("accessToken")) {
        headers.Authorization = `Bearer ${localStorage.getItem("accessToken")}`;
      }

      // Build request payload
      const payload = { prompt: promptInput };
      if (!user) {
        payload.device_hash = localStorage.getItem("device_hash");
      }

      const response = await fetch("/api/rewrite", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (response.status === 403) {
        const data = await response.json();
        setQuotaExceeded(true);
        setError(data.detail || "Quota exceeded.");
        return;
      }

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Unknown error");
      }

      const data = await response.json();
      // Normalize results: backend may return variants or single rewrite
      let items = [];
      if (data.results) {
        items = data.results;
      } else if (data.variants) {
        items = data.variants;
      } else if (data.rewritten_prompt) {
        items = [{ type: data.variant_style, text: data.rewritten_prompt }];
      }
      setResults(items);
    } catch (err) {
      setError(err.message);
    }
  };

  const renderRewrites = () => {
    if (!results.length) return null;
    if (!isPaidUser) {
      const concise = results.find(r => r.type === "Concise") || results[0];
      return (
        <div className="result-item" style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Concise Rewrite:</div>
          <div>{concise.text}</div>
        </div>
      );
    }
    return results.map((r, idx) => (
      <div key={idx} className="result-item" style={{
        marginBottom: 18,
        padding: "1.1em",
        background: "#fafbff",
        borderRadius: 10,
        boxShadow: "0 1px 6px #bbcbe633"
      }}>
        <div style={{ fontWeight: 700, marginBottom: 2 }}>{r.type}:</div>
        <div style={{ marginBottom: 7 }}>{r.text}</div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          {r.bestLLM && (
            <span style={{ color: "#6c7ab3", fontSize: "0.96em" }}>
              <b>Best LLM:</b> {r.bestLLM}
            </span>
          )}
          <button
            onClick={() => navigator.clipboard.writeText(r.text)}
            className="cta-button"
            style={{ marginLeft: 10, fontSize: 13, padding: "0.4em 1em" }}
          >
            Copy
          </button>
        </div>
      </div>
    ));
  };

  return (
    <div className="prompt-history" style={{ maxWidth: 650, margin: "0 auto", padding: "1.5em" }}>
      <h2 style={{ fontSize: "1.7em", marginBottom: 15, fontWeight: 700 }}>
        Prompt History
      </h2>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 20
      }}>
        <div>
          <span style={{ fontWeight: 600 }}>Remaining Quota: </span>
          <span style={{ color: quotaAvailable - quotaUsed < 5 ? "#e7685a" : "#0a8a49" }}>
            {quotaAvailable - quotaUsed} / {quotaAvailable}
          </span>
        </div>
        {!isPaidUser && (
          <button className="cta-button" style={{ fontSize: 14 }} onClick={() => setShowUpgradeModal(true)}>
            Upgrade
          </button>
        )}
      </div>
      <div style={{
        display: "flex",
        alignItems: "flex-end",
        gap: 12,
        marginBottom: 16
      }}>
        <input
          value={promptInput}
          onChange={e => setPromptInput(e.target.value)}
          placeholder="Enter your prompt here"
          className="prompt-input"
          style={{
            flex: 1,
            borderRadius: 8,
            padding: "0.7em 1em",
            border: "1px solid #b9bede",
            fontSize: "1.09em"
          }}
        />
        <button
          onClick={handlePromptSubmit}
          className="cta-button"
          style={{ padding: "0.7em 2.1em", fontWeight: 700, fontSize: "1.1em" }}
        >
          Rewrite
        </button>
      </div>
      {error && <p className="error" style={{ color: "#d32d41", marginBottom: 10 }}>{error}</p>}
      <div className="results">
        {renderRewrites()}
      </div>

      <Modal open={showUpgradeModal} onClose={() => setShowUpgradeModal(false)}>
        <div style={{ textAlign: "center" }}>
          <h3 style={{ fontWeight: 800, marginBottom: 7 }}>Upgrade for Unlimited Rewrites!</h3>
          <div style={{ color: "#6c7ab3", marginBottom: 10 }}>
            You’ve reached your monthly quota. Upgrade now to get unlimited rewrites, access all AI models, and premium support.
          </div>
          <button
            className="cta-button"
            style={{ width: "90%", margin: "13px 0", padding: "0.85em", fontWeight: 800, fontSize: 18 }}
            onClick={() => {
              setShowUpgradeModal(false);
              if (onUpgrade) onUpgrade();
              window.location.href = "/pricing";
            }}
          >
            View Pricing & Upgrade
          </button>
          <div style={{ fontSize: 13, color: "#b5b5b5" }}>
            Have a code? Enter it at checkout.
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default PromptHistory;
