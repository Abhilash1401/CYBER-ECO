'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import { useParams, useRouter } from 'next/navigation';

export default function ReportDetailPage() {
  const params = useParams();
  const router = useRouter();
  const reportId = params?.id as string;

  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [commentText, setCommentText] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);
  const [withdrawing, setWithdrawing] = useState(false);

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchReport();
  }, [reportId]);

  const fetchReport = async () => {
    try {
      const res = await apiClient(`/api/v1/reports/${reportId}/`);
      if (!res.ok) throw new Error('Failed to fetch report');
      setReport(await res.json());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleWithdraw = async () => {
    if (!confirm('Are you sure you want to withdraw this report?')) return;
    setWithdrawing(true);
    try {
      const res = await apiClient(`/api/v1/reports/${reportId}/`, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'withdrawn' })
      });
      if (!res.ok) throw new Error('Failed to withdraw');
      await fetchReport();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setWithdrawing(false);
    }
  };

  const handleCommentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    setSubmittingComment(true);
    try {
      const res = await apiClient(`/api/v1/reports/${reportId}/comments/`, {
        method: 'POST',
        body: JSON.stringify({ message: commentText })
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

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      const res = await apiClient(`/api/v1/reports/${reportId}/evidence/upload/`, {
        method: 'POST',
        body: formData,
        headers: {
          // Do not set Content-Type here, let browser set it with boundary
        }
      });
      if (!res.ok) throw new Error('Upload failed');
      setUploadFile(null);
      await fetchReport();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setUploading(false);
    }
  };

  if (loading) return <div className="p-8">Loading...</div>;
  if (error) return <div className="p-8 text-red-600">Error: {error}</div>;
  if (!report) return null;

  return (
    <div className="max-w-5xl mx-auto p-8">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">{report.title}</h1>
          <div className="flex space-x-4 text-sm text-gray-500">
            <span>Status: <strong className="uppercase">{report.status}</strong></span>
            <span>Severity: <strong className="uppercase">{report.severity}</strong></span>
            <span>Target: {report.target_asset}</span>
          </div>
        </div>
        {report.status !== 'withdrawn' && report.status !== 'closed' && (
          <button
            onClick={handleWithdraw}
            disabled={withdrawing}
            className="bg-red-100 text-red-700 px-4 py-2 rounded hover:bg-red-200"
          >
            {withdrawing ? '...' : 'Withdraw Report'}
          </button>
        )}
      </div>

      <div className="grid grid-cols-3 gap-8">
        <div className="col-span-2 space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">Description</h2>
            <p className="whitespace-pre-wrap">{report.description}</p>

            <h2 className="text-xl font-bold mt-6 mb-4">Steps to Reproduce</h2>
            <p className="whitespace-pre-wrap">{report.steps_to_reproduce}</p>

            <h2 className="text-xl font-bold mt-6 mb-4">Impact</h2>
            <p className="whitespace-pre-wrap">{report.impact}</p>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">Discussion</h2>
            <div className="space-y-4 mb-6">
              {(report.comments || []).map((comment: any) => (
                <div key={comment.id} className="bg-gray-50 p-4 rounded border">
                  <div className="text-sm font-semibold mb-1">{comment.author_email || 'User'}</div>
                  <p className="text-sm">{comment.message}</p>
                  <div className="text-xs text-gray-400 mt-2">{new Date(comment.created_at).toLocaleString()}</div>
                </div>
              ))}
            </div>
            <form onSubmit={handleCommentSubmit} className="flex flex-col gap-2">
              <textarea
                value={commentText}
                onChange={e => setCommentText(e.target.value)}
                placeholder="Add a comment..."
                className="border rounded p-2"
                rows={3}
                required
              />
              <button
                type="submit"
                disabled={submittingComment}
                className="bg-blue-600 text-white px-4 py-2 rounded self-end hover:bg-blue-700"
              >
                Send
              </button>
            </form>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">Evidence</h2>
            <ul className="space-y-2 mb-4">
              {(report.evidence || []).map((ev: any) => (
                <li key={ev.id} className="text-sm">
                  <a
                    href={`/api/v1/reports/${report.id}/evidence/${ev.id}/download/`}
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

            <form onSubmit={handleUpload} className="border-t pt-4">
              <input
                type="file"
                onChange={e => setUploadFile(e.target.files ? e.target.files[0] : null)}
                className="text-sm mb-2"
              />
              <button
                type="submit"
                disabled={!uploadFile || uploading}
                className="bg-gray-200 text-gray-800 px-4 py-2 rounded text-sm w-full hover:bg-gray-300 disabled:opacity-50"
              >
                {uploading ? 'Uploading...' : 'Upload Evidence'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
