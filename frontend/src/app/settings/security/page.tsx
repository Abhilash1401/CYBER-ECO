'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';

interface UserInfo {
  id: string;
  email: string;
  role: string;
  is_verified: boolean;
  mfa_enabled: boolean;
  requires_mfa: boolean;
}

export default function SecuritySettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  // Password Change State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [pwMsg, setPwMsg] = useState<string | null>(null);
  const [pwErr, setPwErr] = useState<string | null>(null);
  const [pwLoading, setPwLoading] = useState(false);

  // MFA Setup State
  const [mfaData, setMfaData] = useState<{
    secret: string;
    qr_code: string;
    recovery_codes: string[];
  } | null>(null);
  const [totpCode, setTotpCode] = useState('');
  const [mfaMsg, setMfaMsg] = useState<string | null>(null);
  const [mfaErr, setMfaErr] = useState<string | null>(null);
  const [mfaLoading, setMfaLoading] = useState(false);

  const fetchUser = async () => {
    try {
      const res = await apiClient('/api/v1/auth/me/');
      if (res.status === 401) {
        router.push('/login');
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwLoading(true);
    setPwMsg(null);
    setPwErr(null);

    try {
      const res = await apiClient('/api/v1/auth/password/change/', {
        method: 'POST',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setPwMsg(data.detail || 'Password changed successfully. All other sessions have been logged out.');
        setCurrentPassword('');
        setNewPassword('');
      } else {
        setPwErr(data.new_password ? data.new_password[0] : (data.detail || 'Password change failed.'));
      }
    } catch {
      setPwErr('Error updating password.');
    } finally {
      setPwLoading(false);
    }
  };

  const handleStartMfaSetup = async () => {
    setMfaLoading(true);
    setMfaErr(null);
    setMfaMsg(null);

    try {
      const res = await apiClient('/api/v1/auth/mfa/setup/', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setMfaData(data);
      } else {
        const data = await res.json();
        setMfaErr(data.detail || 'Unable to start MFA setup.');
      }
    } catch {
      setMfaErr('Network error initiating MFA.');
    } finally {
      setMfaLoading(false);
    }
  };

  const handleConfirmMfa = async (e: React.FormEvent) => {
    e.preventDefault();
    setMfaLoading(true);
    setMfaErr(null);

    try {
      const res = await apiClient('/api/v1/auth/mfa/confirm/', {
        method: 'POST',
        body: JSON.stringify({ code: totpCode }),
      });
      const data = await res.json();
      if (res.ok) {
        setMfaMsg('Two-factor authentication successfully enabled!');
        setMfaData(null);
        fetchUser();
      } else {
        setMfaErr(data.detail || 'Invalid TOTP code.');
      }
    } catch {
      setMfaErr('Error verifying MFA code.');
    } finally {
      setMfaLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center">Loading security settings...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8 dark:bg-gray-900">
      <div className="mx-auto max-w-2xl space-y-8">
        <div className="flex items-center justify-between border-b pb-4 dark:border-gray-800">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Security & MFA</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Manage your credentials and two-factor authentication
            </p>
          </div>
          <div>
            <Link href="/settings/profile" className="text-sm font-semibold text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">
              &larr; Profile Settings
            </Link>
          </div>
        </div>

        {user?.requires_mfa && !user?.mfa_enabled && (
          <div className="rounded-md bg-amber-50 p-4 border border-amber-300 text-sm text-amber-800 dark:bg-amber-950/40 dark:border-amber-800 dark:text-amber-300">
            <strong>Mandatory MFA Required:</strong> Your role ({user.role}) requires two-factor authentication before you can access the platform features.
          </div>
        )}

        {/* --- Two-Factor Authentication Section --- */}
        <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Two-Factor Authentication (TOTP)
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Protect your account with an Authenticator app (e.g., Google Authenticator, Authy, 1Password).
          </p>

          {mfaMsg && (
            <div className="rounded-md bg-green-50 p-4 text-sm text-green-700 dark:bg-green-900/40 dark:text-green-300">
              {mfaMsg}
            </div>
          )}
          {mfaErr && (
            <div className="rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/40 dark:text-red-300">
              {mfaErr}
            </div>
          )}

          {user?.mfa_enabled ? (
            <div className="flex items-center space-x-2 text-sm text-green-600 dark:text-green-400 font-medium">
              <span>&#10003; Two-Factor Authentication is currently enabled on your account.</span>
            </div>
          ) : (
            <div>
              {!mfaData ? (
                <button
                  type="button"
                  onClick={handleStartMfaSetup}
                  disabled={mfaLoading}
                  className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
                >
                  {mfaLoading ? 'Configuring...' : 'Set Up Two-Factor Authentication'}
                </button>
              ) : (
                <div className="mt-4 space-y-6 border-t pt-4 dark:border-gray-700">
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                      1. Scan this QR Code with your Authenticator app:
                    </p>
                    <div className="flex justify-center p-4 bg-white rounded-lg border w-fit">
                      <Image
                        src={mfaData.qr_code}
                        alt="TOTP QR Code"
                        width={192}
                        height={192}
                        unoptimized
                        className="h-48 w-48"
                      />
                    </div>
                    <p className="text-xs text-gray-500">
                      Or manually enter secret key:{' '}
                      <code className="bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded font-mono font-bold">
                        {mfaData.secret}
                      </code>
                    </p>
                  </div>

                  <div className="space-y-2">
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                      2. Save these one-time recovery codes securely:
                    </p>
                    <div className="grid grid-cols-2 gap-2 bg-gray-50 p-3 rounded-md font-mono text-xs dark:bg-gray-900 border dark:border-gray-700">
                      {mfaData.recovery_codes.map((code, idx) => (
                        <div key={idx} className="text-gray-700 dark:text-gray-300">
                          {code}
                        </div>
                      ))}
                    </div>
                  </div>

                  <form onSubmit={handleConfirmMfa} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        3. Enter the 6-digit verification code from your app:
                      </label>
                      <input
                        type="text"
                        maxLength={6}
                        required
                        value={totpCode}
                        onChange={(e) => setTotpCode(e.target.value)}
                        placeholder="123456"
                        className="mt-1 block w-48 rounded-md border border-gray-300 px-3 py-2 text-center text-lg tracking-widest shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={mfaLoading}
                      className="rounded-md bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-500 disabled:opacity-50"
                    >
                      {mfaLoading ? 'Verifying...' : 'Verify and Activate MFA'}
                    </button>
                  </form>
                </div>
              )}
            </div>
          )}
        </div>

        {/* --- Password Change Section --- */}
        <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Change Password</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Changing your password will immediately terminate all your other active sessions.
          </p>

          {pwMsg && (
            <div className="rounded-md bg-green-50 p-4 text-sm text-green-700 dark:bg-green-900/40 dark:text-green-300">
              {pwMsg}
            </div>
          )}
          {pwErr && (
            <div className="rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/40 dark:text-red-300">
              {pwErr}
            </div>
          )}

          <form onSubmit={handleChangePassword} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Current Password
              </label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                New Password
              </label>
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-white"
              />
            </div>

            <button
              type="submit"
              disabled={pwLoading}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
            >
              {pwLoading ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
