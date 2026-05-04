# 前端基础设施与状态管理 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。

**目标：** 初始化 Vite + React 19 项目环境，构建 Ant Design 的视觉防线（政务主题、水印组件），并完成核心底层通讯枢纽（Zustand Store，Axios apiClient）。

**技术栈：** React 19, Vite, TypeScript, Ant Design v6, Zustand, Axios

---

### 任务 1：Vite 基础框架初始化与依赖安装

**文件：**
- 创建：`frontend/package.json`
- 创建：`frontend/vite.config.ts`
- 创建：`frontend/tsconfig.json`
- 创建：`frontend/index.html`

- [ ] **步骤 1：配置前端依赖与构建脚本**

```json
// frontend/package.json
{
  "name": "newgwsh-frontend",
  "private": true,
  "version": "3.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "antd": "^6.0.0",
    "@ant-design/icons": "^5.0.0",
    "zustand": "^5.0.0",
    "axios": "^1.7.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.5.0",
    "vite": "^6.0.0"
  }
}
```

- [ ] **步骤 2：配置 Vite 与 TS**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

```json
// frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"]
}
```

- [ ] **步骤 3：创建入口 HTML**

```html
<!-- frontend/index.html -->
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>泰兴调查队公文处理系统</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **步骤 4：Commit**

```bash
git add frontend/
git commit -m "build: 前端 Vite+React 框架与依赖初始化"
```

### 任务 2：状态管理中枢 (Zustand Stores)

**文件：**
- 创建：`frontend/src/stores/authStore.ts`
- 创建：`frontend/src/stores/editorStore.ts`

- [ ] **步骤 1：实现鉴权状态机**

```typescript
// frontend/src/stores/authStore.ts
import { create } from 'zustand'

interface UserInfo {
  user_id: number;
  username: string;
  full_name: string;
  role_level: number;
  dept_id: number | null;
}

interface AuthState {
  token: string | null;
  userInfo: UserInfo | null;
  setToken: (token: string | null) => void;
  setUserInfo: (info: UserInfo | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('access_token'),
  userInfo: null,
  setToken: (token) => {
    if (token) localStorage.setItem('access_token', token);
    else localStorage.removeItem('access_token');
    set({ token })
  },
  setUserInfo: (info) => set({ userInfo: info }),
  logout: () => {
    localStorage.removeItem('access_token');
    set({ token: null, userInfo: null });
    window.location.href = '/login';
  }
}))
```

- [ ] **步骤 2：实现工作区生命周期状态机**

```typescript
// frontend/src/stores/editorStore.ts
import { create } from 'zustand'

interface EditorState {
  currentDocId: string | null;
  docTypeId: number | null;
  exemplarId: number | null;
  content: string;
  aiPolishedContent: string | null;
  viewMode: 'SINGLE' | 'DIFF';
  context_kb_ids: number[];
  context_snapshot_version: number;
  isBusy: boolean;
  
  setDocId: (id: string | null) => void;
  setContent: (content: string) => void;
  setPolishedContent: (content: string | null) => void;
  setViewMode: (mode: 'SINGLE' | 'DIFF') => void;
  setBusy: (busy: boolean) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  currentDocId: null,
  docTypeId: null,
  exemplarId: null,
  content: '',
  aiPolishedContent: null,
  viewMode: 'SINGLE',
  context_kb_ids: [],
  context_snapshot_version: 0,
  isBusy: false,
  
  setDocId: (id) => set({ currentDocId: id }),
  setContent: (content) => set({ content }),
  setPolishedContent: (content) => set({ aiPolishedContent: content }),
  setViewMode: (mode) => set({ viewMode: mode }),
  setBusy: (busy) => set({ isBusy: busy })
}))
```

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/stores/
git commit -m "feat: 实现鉴权与公文工作区 Zustand 状态中枢"
```

### 任务 3：统一 API 拦截器与水印防御组件

**文件：**
- 创建：`frontend/src/api/client.ts`
- 创建：`frontend/src/components/common/AntiLeakWatermark.tsx`
- 创建：`frontend/src/styles/theme.ts`

- [ ] **步骤 1：编写带防吞噬的 Axios 拦截器**

```typescript
// frontend/src/api/client.ts
import axios from 'axios';
import { useAuthStore } from '../stores/authStore';
import { message, Modal } from 'antd';

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      if (error.response.status === 401) {
        const errorData = error.response.data;
        if (errorData?.error_code === 'SESSION_KICKED') {
          Modal.warning({
            title: '登录失效',
            content: '您的账号已在其他设备登录，请重新登录',
            onOk: () => useAuthStore.getState().logout()
          });
        } else {
          // 这里可以加入 refresh token 逻辑，暂简化
          useAuthStore.getState().logout();
        }
      } else {
        // 防止前端吞没错误
        message.error(error.response.data?.message || '请求失败');
      }
    }
    return Promise.reject(error);
  }
);
```

- [ ] **步骤 2：创建政务主题与全局水印组件**

```typescript
// frontend/src/styles/theme.ts
export const TAIXING_TOKENS = {
  token: {
    colorPrimary: '#003366', // 政务蓝
    colorBgLayout: '#f0f2f5',
    fontFamily: '"方正仿宋_GBK", "FZFS", "仿宋_GB2312", "仿宋", "FangSong", "STFangsong", "华文仿宋", "Noto Serif CJK SC", serif',
  }
};
```

```tsx
// frontend/src/components/common/AntiLeakWatermark.tsx
import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../../stores/authStore';

export const AntiLeakWatermark: React.FC = () => {
  const userInfo = useAuthStore(state => state.userInfo);
  const [timeStr, setTimeStr] = useState(new Date().toLocaleString());

  useEffect(() => {
    const timer = setInterval(() => setTimeStr(new Date().toLocaleString()), 60000);
    return () => clearInterval(timer);
  }, []);

  if (!userInfo) return null;

  const watermarkText = `${userInfo.username} ${userInfo.full_name} ${timeStr}`;

  return (
    <div
      style={{
        position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
        pointerEvents: 'none', zIndex: 9999, overflow: 'hidden', opacity: 0.08,
        display: 'flex', flexWrap: 'wrap', transform: 'rotate(-20deg)', transformOrigin: 'center'
      }}
    >
      {Array.from({ length: 100 }).map((_, i) => (
        <div key={i} style={{ width: '300px', height: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {watermarkText}
        </div>
      ))}
    </div>
  );
};
```

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/api/ frontend/src/components/ frontend/src/styles/
git commit -m "feat: 实现 API 拦截与全局防泄密水印"
```