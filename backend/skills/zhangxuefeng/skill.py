"""
    张雪峰角色技能
    负责加载角色 prompt
"""


import os

class ZhangXueFengSkill:

    """
    初始化技能，加载角色 prompt
    """
    def __init__(self, prompt_path: str = None):

        # 把目录和文件名拼成完整路径,得到文件"zhangxuefeng_prompt.txt"
        if prompt_path is None:
            prompt_path = os.path.join(
                os.path.dirname(__file__), "zhangxuefeng_prompt.txt"
            )
        
        # 读文件
        with open(prompt_path, "r", encoding="utf-8") as file:
            self._prompt_template = file.read()


    """
    获取系统提示词，返回得到的prompt
    """
    def get_system_prompt(self) -> str:
        return self._prompt_template

