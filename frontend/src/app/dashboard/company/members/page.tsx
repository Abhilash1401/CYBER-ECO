'use client';
import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';

export default function MembersPage() {
  const [members, setMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [email, setEmail] = useState('');
  const [role, setRole] = useState('company_viewer');

  useEffect(() => {
    fetchMembers();
  }, []);

  const fetchMembers = async () => {
    try {
      const res = await apiClient('/api/v1/companies/me/members/');
      if (res.ok) {
        const data = await res.json();
        setMembers(data.results || data);
      } else {
        setError('Failed to fetch members');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      const res = await apiClient('/api/v1/companies/me/members/', {
        method: 'POST',
        body: JSON.stringify({ email, role }),
      });
      if (res.ok) {
        setSuccess('Member invited successfully');
        setEmail('');
        fetchMembers();
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to invite member');
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const updateRole = async (id: string, newRole: string) => {
    setError('');
    try {
      const res = await apiClient(`/api/v1/companies/me/members/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ role: newRole }),
      });
      if (res.ok) {
        setSuccess('Role updated');
        fetchMembers();
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to update role');
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const removeMember = async (id: string) => {
    setError('');
    if (!confirm('Are you sure you want to remove this member?')) return;
    try {
      const res = await apiClient(`/api/v1/companies/me/members/${id}/`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setSuccess('Member removed');
        fetchMembers();
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to remove member');
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Team Members</h2>

      {error && <div className="p-4 bg-red-100 text-red-700 rounded-md">{error}</div>}
      {success && <div className="p-4 bg-green-100 text-green-700 rounded-md">{success}</div>}

      <div className="bg-white p-6 shadow-sm rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold mb-4">Invite New Member</h3>
        <form onSubmit={handleInvite} className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700">Email Address</label>
            <input required type="email" value={email} onChange={e => setEmail(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Role</label>
            <select value={role} onChange={e => setRole(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border">
              <option value="company_admin">Admin</option>
              <option value="company_triager">Triager</option>
              <option value="company_viewer">Viewer</option>
            </select>
          </div>
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 h-[42px]">Invite</button>
        </form>
      </div>

      <div className="bg-white shadow-sm rounded-lg border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Joined</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {members.map(member => (
              <tr key={member.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{member.email}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {member.role}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(member.created_at).toLocaleDateString()}</td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <select
                    value={member.role}
                    onChange={(e) => updateRole(member.id, e.target.value)}
                    className="mr-2 text-sm border-gray-300 rounded-md"
                  >
                    <option value="company_admin">Admin</option>
                    <option value="company_triager">Triager</option>
                    <option value="company_viewer">Viewer</option>
                  </select>
                  <button onClick={() => removeMember(member.id)} className="text-red-600 hover:text-red-900">Remove</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
