'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';

interface ProgramSummary {
  id: string;
  organization_name: string;
  title: string;
  slug: string;
  description: string;
  visibility: string;
  scopes: Array<{ asset_type: string; asset_value: string; in_scope: boolean; max_severity?: string }>;
  rewards: Array<{ severity: string; min_amount: string; max_amount: string; currency: string }>;
}

export default function ProgramsCatalogPage() {
  const [programs, setPrograms] = useState<ProgramSummary[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPrograms = async () => {
      setLoading(true);
      try {
        const query = search ? `?search=${encodeURIComponent(search)}` : '';
        const res = await apiClient(`/api/v1/programs/${query}`);
        if (res.ok) {
          const data = await res.json();
          setPrograms(data.results || data || []);
        }
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    };

    const debounce = setTimeout(fetchPrograms, 300);
    return () => clearTimeout(debounce);
  }, [search]);

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8 dark:bg-gray-900">
      <div className="mx-auto max-w-5xl space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
            Bug Bounty Programs
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Discover verified public security programs and start hunting vulnerabilities.
          </p>
        </div>

        <div>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search programs by company, title, or asset..."
            className="block w-full rounded-lg border border-gray-300 bg-white px-4 py-3 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
          />
        </div>

        {loading ? (
          <div className="py-12 text-center text-gray-500">Loading programs...</div>
        ) : programs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 p-12 text-center dark:border-gray-700">
            <p className="text-gray-500 dark:text-gray-400">No active bug bounty programs found.</p>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {programs.map((program) => (
              <div
                key={program.id}
                className="flex flex-col justify-between rounded-xl border border-gray-200 bg-white p-6 shadow-sm transition hover:shadow-md dark:border-gray-800 dark:bg-gray-800"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                      {program.organization_name}
                    </span>
                    {program.visibility === 'private' && (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                        Private Invite
                      </span>
                    )}
                  </div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    {program.title}
                  </h2>
                  <p className="text-sm text-gray-600 line-clamp-2 dark:text-gray-400">
                    {program.description}
                  </p>

                  <div className="flex flex-wrap gap-2 pt-2">
                    {program.scopes.filter((s) => s.in_scope).slice(0, 3).map((scope, idx) => (
                      <span
                        key={idx}
                        className="rounded bg-gray-100 px-2 py-1 text-xs font-mono text-gray-700 dark:bg-gray-700 dark:text-gray-300"
                      >
                        {scope.asset_value}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="mt-6 flex items-center justify-between border-t border-gray-100 pt-4 dark:border-gray-700">
                  <div className="text-xs text-gray-500">
                    {program.rewards.length > 0 ? (
                      <span className="font-semibold text-green-600 dark:text-green-400">
                        Rewards up to $
                        {Math.max(...program.rewards.map((r) => parseFloat(r.max_amount)))}
                      </span>
                    ) : (
                      'Points & Swag'
                    )}
                  </div>
                  <Link
                    href={`/programs/${program.slug}`}
                    className="text-sm font-semibold text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
                  >
                    View Scope &rarr;
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
