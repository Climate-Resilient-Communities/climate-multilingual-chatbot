import type {NextConfig} from 'next';

const nextConfig: NextConfig = {
  /* config options here */
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'placehold.co',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'www.google.com',
        port: '',
        pathname: '/s2/favicons/**',
      },
      {
        protocol: 'https',
        hostname: 'google.com',
        port: '',
        pathname: '/s2/favicons/**',
      },
      // Common domains that might appear in citations
      {
        protocol: 'https',
        hostname: 'climate.gov',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'epa.gov',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'canada.ca',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'toronto.ca',
        port: '',
        pathname: '/**',
      },
    ],
  },
};

export default nextConfig;
