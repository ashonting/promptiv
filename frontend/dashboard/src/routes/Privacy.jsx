// frontend/dashboard/src/routes/Privacy.jsx
import React from "react";

export default function Privacy() {
  return (
    <section className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-4 text-gray-900 dark:text-white">Privacy Policy</h1>
      <div className="space-y-3 text-gray-700 dark:text-gray-300">
        <p>
          Promptiv (“we”, “us”, “our”) is committed to protecting your privacy. This policy explains what information we collect, how we use it, and your rights.
        </p>
        <ul className="list-disc ml-6">
          <li><b>Personal Data:</b> We collect only the minimum data needed for order fulfillment and support. Paddle.com, as merchant of record, is responsible for GDPR/CCPA compliance for payments and customer data.</li>
          <li><b>Marketing:</b> If you opt in, we may send you product updates. You can unsubscribe at any time.</li>
          <li><b>Data Usage:</b> We do not sell your data. Data is only used for order processing, customer support, and service improvement.</li>
          <li><b>Third Parties:</b> Paddle may share data with us for order support. Their privacy policy governs payment data.</li>
          <li><b>Your Rights:</b> You may request deletion or correction of your data by emailing <a href="mailto:support@promptiv.io" className="text-blue-600 hover:underline">support@promptiv.io</a>.</li>
        </ul>
        <p>
          For more details, contact us at <a href="mailto:support@promptiv.io" className="text-blue-600 hover:underline">support@promptiv.io</a>.
        </p>
      </div>
    </section>
  );
}
