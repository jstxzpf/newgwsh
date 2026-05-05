FROM node:20-alpine

WORKDIR /app

# 使用国内镜像源加速 (§一.3)
RUN npm config set registry https://registry.npmmirror.com

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# 暴露 Vite 默认端口
EXPOSE 5173

# 启动开发服务器，--host 允许从容器外部访问
CMD ["npm", "run", "dev", "--", "--host"]