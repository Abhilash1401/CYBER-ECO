import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // API calls from server components use the Docker network
  // Client-side calls use NEXT_PUBLIC_API_URL from env
  output: 'standalone',
  allowedDevOrigins: ['127.0.0.1'],
};

export default nextConfig;
