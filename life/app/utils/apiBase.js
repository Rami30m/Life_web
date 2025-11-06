// Centralized API base URL for frontend fetch calls
// Priority: NEXT_PUBLIC_SSO_API_BASE → production default → localhost
export const API_BASE =
  process.env.NEXT_PUBLIC_SSO_API_BASE ||
  (process.env.NODE_ENV === 'production'
    ? 'https://api.v4.life'
    : 'http://localhost:8000');



