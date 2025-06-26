import { createClient } from '@supabase/supabase-js'

// These are injected from your frontend/dashboard/.env at build time by Vite
const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
);

export default supabase;
