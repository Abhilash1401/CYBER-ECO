'use client';

import { useState, useEffect, Suspense } from 'react';
import { apiClient } from '@/lib/api';
import { useRouter, useSearchParams } from 'next/navigation';

function NewReportForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialProgram = searchParams?.get('program') || '';

  const [programSlug, setProgramSlug] = useState(initialProgram);
  const [scopes, setScopes] = useState<any[]>([]);
  const [loadingScopes, setLoadingScopes] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    title: '',
    vulnerability_type: 'rce',
    target_asset: '',
    severity: 'low',
    cvss_vector: '',
    description: '',
    steps_to_reproduce: '',
    impact: ''
  });

  const fetchScopes = async (slug: string) => {
    if (!slug) return;
    setLoadingScopes(true);
    try {
      const res = await apiClient(`/api/v1/programs/${slug}/`);
      if (res.ok) {
        const data = await res.json();
        setScopes(data.scopes || []);
      } else {
        setScopes([]);
      }
    } catch (err) {
      setScopes([]);
    } finally {
      setLoadingScopes(false);
    }
  };

  useEffect(() => {
    if (programSlug) {
      fetchScopes(programSlug);
    }
  }, [programSlug]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError('');
    setSubmitting(true);
    try {
      const res = await apiClient('/api/v1/reports/', {
        method: 'POST',
        body: JSON.stringify({
          ...formData,
          program: programSlug
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || JSON.stringify(data));
      }

      const report = await res.json();
      router.push(`/reports/${report.id}`);
    } catch (err: any) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <h1 className="text-2xl font-bold mb-6">Submit Vulnerability Report</h1>
      {submitError && <div className="bg-red-50 text-red-600 p-4 rounded mb-6">{submitError}</div>}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700">Program Slug</label>
          <div className="mt-1 flex">
            <input
              type="text"
              value={programSlug}
              onChange={(e) => setProgramSlug(e.target.value)}
              required
              className="border border-gray-300 rounded p-2 flex-1"
              placeholder="e.g. acme-corp"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Target Asset</label>
          <select
            name="target_asset"
            value={formData.target_asset}
            onChange={handleChange}
            required
            className="mt-1 block w-full border border-gray-300 rounded p-2"
          >
            <option value="">Select an asset</option>
            {scopes.map(scope => (
              <option key={scope.id} value={scope.identifier}>{scope.identifier}</option>
            ))}
            {scopes.length === 0 && <option value="other">Other / Custom Asset</option>}
          </select>
          {loadingScopes && <p className="text-sm text-gray-500 mt-1">Loading scopes...</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Title</label>
          <input
            type="text"
            name="title"
            value={formData.title}
            onChange={handleChange}
            required
            className="mt-1 block w-full border border-gray-300 rounded p-2"
            placeholder="Brief description of the issue"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Vulnerability Type</label>
            <select
              name="vulnerability_type"
              value={formData.vulnerability_type}
              onChange={handleChange}
              className="mt-1 block w-full border border-gray-300 rounded p-2"
            >
              <option value="rce">Remote Code Execution (RCE)</option>
              <option value="sqli">SQL Injection</option>
              <option value="xss">Cross-Site Scripting (XSS)</option>
              <option value="ssrf">Server-Side Request Forgery (SSRF)</option>
              <option value="idor">Insecure Direct Object Reference (IDOR)</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Severity</label>
            <select
              name="severity"
              value={formData.severity}
              onChange={handleChange}
              className="mt-1 block w-full border border-gray-300 rounded p-2"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
              <option value="informational">Informational</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">CVSS Vector (Optional)</label>
          <input
            type="text"
            name="cvss_vector"
            value={formData.cvss_vector}
            onChange={handleChange}
            className="mt-1 block w-full border border-gray-300 rounded p-2"
            placeholder="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Description</label>
          <textarea
            name="description"
            value={formData.description}
            onChange={handleChange}
            required
            rows={5}
            className="mt-1 block w-full border border-gray-300 rounded p-2"
            placeholder="Detailed description of the vulnerability..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Steps to Reproduce</label>
          <textarea
            name="steps_to_reproduce"
            value={formData.steps_to_reproduce}
            onChange={handleChange}
            required
            rows={5}
            className="mt-1 block w-full border border-gray-300 rounded p-2"
            placeholder="1. Go to...\n2. Click..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Impact</label>
          <textarea
            name="impact"
            value={formData.impact}
            onChange={handleChange}
            required
            rows={4}
            className="mt-1 block w-full border border-gray-300 rounded p-2"
            placeholder="What is the potential impact?"
          />
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={submitting}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? 'Submitting...' : 'Submit Report'}
          </button>
        </div>
      </form>
    </>
  );
}

export default function NewReportPage() {
  return (
    <div className="max-w-3xl mx-auto p-8">
      <Suspense fallback={<div>Loading...</div>}>
        <NewReportForm />
      </Suspense>
    </div>
  );
}
