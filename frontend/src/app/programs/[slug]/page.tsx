'use client';

import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';

interface ProgramDetail {
  id: string;
  organization_name: string;
  title: string;
  slug: string;
  description: string;
  rules_of_engagement: string;
  safe_harbor: string;
  disclosure_policy: string;
  scopes: Array<{ id: string; asset_type: string; asset_value: string; in_scope: boolean; max_severity?: string }>;
  rewards: Array<{ id: string; severity: string; min_amount: string; max_amount: string; currency: string }>;
}

export default function ProgramDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const resolvedParams = use(params);
  const [program, setProgram] = useState<ProgramDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient(`/api/v1/programs/${resolvedParams.slug}/`)
      .then(async (res) => {
        if (!res.ok) {
          setError('Program not found or access restricted.');
          return;
        }
        const data = await res.json();
        setProgram(data);
      })
      .catch(() => setError('Failed to load program details.'))
      .finally(() => setLoading(false));
  }, [resolvedParams.slug]);

  if (loading) {
    return <div className="py-20 text-center">Loading program details...</div>;
  }

  if (error || !program) {
    return (
      <div className="py-20 text-center text-red-600 dark:text-red-400">
        {error || 'Program not found'}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8 dark:bg-gray-900">
      <div className="mx-auto max-w-5xl space-y-8">
        <div>
          <Link href="/programs" className="text-sm font-semibold text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">
            &larr; Back to all programs
          </Link>
          <div className="mt-4 flex items-center justify-between">
            <div>
              <span className="text-sm font-medium uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                {program.organization_name}
              </span>
              <h1 className="mt-1 text-3xl font-extrabold text-gray-900 dark:text-white">
                {program.title}
              </h1>
            </div>
            <Link
              href={`/reports/submit?program=${program.slug}`}
              className="rounded-md bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
            >
              Submit Vulnerability
            </Link>
          </div>
        </div>

        {/* --- Program Description --- */}
        <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800 space-y-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Program Overview</h2>
          <p className="text-sm text-gray-600 leading-relaxed dark:text-gray-300">
            {program.description}
          </p>
        </div>

        {/* --- Scope Targets --- */}
        <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Scope Targets</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wider text-gray-500">
                  <th className="py-2">Target Asset</th>
                  <th className="py-2">Type</th>
                  <th className="py-2">Eligibility</th>
                  <th className="py-2">Max Severity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800 font-mono text-xs">
                {program.scopes.map((s) => (
                  <tr key={s.id}>
                    <td className="py-3 font-semibold text-gray-900 dark:text-gray-100">{s.asset_value}</td>
                    <td className="py-3 text-gray-600 dark:text-gray-400 uppercase">{s.asset_type}</td>
                    <td className="py-3">
                      {s.in_scope ? (
                        <span className="rounded bg-green-50 px-2 py-0.5 text-green-700 dark:bg-green-950/60 dark:text-green-300">
                          In Scope
                        </span>
                      ) : (
                        <span className="rounded bg-gray-100 px-2 py-0.5 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                          Out of Scope
                        </span>
                      )}
                    </td>
                    <td className="py-3 uppercase text-gray-600 dark:text-gray-400">
                      {s.max_severity || 'Any'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* --- Reward Structure --- */}
        {program.rewards.length > 0 && (
          <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Reward Matrix</h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {program.rewards.map((r) => (
                <div key={r.id} className="rounded-lg border border-gray-200 p-4 text-center dark:border-gray-700">
                  <div className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                    {r.severity}
                  </div>
                  <div className="mt-2 text-lg font-bold text-gray-900 dark:text-white">
                    ${r.min_amount} - ${r.max_amount}
                  </div>
                  <div className="text-xs text-gray-400">{r.currency}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* --- Rules & Safe Harbor --- */}
        <div className="grid gap-6 md:grid-cols-2">
          <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800 space-y-2">
            <h3 className="font-semibold text-gray-900 dark:text-white">Rules of Engagement</h3>
            <p className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap dark:text-gray-400">
              {program.rules_of_engagement || 'Follow responsible disclosure guidelines.'}
            </p>
          </div>
          <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800 space-y-2">
            <h3 className="font-semibold text-gray-900 dark:text-white">Safe Harbor Policy</h3>
            <p className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap dark:text-gray-400">
              {program.safe_harbor}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
