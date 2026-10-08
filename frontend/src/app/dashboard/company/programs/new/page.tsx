'use client';
import { useState } from 'react';
import { apiClient } from '@/lib/api';
import { useRouter } from 'next/navigation';

export default function NewProgramPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [visibility, setVisibility] = useState('public');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await apiClient('/api/v1/programs/manage/list/', {
        method: 'POST',
        body: JSON.stringify({ title, description, visibility }),
      });

      if (res.ok) {
        const data = await res.json();
        router.push(`/dashboard/company/programs/${data.slug}`);
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to create program');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Create New Program</h2>

      {error && <div className="p-4 bg-red-100 text-red-700 rounded-md">{error}</div>}

      <div className="bg-white p-6 shadow-sm rounded-lg border border-gray-200">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700">Title</label>
            <input required type="text" value={title} onChange={e => setTitle(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Description</label>
            <textarea required value={description} onChange={e => setDescription(e.target.value)} rows={4} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border"></textarea>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Visibility</label>
            <div className="flex gap-4">
              <label className="flex items-center">
                <input type="radio" value="public" checked={visibility === 'public'} onChange={e => setVisibility(e.target.value)} className="mr-2" />
                Public
              </label>
              <label className="flex items-center">
                <input type="radio" value="private" checked={visibility === 'private'} onChange={e => setVisibility(e.target.value)} className="mr-2" />
                Private
              </label>
            </div>
          </div>

          <div className="flex justify-end gap-4">
            <button type="button" onClick={() => router.back()} className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">Cancel</button>
            <button type="submit" disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50">
              {loading ? 'Creating...' : 'Create Program'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
