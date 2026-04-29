"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [idea, setIdea] = useState<string>("…loading");

  useEffect(() => {
    fetch("/api")
      .then((r) => r.text())
      .then(setIdea)
      .catch((e) => setIdea(`Error: ${e?.message ?? String(e)}`));
  }, []);

  return (
    <main className="flex-1 p-8 font-sans bg-zinc-50 dark:bg-black">
      <h1 className="text-3xl font-bold mb-4 text-black dark:text-zinc-50">
        Business Idea Generator
      </h1>
      <div className="w-full max-w-2xl p-6 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg shadow-sm">
        <p className="text-gray-900 dark:text-gray-100 whitespace-pre-wrap">
          {idea}
        </p>
      </div>
    </main>
  );
}
