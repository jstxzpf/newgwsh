import os
import requests
from typing import List, Dict, Any, Optional
from markitdown import MarkItDown
from markdown_it import MarkdownIt
from app.core.config import settings

from app.services.prompt_service import prompt_loader

class AIService:
    def __init__(self):
        self.md_it = MarkdownIt("commonmark")
        self.markitdown = MarkItDown()

    def get_embedding(self, text: str) -> List[float]:
        """调用 Ollama 获取向量 (Embeddings)"""
        url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
        payload = {
            "model": settings.OLLAMA_EMBEDDING_MODEL, 
            "prompt": text
        }
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            raise RuntimeError(f"Ollama embedding failed: {str(e)}")

    def parse_to_markdown(self, file_path: str) -> str:
        """使用 MarkItDown 将各种格式转为 Markdown"""
        result = self.markitdown.convert(file_path)
        return result.text_content

    def chunk_markdown(self, md_text: str) -> List[Dict[str, Any]]:
        """基于 AST 的语义切片 (符合实施约束规则 4)"""
        tokens = self.md_it.parse(md_text)
        chunks = []
        current_header_path = ["" for _ in range(7)] # H1-H6
        
        current_chunk_text = ""
        
        for i, token in enumerate(tokens):
            if token.type == "heading_open":
                level = int(token.tag[1])
                # 寻找对应的标题文本
                inline_token = tokens[i+1]
                if inline_token.type == "inline":
                    current_header_path[level] = inline_token.content
                    # 清空更深层级的标题
                    for j in range(level + 1, 7):
                        current_header_path[j] = ""
            
            if token.type == "inline" and tokens[i-1].type != "heading_open":
                current_chunk_text += token.content + "\n"
                
            # 当块足够大时切割 (约 800 字符)
            if len(current_chunk_text) > 800:
                path = " > ".join([h for h in current_header_path if h])
                chunks.append({
                    "content": current_chunk_text.strip(),
                    "metadata": {"title_path": path}
                })
                current_chunk_text = ""

        if current_chunk_text:
            path = " > ".join([h for h in current_header_path if h])
            chunks.append({
                "content": current_chunk_text.strip(),
                "metadata": {"title_path": path}
            })
            
        return chunks

    def chat_completion(self, system_prompt_name: str, user_query: str, context: str = "", **kwargs) -> str:
        """调用 Ollama 生成回答 (从 prompt_loader 加载模板)"""
        url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        
        template = prompt_loader.get_prompt(system_prompt_name)
        if not template:
            template = "You are a helpful assistant."
            
        # 安全填充占位符
        try:
            full_system_prompt = template.format(context=context, **kwargs)
        except KeyError:
            # 防止占位符缺失报错
            full_system_prompt = template
            
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": user_query,
            "system": full_system_prompt,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=settings.OLLAMA_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            raise RuntimeError(f"Ollama chat failed: {str(e)}")

    def stream_chat_completion(self, system_prompt_name: str, user_query: str, context: str = "", **kwargs):
        """流式调用 Ollama (生成器方式)"""
        url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        template = prompt_loader.get_prompt(system_prompt_name)
        if not template:
            template = "You are a helpful assistant."
            
        try:
            full_system_prompt = template.format(context=context, **kwargs)
        except KeyError:
            full_system_prompt = template
            
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": user_query,
            "system": full_system_prompt,
            "stream": True
        }
        
        try:
            # 使用 requests 开启流
            with requests.post(url, json=payload, timeout=settings.OLLAMA_TIMEOUT_SECONDS, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        import json
                        yield json.loads(line)
        except Exception as e:
            yield {"error": str(e), "done": True}

ai_service = AIService()
