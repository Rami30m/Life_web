"use client";

import { Suspense } from "react";
import OAuthLoginPage from "../../components/oauth-login";

export const dynamic = 'force-dynamic';

export default function AuthorizePage() {
  return (
    <Suspense fallback={null}>
      <OAuthLoginPage />
    </Suspense>
  );
}

