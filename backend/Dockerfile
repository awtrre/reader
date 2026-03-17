# 选用精简版 Python 3.11，拒绝臃肿！
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置时区和环境变量，避免中文乱码和时间错乱
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 先复制依赖文件，利用 Docker 缓存机制加速构建
COPY requirements.txt .

# 安装依赖！
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 把后端的魔法阵全部复制进来
COPY . .

# 暴露 FastAPI 的 8000 端口
EXPOSE 8000

# 启动命令：用 Uvicorn 驱动咱们的异步引擎！
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
