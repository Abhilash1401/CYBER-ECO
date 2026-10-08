'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { apiClient } from '@/lib/api';

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [resendEmail, setResendEmail] = useState('');
  const [resendMsg, setResendMsg] = useState<string | null>(null);
  const [resendLoading, setResendLoading] = useState(false);

  useEffect(() => {
    if (!token) return;

    setLoading(true);
    apiClient('/api/v1/auth/verify-email/', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
      .then(async (res) => {
        const data = await res.json();
        if (res.ok) {
          setSuccess(true);
        } else {
          setError(data.token ? data.token[0] : (data.detail || 'Verification link is invalid or expired.'));
        }
      })
      .catch(() => {
        setError('Network error verifying email.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [token]);

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    setResendLoading(true);
    setResendMsg(null);

    try {
      const res = await apiClient('/api/v1/auth/resend-verification/', {
        method: 'POST',
        body: JSON.stringify({ email: resendEmail }),
      });
      const data = await res.json();
      setResendMsg(data.detail || 'If the account exists, a verification link has been sent.');
    } catch {
      setResendMsg('Unable to resend verification link right now.');
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6 dark:bg-gray-900">
      <div className="w-full max-w-md space-y-6 rounded-xl bg-white p-8 shadow-md dark:bg-gray-800 text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Email Verification
        </h2>

        {loading && <p className="text-gray-600 dark:text-gray-400">Verifying your token...</p>}

        {success && (
          <div className="space-y-4">
            <div className="rounded-md bg-green-50 p-4 text-sm text-green-700 dark:bg-green-900/40 dark:text-green-300">
              Your email address has been successfully verified!
            </div>
            <Link
              href="/login"
              className="inline-block w-full rounded-md bg-indigo-600 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
            >
              Proceed to Sign In
            </Link>
          </div>
        )}

        {error && (
          <div className="space-y-4">
            <div className="rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/40 dark:text-red-300">
              {error}
            </div>

            <div className="border-t pt-4 text-left dark:border-gray-700">
              <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                Resend verification email
              </h3>
              {resendMsg && (
                <div className="mt-2 text-xs text-indigo-600 dark:text-indigo-400">
                  {resendMsg}
                </div>
              )}
              <form onSubmit={handleResend} className="mt-3 space-y-3">
                <input
                  type="email"
                  required
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  placeholder="Enter your registered email"
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                />
                <button
                  type="submit"
                  disabled={resendLoading}
                  className="w-full rounded-md bg-gray-900 py-2 text-xs font-semibold text-white hover:bg-gray-800 dark:bg-gray-700 dark:hover:bg-gray-600 disabled:opacity-50"
                >
                  {resendLoading ? 'Sending...' : 'Resend Link'}
                </button>
              </form>
            </div>
          </div>
        )}

        {!token && !success && (
          <div className="space-y-4 text-left">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Please check your inbox and click the verification link sent to your email.
            </p>
            <div className="border-t pt-4 dark:border-gray-700">
              <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                Resend verification link
              </h3>
              {resendMsg && (
                <div className="mt-2 text-xs text-indigo-600 dark:text-indigo-400">
                  {resendMsg}
                </div>
              )}
              <form onSubmit={handleResend} className="mt-3 space-y-3">
                <input
                  type="email"
                  required
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  placeholder="Enter your registered email"
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                />
                <button
                  type="submit"
                  disabled={resendLoading}
                  className="w-full rounded-md bg-gray-900 py-2 text-xs font-semibold text-white hover:bg-gray-800 dark:bg-gray-700 dark:hover:bg-gray-600 disabled:opacity-50"
                >
                  {resendLoading ? 'Sending...' : 'Resend Link'}
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center">Loading...</div>}>
      <VerifyEmailContent />
    </Suspense>
  );
}
