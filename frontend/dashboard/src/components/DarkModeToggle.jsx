// frontend/dashboard/src/components/DarkModeToggle.jsx

import React, { useEffect, useState } from 'react';

export default function DarkModeToggle() {
  const [dark, setDark] = useState(() => {
    if (typeof window === 'undefined') return false;
    const stored = localStorage.getItem('dark-mode');
    if (stored) return stored === 'true';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    document.body.classList.toggle('dark', dark);
    localStorage.setItem('dark-mode', dark);
  }, [dark]);

  return (
    <button
      onClick={() => setDark(d => !d)}
      aria-label="Toggle dark mode"
      style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.4rem' }}
    >
      {dark ? '☀️' : '🌙'}
    </button>
  );
}

