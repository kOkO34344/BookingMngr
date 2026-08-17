/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Emits .next/standalone with a self-contained server.js and only the
  // node_modules it actually uses, so the runtime image needs no npm install.
  output: "standalone",
};

export default nextConfig;
