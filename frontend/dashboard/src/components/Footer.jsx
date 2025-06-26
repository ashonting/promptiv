// frontend/dashboard/src/components/Footer.jsx
import React from "react";

export default function Footer() {
  return (
    <footer className="w-full mt-auto py-4 px-2 text-center bg-black/60 text-gray-300 text-sm rounded-t-2xl">
      <nav className="flex flex-wrap justify-center gap-4 mb-2">
        <a href="/" className="hover:text-blue-300">Home</a>
        <a href="/pricing" className="hover:text-blue-300">Pricing</a>
        <a href="/terms" className="hover:text-blue-300">Terms</a>
        <a href="/privacy" className="hover:text-blue-300">Privacy</a>
        <a href="/refund-policy" className="hover:text-blue-300">Refunds</a>
        <a href="/contact" className="hover:text-blue-300">Contact</a>
      </nav>
      <div>
        &copy; {new Date().getFullYear()} Adam Shonting, doing business as Promptiv.
        All rights reserved. Paddle.com is the Merchant of Record for all orders. Support:{" "}
        <a href="mailto:support@promptiv.io" className="underline hover:text-blue-300">
          support@promptiv.io
        </a>
      </div>
    </footer>
  );
}
