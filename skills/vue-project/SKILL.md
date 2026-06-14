---
name: vue-project
description: Scaffolds and develops Vue 3 + Vite web applications with TailwindCSS and pnpm. Use ONLY when users explicitly request Vue, Vite, or vue3; otherwise default to react-project. Don't use for React projects, mobile H5 pages, or backend-only services.
---
# Vue 项目开发规范

## 核心约束

### 技术栈限制
- **Vue 3 Composition API**，强制使用 `<script setup lang="ts">` 写法
- **Vite 5** 作为打包工具（dev/build 都走 vite），禁止切回 webpack
- **禁止引入任何第三方 UI 组件库**（Element Plus / Ant Design Vue / Naive UI / Vuetify / PrimeVue / Arco Design Vue / Vant 等），也**禁止引入任何第三方图标库**（@element-plus/icons-vue / @ant-design/icons-vue / lucide-vue-next / @heroicons/vue / vue-feather 等）；按钮 / 输入框 / 弹窗 / 表格 / 图标等组件**一律基于原生 HTML 元素 + TailwindCSS 自行实现**，图标统一用**内联 SVG**
- **TailwindCSS 3** 作为原子类样式，业务样式禁止使用 scss/sass
- **pnpm** 作为包管理器，禁止 yarn/npm 产生 lock 污染
- **禁止 esbuild 直接调用 / 任何二进制依赖**
- **路由仅可使用 hash 模式**（createWebHashHistory），多页面时才引入 vue-router
- **Meoo Cloud 云服务** 作为项目后端（@supabase/supabase-js 已预置）

### 硬端口约束
- **dev server 端口固定 3015**（vite.config.ts 已设 `server.port=3015` + `strictPort:true`）
- 禁止改端口，沙箱只开放一个代理端口，改了会导致 Live Preview 预览失败

### 产物约束（OSS 部署契约）
- 产物落 `dist/index.html` + `dist/assets/*`
- HTML 引用必须是相对路径（`base: './'` 已配置），禁止外链 CDN 的 js/css
- 图片/图标/字体 **≤1MB 走内联 dataURL**（vite.config assetsInlineLimit 已配置）
- 这些字段是部署和预览的强制契约，**禁止改动 vite.config 的 base / outDir / assetsDir / assetsInlineLimit**

### 代码风格
- 使用 **2 个空格**缩进
- 业务样式优先 TailwindCSS，组件内局部样式用 `<style scoped>`
- **不要添加任何注释**，除非用户明确要求
- **不要使用 emoji 代替 svg/icon**：图标全部用**内联 SVG** 自己实现（可参考 lucide / heroicons 的开源 SVG 拷贝路径数据，但不要 npm 安装它们的包），统一封装到 `src/components/icons/` 下复用

### 文件管理
- 单文件严格不超过 **260 行**，超过需拆分组件/composable
- 组件放 `src/components/`，页面放 `src/views/`，composable 放 `src/composables/`
- 生成文件按功能模块组织，目录扁平化
- 修改文件时返回完整内容，禁止省略占位符
- 禁止创建任何二进制文件或 base64 编码资源

### 项目结构示例
```
src/
  components/         # 通用组件
    AppHeader.vue
  views/              # 页面级组件
    Home.vue
    Dashboard.vue
  composables/        # Composition API 封装
    useAuth.ts
  stores/             # Pinia store
    user.ts
  router/             # vue-router 配置
    index.ts
  styles/
    tailwind.css
  main.ts
  App.vue
```

## Vite 配置规范

### 不可修改字段
以下字段由部署契约强制，**禁止修改**：
```ts
server.port = 3015
server.strictPort = true
server.host = '0.0.0.0'
base = './'
build.outDir = 'dist'
build.assetsDir = 'assets'
build.assetsInlineLimit = 1024 * 1024
```

### 可扩展
- plugins：可追加 vue-jsx / legacy 等
- resolve.alias：可追加 `@` 别名
- rollupOptions.external：按需

## Package.json 规范

### 必须的脚本命令
```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview",
    "typecheck": "vue-tsc --noEmit"
  }
}
```

- `pnpm run dev` 启动开发服务器（3015）
- `pnpm run build` 构建，输出到 dist

## 开发注意事项

### 路由实现 (MANDATORY)
- 所有导航必须先实现路由再加 UI
- 每个 tab/页面都要有 Route 定义
- 菜单宽度固定，不被 tab 挤压
- 示例：
```ts
import { createRouter, createWebHashHistory } from 'vue-router';

export default createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: () => import('@/views/Home.vue') },
    { path: '/dashboard', component: () => import('@/views/Dashboard.vue') },
  ],
});
```
- 所有模式支持 URL 参数切换（`?theme=dark&lang=en`，前提是用户要求）
- 禁止使用 Tailwind 未定义的颜色

### 依赖管理
- 需要的依赖统一加到 package.json
- 避免 `pnpm i <pkg>` 单独安装
- 更新 package.json 后执行 `pnpm install`
- **dependencies 里严禁出现任何 UI 组件库 / 图标库 npm 包**：`element-plus` / `@element-plus/icons-vue` / `ant-design-vue` / `@ant-design/icons-vue` / `naive-ui` / `vuetify` / `primevue` / `@arco-design/web-vue` / `vant` / `lucide-vue-next` / `@heroicons/vue` / `vue-feather` 等均不允许；同时不要引入 `unplugin-vue-components` + `ElementPlusResolver` 之类的自动按需注入器

### 资源引用
- 用户无特别约束时可用 Unsplash 图片
- 图标统一用**内联 SVG**（`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="..." /></svg>`），按需封装到 `src/components/icons/` 下的小 SFC 复用；不要依赖任何图标 npm 包
- 禁止 base64 图片

### 前端视觉要求
- 体现设计感、规范专业、严谨细节
- 尽可能多的功能和交互
- 悬停状态、过渡、微交互要周到
- 遵循层次结构、对比、平衡、动态原则

## Vue 专属最佳实践
- IMPORTANT: 必须创建标准 Vue 3 SFC 应用，严禁使用单 HTML
- `<script setup>` 顶层导入/声明即可自动暴露给模板
- 响应式状态优先用 `ref` + `computed`，复杂场景用 Pinia
- Vue 模板编译错误导致多次修复失败（尝试 3 次以上），直接重写文件
- 任何文件编辑/新建后最终交付前都要运行 `pnpm run dev` 确保无编译错误
