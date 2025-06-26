import React from "react";

export default function Pricing() {
  return (
    <section>
      <h1 className="text-3xl font-bold mb-6 text-gray-900 dark:text-white">Pricing</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        <div className="border rounded-lg p-6 bg-white dark:bg-gray-800 shadow">
          <h2 className="text-2xl font-bold mb-2 text-blue-700">Basic</h2>
          <div className="text-lg font-bold mb-4">$0</div>
          <ul className="list-disc ml-6 mb-2 text-gray-700 dark:text-gray-200">
            <li>1 free rewrite (no signup)</li>
            <li>3 free rewrites/month (with email)</li>
            <li>Try every feature before upgrading</li>
            <li>No credit card required</li>
          </ul>
        </div>
        <div className="border rounded-lg p-6 bg-white dark:bg-gray-800 shadow">
          <h2 className="text-2xl font-bold mb-2 text-blue-700">Pro</h2>
          <div className="text-lg font-bold mb-4">$4.99/mo</div>
          <ul className="list-disc ml-6 mb-2 text-gray-700 dark:text-gray-200">
            <li>30 expert-level rewrites monthly</li>
            <li>Access all features</li>
            <li>Priority support</li>
          </ul>
        </div>
      </div>
      <div className="bg-blue-50 dark:bg-blue-900 p-4 rounded mb-6">
        <h3 className="font-semibold mb-1">Frequently Asked Questions</h3>
        <ul className="list-disc ml-6 text-gray-700 dark:text-gray-200">
          <li>Every user gets one free rewrite on the home page. Sign up for more and unlock full features.</li>
          <li>Subscriptions handled by Paddle. Cancel anytime. No refunds for unused time. See our Terms.</li>
        </ul>
      </div>
    </section>
  );
}
