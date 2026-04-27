import subprocess
import time
import socket

def ensure_containers_running():
    """
    检查并确保所需的 Docker 容器（postgres, redis）正在运行。
    增加端口拨测逻辑以确保服务真正可用。
    """
    containers = {
        "postgres": 5432,
        "redis": 6379
    }
    
    for c, port in containers.items():
        try:
            # 1. 检查并启动容器
            res = subprocess.run(
                ["docker", "ps", "-a", "-f", f"name=^/{c}$", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            
            if c not in res.stdout:
                print(f"Container {c} not found. You might need to run 'docker run' manually once.")
                # 此处不自动 run，防止配置错误，保持 current logic
                continue

            running_res = subprocess.run(
                ["docker", "ps", "-f", f"name=^/{c}$", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )

            if c not in running_res.stdout:
                print(f"Starting container {c}...")
                subprocess.run(["docker", "start", c], check=True)
            
            # 2. 端口拨测：最多等待 15 秒
            print(f"Waiting for {c} to be ready on port {port}...")
            start_time = time.time()
            while time.time() - start_time < 15:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    if s.connect_ex(("localhost", port)) == 0:
                        print(f"Container {c} is ready.")
                        break
                time.sleep(1)
            else:
                raise RuntimeError(f"Timeout waiting for {c} to become ready.")
                
        except subprocess.CalledProcessError as e:
            print(f"Error checking/starting container {c}: {e}")
            raise RuntimeError(f"Docker command failed for {c}.")

if __name__ == "__main__":
    ensure_containers_running()
