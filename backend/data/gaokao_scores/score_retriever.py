"""
高考分数线数据检索器
用于加载和检索高考分数线数据
"""

import json
import os
from typing import List, Dict, Optional


class ScoreRetriever:
    """
    高考分数线检索器
    加载高考分数线数据，提供关键词检索功能
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化检索器，加载高考分数线数据
        
        Args:
            data_dir: 数据文件目录，默认使用当前文件所在目录
        """
        print(f"[ScoreRetriever] 开始初始化...")
        if data_dir is None:
            data_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.data_dir = data_dir
        self.score_data = {}
        self._load_data()
        print(f"[ScoreRetriever] 初始化完成")
    
    def _load_data(self):
        """加载高考分数线数据"""
        print(f"[ScoreRetriever] 开始加载数据...")
        # 加载2023-2025年分数线数据
        years = [2023, 2024, 2025]
        for year in years:
            data_path = os.path.join(self.data_dir, f"{year}_scores.json")
            print(f"[ScoreRetriever] 检查数据文件: {data_path}")
            if os.path.exists(data_path):
                print(f"[ScoreRetriever] 加载数据文件: {year}_scores.json")
                try:
                    with open(data_path, "r", encoding="utf-8") as f:
                        self.score_data[year] = json.load(f)
                    print(f"[ScoreRetriever] 加载完成: {year}_scores.json")
                except Exception as e:
                    print(f"[ScoreRetriever] 加载数据文件出错: {e}")
            else:
                print(f"[ScoreRetriever] 数据文件不存在: {data_path}")
    
    def search(self, province: str, year: int = 2025) -> Optional[Dict]:
        """
        根据省份和年份检索分数线
        
        Args:
            province: 省份名称
            year: 年份，默认2025
            
        Returns:
            该省份的分数线信息
        """
        if year not in self.score_data:
            return None
        
        provinces = self.score_data[year].get("provinces", [])
        for prov_data in provinces:
            if prov_data["name"] == province:
                return prov_data
        
        return None
    
    def get_all_provinces(self, year: int = 2025) -> List[str]:
        """
        获取指定年份的所有省份列表
        
        Args:
            year: 年份，默认2025
            
        Returns:
            省份列表
        """
        if year not in self.score_data:
            return []
        
        provinces = self.score_data[year].get("provinces", [])
        return [prov["name"] for prov in provinces]
    
    def format_score_for_prompt(self, score_data: Dict, year: int) -> str:
        """
        将分数线数据格式化为 Prompt 可用的字符串
        
        Args:
            score_data: 分数线数据
            year: 年份
            
        Returns:
            格式化后的字符串
        """
        if not score_data:
            return ""
        
        formatted = f"【{year}年高考分数线参考】\n"
        formatted += f"省份: {score_data['name']}\n"
        
        # 处理分数线数据
        if "first_batch_line" in score_data:
            # 老高考数据
            if isinstance(score_data["first_batch_line"], dict):
                # 分文理科
                formatted += "一本线:\n"
                if "arts" in score_data["first_batch_line"]:
                    formatted += f"  文科: {score_data['first_batch_line']['arts']}\n"
                if "science" in score_data["first_batch_line"]:
                    formatted += f"  理科: {score_data['first_batch_line']['science']}\n"
            else:
                # 不分文理
                formatted += f"一本线: {score_data['first_batch_line']}\n"
            
            if "second_batch_line" in score_data:
                if isinstance(score_data["second_batch_line"], dict):
                    # 分文理科或分段
                    if "arts" in score_data["second_batch_line"]:
                        formatted += "二本线:\n"
                        formatted += f"  文科: {score_data['second_batch_line']['arts']}\n"
                        formatted += f"  理科: {score_data['second_batch_line']['science']}\n"
                    elif "first_segment" in score_data["second_batch_line"]:
                        formatted += "本科线:\n"
                        formatted += f"  一段: {score_data['second_batch_line']['first_segment']}\n"
                        formatted += f"  二段: {score_data['second_batch_line']['second_segment']}\n"
                else:
                    # 不分文理
                    formatted += f"二本线: {score_data['second_batch_line']}\n"
        elif "special_control_line" in score_data:
            # 新高考数据
            if isinstance(score_data["special_control_line"], dict):
                # 分历史/物理
                formatted += "特控线(一本):\n"
                if "history" in score_data["special_control_line"]:
                    formatted += f"  历史类: {score_data['special_control_line']['history']}\n"
                if "physics" in score_data["special_control_line"]:
                    formatted += f"  物理类: {score_data['special_control_line']['physics']}\n"
            else:
                # 不分文理
                formatted += f"特控线(一本): {score_data['special_control_line']}\n"
            
            if "undergraduate_line" in score_data:
                if isinstance(score_data["undergraduate_line"], dict):
                    # 分历史/物理或分段
                    if "history" in score_data["undergraduate_line"]:
                        formatted += "本科线(二本):\n"
                        formatted += f"  历史类: {score_data['undergraduate_line']['history']}\n"
                        formatted += f"  物理类: {score_data['undergraduate_line']['physics']}\n"
                    elif "first_segment" in score_data["undergraduate_line"]:
                        formatted += "本科线:\n"
                        formatted += f"  一段: {score_data['undergraduate_line']['first_segment']}\n"
                        formatted += f"  二段: {score_data['undergraduate_line']['second_segment']}\n"
                else:
                    # 不分文理
                    formatted += f"本科线(二本): {score_data['undergraduate_line']}\n"
        
        if "notes" in score_data:
            formatted += f"备注: {score_data['notes']}\n"
        
        return formatted


# 单例模式，全局使用
_retriever_instance = None

def get_score_retriever() -> ScoreRetriever:
    """获取分数线检索器单例"""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = ScoreRetriever()
    return _retriever_instance


if __name__ == "__main__":
    # 测试
    retriever = ScoreRetriever()
    
    # 测试搜索
    test_provinces = ["江西", "北京", "上海"]
    for province in test_provinces:
        print(f"\n搜索: {province} 2025年分数线")
        result = retriever.search(province, 2025)
        if result:
            print(retriever.format_score_for_prompt(result, 2025))
        else:
            print("  未找到数据")
    
    # 测试获取所有省份
    print("\n2025年所有省份:")
    provinces = retriever.get_all_provinces(2025)
    print(f"  共 {len(provinces)} 个省份")
    print(f"  前10个: {provinces[:10]}")
