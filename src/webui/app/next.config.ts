import type {NextConfig} from 'next';

const nextConfig: NextConfig = {
  /* config options here */
  output: 'export',    // Static export for production
  distDir: 'out',      // Static build directory
  typescript: {
    ignoreBuildErrors: false,  // Enable TypeScript checking in production
  },
  eslint: {
    ignoreDuringBuilds: false, // Enable ESLint checking in production
  },
  images: {
    unoptimized: true,  // Required for static export
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
        hostname: 'www.canada.ca',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'toronto.ca',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'www.toronto.ca',
        port: '',
        pathname: '/**',
      },
    ],
  },
};

export default nextConfig;
