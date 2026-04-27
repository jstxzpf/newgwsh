FROM python:3.11-slim

WORKDIR /app

# 1. 配置 Debian 国内镜像源 (中科大源/清华源) 并安装系统依赖
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. 复制依赖文件 (实现最小变动构建原则：依赖不变则缓存命中)
COPY requirements.txt .

# 3. 安装 Python 依赖 (使用清华源)
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 4. 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
