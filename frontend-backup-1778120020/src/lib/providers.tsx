/**
 * providers.tsx — React Query provider wrapper for Next.js App Router
 *
 * Usage:
 *   import { QueryProvider } from "@/lib/providers";
 *   // Wrap root layout or specific pages
 */

"use client";

import React, { ReactNode, useState, useEffect, useMemo, lazy, Suspense } from "react";
import {
  QueryClient,
  QueryClientProvider,
  defaultShouldDehydrateQuery,
} from "@tanstack/react-query";

// ---------------------------------------------------------------------------
// Create a client with sensible defaults
// ---------------------------------------------------------------------------

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000, // 1 minute
        refetchOnWindowFocus: false,
        retry: (failureCount, error: any) => {
          // Only retry on network or 5xx errors
          if (error?.status >= 500) return failureCount < 2;
          return false;
        },
      },
      dehydrate: {
        shouldDehydrateQuery: (query) =>
          defaultShouldDehydrateQuery(query) ||
          query.state.status === "pending",
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

function getQueryClient(): QueryClient {
  if (typeof window === "undefined") {
    // Server — always create a fresh client
    return makeQueryClient();
  }
  // Browser — reuse existing or create
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}

// ---------------------------------------------------------------------------
// Provider component
// ---------------------------------------------------------------------------

interface QueryProviderProps {
  children: ReactNode;
}

export function QueryProvider({ children }: QueryProviderProps) {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {/* Devtools only rendered in development */}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDehydratedBoundary />
      )}
    </QueryClientProvider>
  );
}

/** Dev-only: hydrate devtools after initial render to avoid SSR mismatch */
function ReactQueryDehydratedBoundary() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  // Dynamic import avoids bundling devtools in production
  return <LazyDevtools />;
}

function LazyDevtools() {
  const Devtools = useMemo(
    () =>
      lazy(() =>
        import("@tanstack/react-query-devtools").then((mod) => ({
          default: mod.ReactQueryDevtools,
        }))
      ),
    []
  );
  return (
    <Suspense fallback={null}>
      <Devtools initialIsOpen={false} />
    </Suspense>
  );
}
