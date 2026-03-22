import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.js'],
    coverage: {
      provider: 'v8',
      include: ['src/domain/**', 'src/adapter/**'],
      reporter: ['text', 'text-summary'],
    },
  },
});
