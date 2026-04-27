import subprocess
import time

def ensure_containers_running():
    """
    检查并确保所需的 Docker 容器（postgres, redis）正在运行。
    如果容器未运行，则尝试启动它们。
    """
    containers = ["postgres", "redis"]
    for c in containers:
        # 检查容器是否在运行
        # 使用 -f name={c} 过滤，--format "{{.Names}}" 只输出名称
        res = subprocess.run(
            ["docker", "ps", "-f", f"name={c}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        
        # 如果输出中不包含容器名称，说明容器未运行（或者不存在，但此处假设已创建）
        if c not in res.stdout:
            print(f"Starting container {c}...")
            subprocess.run(["docker", "start", c])
            
    # 简单的就绪等待，确保服务初始化完成
    time.sleep(2)

if __name__ == "__main__":
    ensure_containers_running()
