import type { NextConfig } from "next";

// 백엔드 오리진은 env로 주입(Compose에서 service명, 로컬은 localhost 기본값).
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  // 업로드 프록시 본문 한도. 기본 10MB가 backend 허용(50MB)보다 작아, 10MB 넘는 논문이
  // /api/deck/upload 프록시(rewrites)에서 잘려 backend 도달 전 ECONNRESET→500이 났다.
  // backend 50MB + 멀티파트 오버헤드 여유로 60MB. 실제 상한은 backend가 친절 메시지로 강제.
  experimental: {
    proxyClientMaxBodySize: '60mb',        // rewrites 프록시(우리 /api/* → backend) 본문 한도(기본 10MB)
    // 동기 AI 편집(nlpatch)은 Sonnet 전체덱 편집을 요청 안에서 기다린다. 기본 30초(30000ms)로는
    // 큰 덱 편집이 넘겨 web→backend 프록시가 ECONNRESET → 프론트 실패 + backend는 완료·크레딧 차감.
    // backend AUTHOR_TIMEOUT_S(600s)와 맞춰 620초. backend가 실제 상한, 프록시가 먼저 안 끊게.
    proxyTimeout: 620_000,
  },
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
