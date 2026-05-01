import os
from typing import Dict, Optional
from app.core.config import settings

class PromptLoader:
    _instance: Optional["PromptLoader"] = None
    _prompts: Dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PromptLoader, cls).__new__(cls)
            cls._instance.reload()
        return cls._instance

    def reload(self):
        """
        热加载提示词: 扫描 app/prompts/ 目录下的所有 .txt 文件
        """
        prompts_dir = settings.PROMPTS_ROOT
        if not os.path.exists(prompts_dir):
            os.makedirs(prompts_dir, exist_ok=True)
            
        new_prompts = {}
        for filename in os.listdir(prompts_dir):
            if filename.endswith(".txt"):
                name = os.path.splitext(filename)[0]
                with open(os.path.join(prompts_dir, filename), "r", encoding="utf-8") as f:
                    new_prompts[name] = f.read()
        
        self._prompts = new_prompts

    def get_prompt(self, name: str) -> str:
        """
        获取提示词内容
        """
        return self._prompts.get(name, "")

    def get_vocab_blacklist(self) -> Dict[str, str]:
        """
        解析 vocab_blacklist.txt 格式: 原词→替换词
        """
        content = self.get_prompt("vocab_blacklist")
        blacklist = {}
        for line in content.splitlines():
            if "→" in line:
                old, new = line.split("→", 1)
                blacklist[old.strip()] = new.strip()
        return blacklist

    def list_prompts(self) -> Dict[str, str]:
        """
        获取所有已加载的提示词列表
        """
        return self._prompts

prompt_loader = PromptLoader()
