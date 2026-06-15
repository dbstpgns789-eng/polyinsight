import type { NextConfig } from "next";

// 백엔드 오리진은 env로 주입(Compose에서 service명, 로컬은 localhost 기본값).
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${BACKEND_ORIGIN}/api/:path*`,
      },
    ]
  },
};

export default nextConfig;
