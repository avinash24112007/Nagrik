import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  async rewrites() {
    return [
      {
        source: '/api/Flask_APP/:path*',
        destination: 'https://avinash159-159-nagrik-backend.hf.space/:path*',
      },
    ];
  },
};

export default nextConfig;
