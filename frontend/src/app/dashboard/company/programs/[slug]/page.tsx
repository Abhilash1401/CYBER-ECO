'use client';
import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { useParams, useRouter } from 'next/navigation';

export default function ProgramDetailPage() {
  const params = useParams();
  const slug = params.slug as string;
  const router = useRouter();

  const [activeTab, setActiveTab] = useState('details');
  const [program, setProgram] = useState<any>(null);
  const [scopes, setScopes] = useState<any[]>([]);
  const [rewards, setRewards] = useState<any[]>([]);
  const [invites, setInvites] = useState<any[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Forms state
  const [detailsForm, setDetailsForm] = useState({ title: '', description: '', rules_of_engagement: '', safe_harbor: '', disclosure_policy: '', visibility: 'public' });
  const [scopeForm, setScopeForm] = useState({ asset_type: 'domain', asset_value: '', in_scope: true });
  const [rewardForm, setRewardForm] = useState({ severity: 'low', min_amount: 0, max_amount: 0, currency: 'USD' });
  const [inviteEmail, setInviteEmail] = useState('');

  useEffect(() => {
    fetchProgram();
  }, [slug]);

  useEffect(() => {
    if (activeTab === 'scope') fetchScopes();
    if (activeTab === 'rewards') fetchRewards();
    if (activeTab === 'invites') fetchInvites();
  }, [activeTab]);

  const fetchProgram = async () => {
    try {
      const res = await apiClient(`/api/v1/programs/manage/${slug}/`);
      if (res.ok) {
        const data = await res.json();
        setProgram(data);
        setDetailsForm({
          title: data.title || '',
          description: data.description || '',
          rules_of_engagement: data.rules_of_engagement || '',
          safe_harbor: data.safe_harbor || '',
          disclosure_policy: data.disclosure_policy || '',
          visibility: data.visibility || 'public',
        });
      } else {
        setError('Failed to fetch program');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchScopes = async () => {
    const res = await apiClient(`/api/v1/programs/manage/${slug}/scopes/`);
    if (res.ok) {
      const data = await res.json();
      setScopes(data.results || data);
    }
  };

  const fetchRewards = async () => {
    const res = await apiClient(`/api/v1/programs/manage/${slug}/rewards/`);
    if (res.ok) {
      const data = await res.json();
      setRewards(data.results || data);
    }
  };

  const fetchInvites = async () => {
    const res = await apiClient(`/api/v1/programs/manage/${slug}/invites/`);
    if (res.ok) {
      const data = await res.json();
      setInvites(data.results || data);
    }
  };

  const saveDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      const res = await apiClient(`/api/v1/programs/manage/${slug}/`, {
        method: 'PATCH',
        body: JSON.stringify(detailsForm),
      });
      if (res.ok) {
        setSuccess('Program updated');
        fetchProgram();
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to update program');
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const transitionStatus = async (status: string) => {
    setError('');
    setSuccess('');
    try {
      let url = `/api/v1/programs/manage/${slug}/transition-status/`;
      let payload = { status };

      if (status === 'in_review') {
        url = `/api/v1/programs/manage/${slug}/submit-review/`;
        payload = {} as any;
      }

      const res = await apiClient(url, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        setSuccess('Status updated');
        fetchProgram();
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to update status');
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const addScope = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await apiClient(`/api/v1/programs/manage/${slug}/scopes/`, {
        method: 'POST',
        body: JSON.stringify(scopeForm),
      });
      if (res.ok) {
        setSuccess('Scope added');
        setScopeForm({ ...scopeForm, asset_value: '' });
        fetchScopes();
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to add scope');
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const deleteScope = async (id: string) => {
    const res = await apiClient(`/api/v1/programs/manage/${slug}/scopes/${id}/`, { method: 'DELETE' });
    if (res.ok) { fetchScopes(); }
  };

  const addReward = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await apiClient(`/api/v1/programs/manage/${slug}/rewards/`, {
        method: 'POST',
        body: JSON.stringify(rewardForm),
      });
      if (res.ok) {
        setSuccess('Reward added');
        fetchRewards();
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to add reward');
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const deleteReward = async (id: string) => {
    const res = await apiClient(`/api/v1/programs/manage/${slug}/rewards/${id}/`, { method: 'DELETE' });
    if (res.ok) { fetchRewards(); }
  };

  const inviteHunter = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await apiClient(`/api/v1/programs/manage/${slug}/invites/`, {
        method: 'POST',
        body: JSON.stringify({ email: inviteEmail }),
      });
      if (res.ok) {
        setSuccess('Invite sent');
        setInviteEmail('');
        fetchInvites();
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to send invite');
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const deleteInvite = async (id: string) => {
    const res = await apiClient(`/api/v1/programs/manage/${slug}/invites/${id}/`, { method: 'DELETE' });
    if (res.ok) { fetchInvites(); }
  };

  if (loading) return <div>Loading...</div>;
  if (!program) return <div>Program not found</div>;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{program.title}</h2>
          <div className="flex gap-2 mt-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 capitalize">
              {program.status.replace('_', ' ')}
            </span>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 capitalize">
              {program.visibility}
            </span>
          </div>
        </div>

        <div className="flex gap-2">
          {program.status === 'draft' && (
            <button onClick={() => transitionStatus('in_review')} className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">Submit for Review</button>
          )}
          {program.status === 'active' && (
            <>
              <button onClick={() => transitionStatus('paused')} className="bg-yellow-500 text-white px-4 py-2 rounded-md hover:bg-yellow-600">Pause</button>
              <button onClick={() => transitionStatus('closed')} className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700">Close</button>
            </>
          )}
          {program.status === 'paused' && (
            <>
              <button onClick={() => transitionStatus('active')} className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700">Resume</button>
              <button onClick={() => transitionStatus('closed')} className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700">Close</button>
            </>
          )}
        </div>
      </div>

      {error && <div className="p-4 bg-red-100 text-red-700 rounded-md">{error}</div>}
      {success && <div className="p-4 bg-green-100 text-green-700 rounded-md">{success}</div>}

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {['details', 'scope', 'rewards', ...(program.visibility === 'private' ? ['invites'] : [])].map(tab => (
            <button
              key={tab}
              onClick={() => { setError(''); setSuccess(''); setActiveTab(tab); }}
              className={`${activeTab === tab ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm capitalize`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      <div className="bg-white p-6 shadow-sm rounded-lg border border-gray-200">
        {activeTab === 'details' && (
          <form onSubmit={saveDetails} className="space-y-4">
            <div><label className="block text-sm font-medium">Title</label><input type="text" value={detailsForm.title} onChange={e => setDetailsForm({...detailsForm, title: e.target.value})} className="mt-1 block w-full border rounded-md p-2" /></div>
            <div><label className="block text-sm font-medium">Description</label><textarea rows={3} value={detailsForm.description} onChange={e => setDetailsForm({...detailsForm, description: e.target.value})} className="mt-1 block w-full border rounded-md p-2" /></div>
            <div><label className="block text-sm font-medium">Rules of Engagement</label><textarea rows={3} value={detailsForm.rules_of_engagement} onChange={e => setDetailsForm({...detailsForm, rules_of_engagement: e.target.value})} className="mt-1 block w-full border rounded-md p-2" /></div>
            <div><label className="block text-sm font-medium">Safe Harbor</label><textarea rows={3} value={detailsForm.safe_harbor} onChange={e => setDetailsForm({...detailsForm, safe_harbor: e.target.value})} className="mt-1 block w-full border rounded-md p-2" /></div>
            <div><label className="block text-sm font-medium">Disclosure Policy</label><textarea rows={3} value={detailsForm.disclosure_policy} onChange={e => setDetailsForm({...detailsForm, disclosure_policy: e.target.value})} className="mt-1 block w-full border rounded-md p-2" /></div>
            <div>
              <label className="block text-sm font-medium">Visibility</label>
              <select value={detailsForm.visibility} onChange={e => setDetailsForm({...detailsForm, visibility: e.target.value})} className="mt-1 block w-full border rounded-md p-2">
                <option value="public">Public</option>
                <option value="private">Private</option>
              </select>
            </div>
            <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">Save Changes</button>
          </form>
        )}

        {activeTab === 'scope' && (
          <div className="space-y-6">
            <form onSubmit={addScope} className="flex gap-4 items-end border-b pb-6">
              <div><label className="block text-sm font-medium">Type</label>
                <select value={scopeForm.asset_type} onChange={e => setScopeForm({...scopeForm, asset_type: e.target.value})} className="mt-1 block w-full border rounded-md p-2">
                  <option value="domain">Domain</option><option value="url">URL</option><option value="ip_cidr">IP CIDR</option><option value="mobile_app">Mobile App</option><option value="api_endpoint">API Endpoint</option><option value="other">Other</option>
                </select>
              </div>
              <div className="flex-1"><label className="block text-sm font-medium">Value</label><input required type="text" value={scopeForm.asset_value} onChange={e => setScopeForm({...scopeForm, asset_value: e.target.value})} className="mt-1 block w-full border rounded-md p-2" /></div>
              <div className="flex items-center h-[42px]">
                <label className="flex items-center"><input type="checkbox" checked={scopeForm.in_scope} onChange={e => setScopeForm({...scopeForm, in_scope: e.target.checked})} className="mr-2" /> In Scope</label>
              </div>
              <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 h-[42px]">Add</button>
            </form>
            <ul className="divide-y">
              {scopes.map(s => (
                <li key={s.id} className="py-4 flex justify-between">
                  <div>
                    <span className={`inline-block mr-2 px-2 py-1 text-xs rounded ${s.in_scope ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>{s.in_scope ? 'In Scope' : 'Out of Scope'}</span>
                    <span className="font-mono">{s.asset_value}</span> <span className="text-gray-500 text-sm">({s.asset_type})</span>
                  </div>
                  <button onClick={() => deleteScope(s.id)} className="text-red-600">Delete</button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {activeTab === 'rewards' && (
          <div className="space-y-6">
            <form onSubmit={addReward} className="flex gap-4 items-end border-b pb-6">
              <div><label className="block text-sm font-medium">Severity</label>
                <select value={rewardForm.severity} onChange={e => setRewardForm({...rewardForm, severity: e.target.value})} className="mt-1 block w-full border rounded-md p-2">
                  <option value="informational">Informational</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option>
                </select>
              </div>
              <div><label className="block text-sm font-medium">Min ($)</label><input type="number" required min="0" value={rewardForm.min_amount} onChange={e => setRewardForm({...rewardForm, min_amount: Number(e.target.value)})} className="mt-1 block w-full border rounded-md p-2" /></div>
              <div><label className="block text-sm font-medium">Max ($)</label><input type="number" required min="0" value={rewardForm.max_amount} onChange={e => setRewardForm({...rewardForm, max_amount: Number(e.target.value)})} className="mt-1 block w-full border rounded-md p-2" /></div>
              <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 h-[42px]">Add</button>
            </form>
            <ul className="divide-y">
              {rewards.map(r => (
                <li key={r.id} className="py-4 flex justify-between">
                  <div className="capitalize font-medium">{r.severity}: ${r.min_amount} - ${r.max_amount}</div>
                  <button onClick={() => deleteReward(r.id)} className="text-red-600">Delete</button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {activeTab === 'invites' && program.visibility === 'private' && (
          <div className="space-y-6">
            <form onSubmit={inviteHunter} className="flex gap-4 items-end border-b pb-6">
              <div className="flex-1"><label className="block text-sm font-medium">Hunter Email</label><input type="email" required value={inviteEmail} onChange={e => setInviteEmail(e.target.value)} className="mt-1 block w-full border rounded-md p-2" /></div>
              <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 h-[42px]">Send Invite</button>
            </form>
            <ul className="divide-y">
              {invites.map(i => (
                <li key={i.id} className="py-4 flex justify-between">
                  <div>{i.email} <span className="text-sm text-gray-500 ml-2">({i.status})</span></div>
                  <button onClick={() => deleteInvite(i.id)} className="text-red-600">Delete</button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
