"use client";

// Phase 4C.2A — Minimal MUJI-style breadcrumb / back button.
// For pages where the user navigates from a specific parent (known href), use
// `href`. For pages reachable from multiple origins (e.g. stock detail), omit
// `href` to fall back to router.back().

import Link from "next/link";
import { useRouter } from "next/navigation";

interface Props {
  parent: string;         // label for the parent hub, e.g. "พอร์ตโฟลิโอ"
  current: string;        // label for the current page, e.g. "DNA Analysis"
  href?: string;          // if omitted, pressing parent calls router.back()
}

export default function BackBreadcrumb({ parent, current, href }: Props) {
  const router = useRouter();

  const parentEl = href ? (
    <Link
      href={href}
      className="flex items-center gap-1 text-gray-400 hover:text-blue-600 transition-colors"
    >
      <span className="text-[11px]">←</span>
      <span>{parent}</span>
    </Link>
  ) : (
    <button
      onClick={() => router.back()}
      className="flex items-center gap-1 text-gray-400 hover:text-blue-600 transition-colors"
    >
      <span className="text-[11px]">←</span>
      <span>{parent}</span>
    </button>
  );

  return (
    <nav className="flex items-center gap-1.5 text-xs font-medium mb-4">
      {parentEl}
      <span className="text-gray-200">/</span>
      <span className="text-gray-600">{current}</span>
    </nav>
  );
}
