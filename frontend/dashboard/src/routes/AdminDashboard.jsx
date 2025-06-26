import React from "react";
export default function AdminDashboard({ user }) {
  return (
    <div>
      <h1>Admin Dashboard</h1>
      <p>Welcome, {user.email} (ADMIN).</p>
    </div>
  );
}
