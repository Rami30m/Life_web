/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config) => {
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
      path: false,
      crypto: false,
    };
    
    // Игнорируем предупреждения о модулях
    config.externals = [...(config.externals || []), { canvas: 'canvas' }];
    
    return config;
  },
};

export default nextConfig;
