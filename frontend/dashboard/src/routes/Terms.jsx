// frontend/dashboard/src/routes/Terms.jsx
import React from "react";

export default function Terms() {
  return (
    <section className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-4 text-gray-900 dark:text-white">Terms &amp; Conditions</h1>
      <div className="space-y-3 text-gray-700 dark:text-gray-300">
        <p>
          These terms and conditions (“Agreement”) are entered into by and between <span className="font-semibold">Adam Shonting, doing business as Promptiv</span> (“Promptiv”, “we”, “us”, or “our”), and you (“User”, “you”, or “your”). By using the Promptiv website and services, you agree to these terms.
        </p>
        <ul className="list-disc ml-6">
          <li><b>Service:</b> Promptiv provides an AI-powered prompt rewriting tool. All purchases are handled by Paddle.com, the merchant of record for all orders. Paddle is responsible for customer service inquiries and returns.</li>
          <li><b>Usage:</b> Users are allowed one free prompt rewrite without an account. Registration is required for further use.</li>
          <li><b>Subscriptions &amp; Payments:</b> All payments are securely processed via Paddle. You agree to Paddle’s Terms in addition to these.</li>
          <li><b>Refunds:</b> See our Refund Policy.</li>
          <li><b>Changes:</b> We may update these terms from time to time. Your continued use signifies acceptance.</li>
          <li><b>Governing Law:</b> This Agreement is governed by the laws of Tennessee, USA.</li>
        </ul>
        <p>
          Paddle.com is the merchant of record for all orders. All customer service and returns are handled by Paddle. For issues, contact us at <a href="mailto:support@promptiv.io" className="text-blue-600 hover:underline">support@promptiv.io</a>.
        </p>
      </div>
    </section>
  );
}
