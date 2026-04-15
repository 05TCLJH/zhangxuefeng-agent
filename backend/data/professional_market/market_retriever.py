"""
专业行情数据检索器
用于加载和检索专业行情数据
"""

import json
import os
from typing import List, Dict, Optional


class MarketRetriever:
    """
    专业行情检索器
    加载专业行情数据，提供关键词检索功能
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化检索器，加载专业行情数据
        
        Args:
            data_dir: 数据文件目录，默认使用当前文件所在目录
        """
        print(f"[MarketRetriever] 开始初始化...")
        if data_dir is None:
            data_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.data_dir = data_dir
        self.market_data = None
        self._load_data()
        print(f"[MarketRetriever] 初始化完成")
    
    def _load_data(self):
        """加载专业行情数据"""
        print(f"[MarketRetriever] 开始加载数据...")
        # 加载2026年专业行情数据
        data_path = os.path.join(self.data_dir, "2026_professional_market.json")
        print(f"[MarketRetriever] 检查数据文件: {data_path}")
        if os.path.exists(data_path):
            print(f"[MarketRetriever] 加载数据文件")
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    self.market_data = json.load(f)
                print(f"[MarketRetriever] 加载完成")
            except Exception as e:
                print(f"[MarketRetriever] 加载数据文件出错: {e}")
                self.market_data = None
        else:
            print(f"[MarketRetriever] 数据文件不存在: {data_path}")
            self.market_data = None
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        根据关键词检索相关专业行情
        
        Args:
            query: 用户查询/关键词
            top_k: 返回最相关的几条
            
        Returns:
            相关专业行情列表
        """
        if not query or not self.market_data:
            return []
        
        query = query.lower()
        results = []
        
        # 遍历所有专业类别
        categories = self.market_data.get("categories", {})
        for category_type, category_data in categories.items():
            majors = category_data.get("majors", [])
            for major in majors:
                # 检查专业大类是否匹配
                if query in major["category"].lower():
                    results.append({
                        "type": category_type,
                        "category": major["category"],
                        "core_majors": major["core_majors"],
                        "employment_rate": major["employment_rate"],
                        "starting_salary": major["starting_salary"],
                        "prospects": major.get("prospects", major.get("status", "")),
                        "risks": major.get("risks", major.get("exceptions", ""))
                    })
                # 检查核心专业是否匹配
                for core_major in major["core_majors"]:
                    if query in core_major.lower():
                        results.append({
                            "type": category_type,
                            "category": major["category"],
                            "core_majors": major["core_majors"],
                            "employment_rate": major["employment_rate"],
                            "starting_salary": major["starting_salary"],
                            "prospects": major.get("prospects", major.get("status", "")),
                            "risks": major.get("risks", major.get("exceptions", ""))
                        })
        
        # 去重
        unique_results = []
        seen = set()
        for result in results:
            key = result["category"]
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        # 返回前top_k个结果
        return unique_results[:top_k]
    
    def get_key_supplements(self) -> List[str]:
        """
        获取关键补充信息
        
        Returns:
            关键补充信息列表
        """
        if not self.market_data:
            return []
        return self.market_data.get("key_supplements", [])
    
    def format_market_for_prompt(self, market_results: List[Dict]) -> str:
        """
        将专业行情数据格式化为 Prompt 可用的字符串
        
        Args:
            market_results: 专业行情数据列表
            
        Returns:
            格式化后的字符串
        """
        if not market_results:
            return ""
        
        formatted = "【专业行情参考】\n"
        for i, result in enumerate(market_results, 1):
            # 转换类型为中文
            type_map = {
                "green": "绿牌专业",
                "yellow": "黄牌专业",
                "red": "红牌专业"
            }
            type_zh = type_map.get(result["type"], result["type"])
            
            formatted += f"{i}. [{type_zh}] {result['category']}\n"
            formatted += f"   核心专业: {', '.join(result['core_majors'])}\n"
            formatted += f"   就业率: {result['employment_rate']}\n"
            formatted += f"   起薪: {result['starting_salary']}\n"
            formatted += f"   前景: {result['prospects']}\n"
            formatted += f"   风险: {result['risks']}\n"
        
        # 添加关键补充信息
        supplements = self.get_key_supplements()
        if supplements:
            formatted += "\n【关键补充信息】\n"
            for i, supplement in enumerate(supplements, 1):
                formatted += f"{i}. {supplement}\n"
        
        return formatted


# 单例模式，全局使用
_retriever_instance = None

def get_market_retriever() -> MarketRetriever:
    """获取专业行情检索器单例"""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = MarketRetriever()
    return _retriever_instance


if __name__ == "__main__":
    # 测试
    retriever = MarketRetriever()
    
    # 测试搜索
    test_queries = ["计算机", "金融", "医学", "生化环材"]
    for query in test_queries:
        print(f"\n搜索: {query}")
        results = retriever.search(query, top_k=2)
        for r in results:
            print(f"  - {r['category']}: {r['core_majors']}")
    
    # 测试格式化
    print("\n格式化输出:")
    print(retriever.format_market_for_prompt(retriever.search("计算机", top_k=2)))
