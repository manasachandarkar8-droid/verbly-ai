import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  basePath: "/verbly-ai",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
