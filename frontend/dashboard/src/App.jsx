import React, { Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./ProtectedRoute";

// Lazy-load route pages
const Home       = React.lazy(() => import("./routes/Home"));
const Login      = React.lazy(() => import("./routes/Login"));
const Signup     = React.lazy(() => import("./routes/Signup"));
const Dashboard  = React.lazy(() => import("./routes/Dashboard"));
const Pricing    = React.lazy(() => import("./routes/Pricing"));
const Contact    = React.lazy(() => import("./routes/Contact"));
const Terms      = React.lazy(() => import("./routes/Terms"));
const Privacy    = React.lazy(() => import("./routes/Privacy"));
const Refund     = React.lazy(() => import("./routes/RefundPolicy"));
const Reset      = React.lazy(() => import("./routes/Reset"));
const NotFound   = React.lazy(() => import("./routes/NotFound"));

export default function App() {
  return (
    <Layout>
      {/* TAILWIND TEST BLOCK: REMOVE WHEN CONFIRMED */}
      <div className="bg-red-600 text-white p-4 text-xl text-center">
        If you see this red box, Tailwind is working for React!
      </div>

      {/* The rest of your app */}
      <Suspense fallback={<div className="text-center mt-16">Loading…</div>}>
        <Routes>
          <Route path="/"          element={<Home />} />
          <Route path="/login"     element={<Login />} />
          <Route path="/signup"    element={<Signup />} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/pricing"       element={<Pricing />} />
          <Route path="/contact"       element={<Contact />} />
          <Route path="/terms"         element={<Terms />} />
          <Route path="/privacy"       element={<Privacy />} />
          <Route path="/refund-policy" element={<Refund />} />
          <Route path="/reset"         element={<Reset />} />
          <Route path="*"              element={<NotFound />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
