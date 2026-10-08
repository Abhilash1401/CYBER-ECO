'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import { useParams } from 'next/navigation';

export default function CompanyReportDetailPage() {
  const params = useParams();
  const reportId = params?.id as string;

  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [updateStatus, setUpdateStatus] = useState('');
  const [updateSeverity, setUpdateSeverity] = useState('');
  const [duplicateId, setDuplicateId] = useState('');
  const [updating, setUpdating] = useState(false);

  const [commentText, setCommentText] = useState('');
  const [commentVisibility, setCommentVisibility] = useState('shared');
  const [submittingComment, setSubmittingComment] = useState(false);

  useEffect(() => {
    fetchReport();
  }, [reportId]);

  const fetchReport = async () => {
    try {
      const res = await apiClient(`/api/v1/reports/manage/${reportId}/`);
      if (!res.ok) throw new Error('Failed to fetch report');
      const data = await res.json();
      setReport(data);
      setUpdateStatus(data.status);
      setUpdateSeverity(data.triaged_severity || data.severity);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setUpdating(true);
    try {
      const payload: any = {
        status: updateStatus,
        triaged_severity: updateSeverity,
      };
      if (updateStatus === 'duplicate' && duplicateId) {
        payload.duplicate_of = duplicateId;
      }
      const res = await apiClient(`/api/v1/reports/manage/${reportId}/`, {
        method: 'PATCH',
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('Failed to update report');
      await fetchReport();
      alert('Updated successfully');
    } catch (err: any) {
      alert(err.message);
    } finally {
      setUpdating(false);
    }
  };

  const handleCommentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    setSubmittingComment(true);
    try {
      const res = await apiClient(`/api/v1/reports/manage/${reportId}/comments/`, {
        method: 'POST',
        body: JSON.stringify({ message: commentText, visibility: commentVisibility })
      });
      if (!res.ok) throw new Error('Failed to add comment');
      setCommentText('');
      await fetchReport();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSubmittingComment(false);
    }
  };

  if (loading) return <div className="p-8">Loading...</div>;
  if (error) return <div className="p-8 text-red-600">Error: {error}</div>;
  if (!report) return null;

  const sharedComments = report.comments?.filter((c: any) => c.visibility === 'shared') || [];
  const internalComments = report.comments?.filter((c: any) => c.visibility === 'internal') || [];

  return (
    <div className="max-w-6xl mx-auto p-8">
      <div className="grid grid-cols-3 gap-8">

        <div className="col-span-2 space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <h1 className="text-2xl font-bold mb-4">{report.title}</h1>
            <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 mb-6">
              <div><strong>Researcher:</strong> {report.hunter_email}</div>
              <div><strong>Asset:</strong> {report.target_asset}</div>
              <div><strong>CVSS:</strong> {report.cvss_vector || 'N/A'}</div>
              <div><strong>Submitted:</strong> {new Date(report.created_at).toLocaleString()}</div>
            </div>

            <h2 className="text-xl font-bold mt-6 mb-2">Description</h2>
            <p className="whitespace-pre-wrap bg-gray-50 p-4 rounded">{report.description}</p>

            <h2 className="text-xl font-bold mt-6 mb-2">Steps to Reproduce</h2>
            <p className="whitespace-pre-wrap bg-gray-50 p-4 rounded">{report.steps_to_reproduce}</p>

            <h2 className="text-xl font-bold mt-6 mb-2">Impact</h2>
            <p className="whitespace-pre-wrap bg-gray-50 p-4 rounded">{report.impact}</p>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">Comments</h2>

            <div className="mb-6 space-y-4">
              <h3 className="font-semibold text-gray-700">Shared Discussion</h3>
              {sharedComments.map((comment: any) => (
                <div key={comment.id} className="bg-blue-50 p-3 rounded text-sm">
                  <div className="font-semibold">{comment.author_email}</div>
                  <div>{comment.message}</div>
                </div>
              ))}
              {sharedComments.length === 0 && <div className="text-sm text-gray-500">No shared comments.</div>}
            </div>

            <div className="mb-6 space-y-4">
              <h3 className="font-semibold text-gray-700">Internal Notes</h3>
              {internalComments.map((comment: any) => (
                <div key={comment.id} className="bg-yellow-50 p-3 rounded text-sm">
                  <div className="font-semibold">{comment.author_email}</div>
                  <div>{comment.message}</div>
                </div>
              ))}
              {internalComments.length === 0 && <div className="text-sm text-gray-500">No internal notes.</div>}
            </div>

            <form onSubmit={handleCommentSubmit} className="space-y-4 border-t pt-4">
              <textarea
                value={commentText}
                onChange={e => setCommentText(e.target.value)}
                placeholder="Add a comment..."
                className="w-full border rounded p-2"
                rows={3}
                required
              />
              <div className="flex justify-between items-center">
                <select
                  value={commentVisibility}
                  onChange={e => setCommentVisibility(e.target.value)}
                  className="border rounded p-2"
                >
                  <option value="shared">Shared (Visible to Researcher)</option>
                  <option value="internal">Internal Note (Hidden)</option>
                </select>
                <button
                  type="submit"
                  disabled={submittingComment}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                >
                  Post Comment
                </button>
              </div>
            </form>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">Triage Actions</h2>
            <form onSubmit={handleUpdate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Status</label>
                <select
                  value={updateStatus}
                  onChange={e => setUpdateStatus(e.target.value)}
                  className="w-full border rounded p-2"
                >
                  <option value="new">New</option>
                  <option value="triaged">Triaged</option>
                  <option value="needs_info">Needs Info</option>
                  <option value="accepted">Accepted</option>
                  <option value="duplicate">Duplicate</option>
                  <option value="rejected">Rejected</option>
                  <option value="informative">Informative</option>
                  <option value="fixed">Fixed</option>
                  <option value="rewarded">Rewarded</option>
                  <option value="closed">Closed</option>
                </select>
              </div>

              {updateStatus === 'duplicate' && (
                <div>
                  <label className="block text-sm font-medium mb-1">Original Report UUID</label>
                  <input
                    type="text"
                    value={duplicateId}
                    onChange={e => setDuplicateId(e.target.value)}
                    className="w-full border rounded p-2"
                    placeholder="Enter original report UUID"
                    required
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-1">Triaged Severity</label>
                <select
                  value={updateSeverity}
                  onChange={e => setUpdateSeverity(e.target.value)}
                  className="w-full border rounded p-2"
                >
                  <option value="informational">Informational</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={updating}
                className="w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                Update Report
              </button>
            </form>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">Evidence</h2>
            <ul className="space-y-2">
              {(report.evidence || []).map((ev: any) => (
                <li key={ev.id} className="text-sm">
                  <a
                    href={`/api/v1/reports/manage/${report.id}/evidence/${ev.id}/download/`}
                    target="_blank"
                    className="text-blue-600 hover:underline"
                  >
                    {ev.filename || `Evidence #${ev.id}`}
                  </a>
                </li>
              ))}
              {(!report.evidence || report.evidence.length === 0) && (
                <li className="text-sm text-gray-500">No evidence attached.</li>
              )}
            </ul>
          </div>

        </div>

      </div>
    </div>
  );
}
