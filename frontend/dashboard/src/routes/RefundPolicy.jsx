// frontend/dashboard/src/routes/RefundPolicy.jsx
import React from "react";

export default function RefundPolicy() {
  return (
    <section className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-4 text-gray-900 dark:text-white">Refund Policy</h1>
      <div className="space-y-3 text-gray-700 dark:text-gray-300">
        <p>
          As all payments are processed by Paddle.com (our merchant of record), any refunds will be handled in accordance with Paddle’s policies.
        </p>
        <ul className="list-disc ml-6">
          <li>Pro users may cancel their subscription at any time. Cancellation will prevent future billing, but no refunds are provided for unused time or partial months.</li>
          <li>If you experience an issue, please contact us at <a href="mailto:support@promptiv.io" className="text-blue-600 hover:underline">support@promptiv.io</a> and we’ll help resolve it promptly.</li>
          <li>Any refund granted by agreement will be processed by Paddle.</li>
        </ul>
      </div>
    </section>
  );
}
