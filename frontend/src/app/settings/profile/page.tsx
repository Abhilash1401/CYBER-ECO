'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';

interface UserProfile {
  username: string;
  bio: string;
  website: string;
  twitter_handle: string;
  github_handle: string;
  is_public: boolean;
}

export default function ProfileSettingsPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile>({
    username: '',
    bio: '',
    website: '',
    twitter_handle: '',
    github_handle: '',
    is_public: true,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient('/api/v1/profiles/me/')
      .then(async (res) => {
        if (res.status === 401) {
          router.push('/login');
          return;
        }
        if (res.status === 403) {
          const data = await res.json();
          if (data.detail && data.detail.includes('MFA')) {
            router.push('/settings/security');
            return;
          }
        }
        if (res.ok) {
          const data = await res.json();
          setProfile({
            username: data.username || '',
            bio: data.bio || '',
            website: data.website || '',
            twitter_handle: data.twitter_handle || '',
            github_handle: data.github_handle || '',
            is_public: data.is_public ?? true,
          });
        }
      })
      .catch(() => setError('Failed to load profile data.'))
      .finally(() => setLoading(false));
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);

    try {
      const res = await apiClient('/api/v1/profiles/me/', {
        method: 'PATCH',
        body: JSON.stringify(profile),
      });
      const data = await res.json();

      if (res.ok) {
        setMessage('Profile updated successfully.');
      } else {
        setError(data.username ? data.username[0] : (data.detail || 'Failed to update profile.'));
      }
    } catch {
      setError('An error occurred updating profile.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-600 dark:text-gray-400">Loading settings...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8 dark:bg-gray-900">
      <div className="mx-auto max-w-2xl space-y-8">
        <div className="flex items-center justify-between border-b pb-4 dark:border-gray-800">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Profile Settings</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Manage your public researcher persona
            </p>
          </div>
          <div className="space-x-4 text-sm font-semibold">
            <Link href="/settings/security" className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">
              Security & MFA &rarr;
            </Link>
          </div>
        </div>

        {message && (
          <div className="rounded-md bg-green-50 p-4 text-sm text-green-700 dark:bg-green-900/40 dark:text-green-300">
            {message}
          </div>
        )}

        {error && (
          <div className="rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/40 dark:text-red-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6 rounded-xl bg-white p-6 shadow-sm dark:bg-gray-800">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Username
            </label>
            <input
              type="text"
              required
              value={profile.username}
              onChange={(e) => setProfile({ ...profile, username: e.target.value })}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Bio
            </label>
            <textarea
              rows={4}
              value={profile.bio}
              onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
              placeholder="Tell others about your security background..."
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Website
              </label>
              <input
                type="url"
                value={profile.website}
                onChange={(e) => setProfile({ ...profile, website: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                placeholder="https://yourdomain.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                GitHub Handle
              </label>
              <input
                type="text"
                value={profile.github_handle}
                onChange={(e) => setProfile({ ...profile, github_handle: e.target.value })}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                placeholder="octocat"
              />
            </div>
          </div>

          <div className="flex items-center">
            <input
              id="is_public"
              type="checkbox"
              checked={profile.is_public}
              onChange={(e) => setProfile({ ...profile, is_public: e.target.checked })}
              className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 dark:border-gray-700 dark:bg-gray-900"
            />
            <label htmlFor="is_public" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
              Make my profile publicly visible
            </label>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </form>
      </div>
    </div>
  );
}
