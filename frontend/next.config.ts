import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  allowedDevOrigins: ['127.0.0.1', 'localhost', '192.168.43.125'],
  turbopack: {
    root: process.cwd(),
  },
  experimental: {
    optimizePackageImports: ['recharts', 'lucide-react'],
  },
  async rewrites() {
    // 统一在生产/开发环境启用 /api 反向代理。
    // 原实现仅 development 生效、并假设生产有 Nginx 反代；但本项目生产由前端容器直接暴露 3000，
    // 没有 Nginx，导致客户端相对路径 /api/* 打到 Next 自身 → 404 → 所有功能不可用。
    const isDev = process.env.NODE_ENV === 'development';
    // 开发环境后端跑在宿主机（强制 IPv4，避免 localhost→::1 的 IPv6 超时）；
    // 生产环境在容器内，必须使用 compose 服务名 backend。
    const backend = isDev ? 'http://127.0.0.1:8888' : 'http://backend:8888';
    return [
      {
        source: '/api-docs',
        destination: `${backend}/api/docs/`,
      },
      {
        source: '/api-docs/:path*',
        destination: `${backend}/api/docs/`,
      },
      {
        // app/api/market_indices/route.ts 等既有 Route Handler 优先级高于 rewrites，
        // 因此本规则只接管其余 /api/* 业务接口。
        source: '/api/:path*',
        destination: `${backend}/api/:path*`,
      },
      {
        // Swagger UI 的 /static/* 仅后端 Flask 使用
        source: '/static/:path*',
        destination: `${backend}/static/:path*`,
      },
    ];
  },

  async headers() {
    // 覆盖 Werkzeug 透传的 Connection:close，让浏览器复用 TCP 连接，
    // 避免每次 fetch /api/* 都重新建连（开发期曾导致 16s 冷启动）。
    // 生产环境同样需要，否则 SSE 流式响应易被中断。
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Connection', value: 'keep-alive' },
        ],
      },
    ];
  },
};

export default nextConfig;
