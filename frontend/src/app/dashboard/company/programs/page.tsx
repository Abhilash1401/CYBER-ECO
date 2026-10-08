'use client';
import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import Link from 'next/link';

export default function ProgramsPage() {
  const [programs, setPrograms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchPrograms();
  }, []);

  const fetchPrograms = async () => {
    try {
      const res = await apiClient('/api/v1/programs/manage/list/');
      if (res.ok) {
        const data = await res.json();
        setPrograms(data.results || data);
      } else {
        setError('Failed to fetch programs');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  const statusColors: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-800',
    in_review: 'bg-blue-100 text-blue-800',
    active: 'bg-green-100 text-green-800',
    paused: 'bg-yellow-100 text-yellow-800',
    closed: 'bg-red-100 text-red-800',
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Programs</h2>
        <Link href="/dashboard/company/programs/new" className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">
          New Program
        </Link>
      </div>

      {error && <div className="p-4 bg-red-100 text-red-700 rounded-md">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {programs.map(program => (
          <Link key={program.slug} href={`/dashboard/company/programs/${program.slug}`}>
            <div className="bg-white p-6 shadow-sm rounded-lg border border-gray-200 hover:shadow-md transition-shadow cursor-pointer h-full flex flex-col">
              <h3 className="text-lg font-semibold text-gray-900 mb-2 truncate">{program.title}</h3>
              <div className="flex gap-2 mb-4">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${statusColors[program.status] || 'bg-gray-100 text-gray-800'}`}>
                  {program.status.replace('_', ' ')}
                </span>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 capitalize">
                  {program.visibility}
                </span>
              </div>
              <p className="text-sm text-gray-500 mt-auto">
                Created: {new Date(program.created_at).toLocaleDateString()}
              </p>
            </div>
          </Link>
        ))}
        {programs.length === 0 && !error && (
          <div className="col-span-full p-8 text-center bg-gray-50 rounded-lg border border-gray-200 text-gray-500">
            No programs found. Create your first bug bounty program!
          </div>
        )}
      </div>
    </div>
  );
}
