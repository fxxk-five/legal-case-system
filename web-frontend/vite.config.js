import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import Components from 'unplugin-vue-components/vite'

function toKebabCase(value) {
  return value
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    .replace(/([A-Z])([A-Z][a-z])/g, '$1-$2')
    .toLowerCase()
}

function resolveElementPlusComponent(name) {
  if (!/^El[A-Z]/.test(name)) {
    return undefined
  }

  if (/^ElIcon[A-Z]/.test(name)) {
    return {
      name: name.replace(/^ElIcon/, ''),
      from: '@element-plus/icons-vue',
    }
  }

  const componentName = toKebabCase(name.slice(2))
  const componentOverrides = {
    option: {
      from: 'element-plus/es/components/select/index',
      styles: ['select', 'option'],
    },
    'table-column': {
      from: 'element-plus/es/components/table/index',
      styles: ['table', 'table-column'],
    },
    'tab-pane': {
      from: 'element-plus/es/components/tabs/index',
      styles: ['tabs', 'tab-pane'],
    },
    'timeline-item': {
      from: 'element-plus/es/components/timeline/index',
      styles: ['timeline', 'timeline-item'],
    },
  }
  const override = componentOverrides[componentName]

  return {
    name,
    from: override?.from ?? `element-plus/es/components/${componentName}/index`,
    sideEffects: [
      'element-plus/es/components/base/style/css',
      ...(override?.styles ?? [componentName]).map(
        (styleName) => `element-plus/es/components/${styleName}/style/css`,
      ),
    ],
  }
}

function buildManualChunks(id) {
  if (!id.includes('node_modules')) {
    return undefined
  }
  if (
    id.includes('@vueuse/') ||
    id.includes('dayjs') ||
    id.includes('async-validator') ||
    id.includes('@floating-ui/') ||
    id.includes('@popperjs/') ||
    id.includes('lodash') ||
    id.includes('lodash-unified') ||
    id.includes('memoize-one') ||
    id.includes('normalize-wheel-es') ||
    id.includes('@ctrl/tinycolor') ||
    id.includes('@element-plus/icons-vue')
  ) {
    return 'vendor-ui-deps'
  }
  if (id.includes('element-plus')) {
    return 'vendor-element-plus'
  }
  if (id.includes('lucide-vue-next')) {
    return 'vendor-icons'
  }
  if (id.includes('axios')) {
    return 'vendor-http'
  }
  if (id.includes('/vue/') || id.includes('\\vue\\') || id.includes('vue-router') || id.includes('pinia')) {
    return 'vendor-vue'
  }
  return 'vendor-misc'
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    Components({
      dts: false,
      directives: false,
      resolvers: [resolveElementPlusComponent],
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: buildManualChunks,
      },
    },
  },
})
