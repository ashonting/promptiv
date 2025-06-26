import React from "react";
export default function UserDashboard({ user }) {
  return (
    <div>
      <h1>Welcome, {user.email}!</h1>
      <p>This is your user dashboard.</p>
    </div>
  );
}
