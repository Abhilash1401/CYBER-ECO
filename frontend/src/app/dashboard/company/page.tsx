'use client';
import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';

export default function OrganizationPage() {
  const [org, setOrg] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Form state
  const [name, setName] = useState('');
  const [website, setWebsite] = useState('');
  const [domains, setDomains] = useState('');

  useEffect(() => {
    fetchOrg();
  }, []);

  const fetchOrg = async () => {
    try {
      const res = await apiClient('/api/v1/companies/me/');
      if (res.ok) {
        const data = await res.json();
        setOrg(data);
      } else if (res.status !== 404) {
        setError('Failed to fetch organization');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const domainsList = domains.split(',').map((d) => d.trim()).filter(Boolean);
      const res = await apiClient('/api/v1/companies/', {
        method: 'POST',
        body: JSON.stringify({ name, website, domains: domainsList }),
      });
      if (res.ok) {
        const data = await res.json();
        setOrg(data);
        setSuccess('Organization created successfully');
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to create organization');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const verifyDns = async (domainId: string) => {
    setError('');
    setSuccess('');
    try {
      const res = await apiClient(`/api/v1/companies/me/domains/${domainId}/verify-dns/`, {
        method: 'POST',
      });
      if (res.ok) {
        setSuccess('DNS verification triggered');
        fetchOrg(); // Refresh
      } else {
        setError('Failed to verify DNS');
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Organization Overview</h2>

      {error && <div className="p-4 bg-red-100 text-red-700 rounded-md">{error}</div>}
      {success && <div className="p-4 bg-green-100 text-green-700 rounded-md">{success}</div>}

      {!org ? (
        <div className="bg-white p-6 shadow-sm rounded-lg border border-gray-200 text-black">
          <h3 className="text-lg font-semibold mb-4">Create Organization</h3>
          <form onSubmit={handleCreateOrg} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Name</label>
              <input required type="text" value={name} onChange={e => setName(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Website</label>
              <input required type="url" value={website} onChange={e => setWebsite(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Domains (comma-separated)</label>
              <input type="text" value={domains} onChange={e => setDomains(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border" />
            </div>
            <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">Create</button>
          </form>
        </div>
      ) : (
        <div className="bg-white p-6 shadow-sm rounded-lg border border-gray-200">
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <p className="text-sm text-gray-500">Name</p>
              <p className="font-semibold text-lg">{org.name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Website</p>
              <p className="font-semibold text-lg">{org.website}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Status</p>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize
                ${org.status === 'verified' ? 'bg-green-100 text-green-800' :
                  org.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                  org.status === 'rejected' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'}`}>
                {org.status || 'pending'}
              </span>
            </div>
          </div>

          <h3 className="text-lg font-semibold mb-4">Domains</h3>
          <ul className="divide-y divide-gray-200 border rounded-md">
            {org.domains?.map((d: any) => (
              <li key={d.id} className="p-4 flex justify-between items-center">
                <div>
                  <p className="font-medium">{d.domain}</p>
                  <p className="text-sm text-gray-500">Status: {d.verified ? 'Verified' : 'Unverified'}</p>
                </div>
                {!d.verified && (
                  <button onClick={() => verifyDns(d.id)} className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                    Verify DNS
                  </button>
                )}
              </li>
            ))}
            {(!org.domains || org.domains.length === 0) && (
              <li className="p-4 text-gray-500 text-sm">No domains added.</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
