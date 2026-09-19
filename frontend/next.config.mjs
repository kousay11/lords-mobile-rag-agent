/** @type {import('next').NextConfig} */
import { dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const projectRoot = dirname(fileURLToPath(import.meta.url))
const backendInternalUrl = process.env.BACKEND_INTERNAL_URL || 'http://backend:8080'

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/backend-api/:path*',
        destination: `${backendInternalUrl}/:path*`,
      },
    ]
  },
  turbopack: {
    root: projectRoot,
  },
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
      },
    ],
  },
}

export default nextConfig
