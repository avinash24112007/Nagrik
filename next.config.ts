import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  async rewrites() {
    return [
      {
        source: '/api/Flask_APP/:path*',
        destination: 'https://nagrik.onrender.com/:path*',
      },
    ];
  },
};

export default nextConfig;
