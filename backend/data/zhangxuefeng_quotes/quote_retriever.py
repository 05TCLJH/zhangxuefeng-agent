"""
张雪峰语录知识库检索器
用于加载和检索张雪峰的经典语录
"""

import json
import os
from typing import List, Dict, Optional
from difflib import SequenceMatcher


class QuoteRetriever:
    """
    语录检索器
    加载所有语录文件，提供关键词检索功能
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化检索器，加载所有语录数据
        
        Args:
            data_dir: 语录文件目录，默认使用当前文件所在目录
        """
        print(f"[QuoteRetriever] 开始初始化...")
        if data_dir is None:
            data_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.data_dir = data_dir
        self.categories = []
        self.quotes = []  # 所有语录列表
        self._load_data()
        print(f"[QuoteRetriever] 初始化完成")
    
    def _load_data(self):
        """加载所有语录数据"""
        print(f"[QuoteRetriever] 开始加载数据...")
        # 加载分类信息
        categories_path = os.path.join(self.data_dir, "categories.json")
        print(f"[QuoteRetriever] 检查分类文件: {categories_path}")
        if os.path.exists(categories_path):
            print(f"[QuoteRetriever] 加载分类文件")
            try:
                with open(categories_path, "r", encoding="utf-8") as f:
                    categories_data = json.load(f)
                    self.categories = categories_data.get("categories", [])
                print(f"[QuoteRetriever] 加载了 {len(self.categories)} 个分类")
            except Exception as e:
                print(f"[QuoteRetriever] 加载分类文件出错: {e}")
        else:
            print(f"[QuoteRetriever] 分类文件不存在: {categories_path}")
        
        # 加载各分类的语录
        category_ids = [cat["id"] for cat in self.categories]
        print(f"[QuoteRetriever] 分类ID列表: {category_ids}")
        
        for cat_id in category_ids:
            file_path = os.path.join(self.data_dir, f"{cat_id}.json")
            print(f"[QuoteRetriever] 检查语录文件: {file_path}")
            if os.path.exists(file_path):
                print(f"[QuoteRetriever] 加载语录文件: {file_path}")
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        quotes = data.get("quotes", [])
                        # 为每个语录添加分类信息
                        for quote in quotes:
                            quote["_category"] = cat_id
                            quote["_category_name"] = next(
                                (cat["name_zh"] for cat in self.categories if cat["id"] == cat_id),
                                cat_id
                            )
                        self.quotes.extend(quotes)
                    print(f"[QuoteRetriever] 加载了 {len(quotes)} 条语录")
                except Exception as e:
                    print(f"[QuoteRetriever] 加载语录文件出错: {e}")
            else:
                print(f"[QuoteRetriever] 语录文件不存在: {file_path}")
        
        print(f"[QuoteRetriever] 已加载 {len(self.quotes)} 条语录，{len(self.categories)} 个分类")
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        根据关键词检索相关语录
        
        Args:
            query: 用户查询/关键词
            top_k: 返回最相关的几条
            
        Returns:
            相关语录列表
        """
        if not query or not self.quotes:
            return []
        
        query = query.lower()
        scored_quotes = []
        
        for quote in self.quotes:
            score = self._calculate_relevance(quote, query)
            if score > 0:
                scored_quotes.append((quote, score))
        
        # 按相关度排序，返回 top_k
        scored_quotes.sort(key=lambda x: x[1], reverse=True)
        return [quote for quote, score in scored_quotes[:top_k]]
    
    def _calculate_relevance(self, quote: Dict, query: str) -> float:
        """
        计算语录与查询的相关度分数
        
        匹配字段（按优先级）：
        1. tags - 标签完全匹配权重最高
        2. related_majors - 相关专业匹配
        3. text - 语录内容模糊匹配
        """
        score = 0.0
        
        # 1. 标签匹配（权重：3.0）
        tags = quote.get("tags", [])
        for tag in tags:
            if query in tag.lower() or tag.lower() in query:
                score += 3.0
        
        # 2. 相关专业匹配（权重：2.5）
        related_majors = quote.get("related_majors", [])
        for major in related_majors:
            if query in major.lower() or major.lower() in query:
                score += 2.5
        
        # 3. 语录内容模糊匹配（权重：1.0 + 相似度）
        text = quote.get("text", "")
        if query in text.lower():
            score += 1.5
        else:
            # 使用序列匹配计算相似度
            similarity = SequenceMatcher(None, query, text.lower()).ratio()
            if similarity > 0.3:  # 相似度阈值
                score += similarity
        
        # 4. ID 匹配（权重：2.0）
        quote_id = quote.get("id", "").lower()
        if query in quote_id:
            score += 2.0
        
        return score
    
    def get_quotes_by_category(self, category_id: str) -> List[Dict]:
        """获取指定分类的所有语录"""
        return [q for q in self.quotes if q.get("_category") == category_id]
    
    def get_quotes_by_sentiment(self, sentiment: str) -> List[Dict]:
        """根据情感类型获取语录"""
        return [q for q in self.quotes if q.get("sentiment") == sentiment]
    
    def get_random_quote(self, category: Optional[str] = None) -> Optional[Dict]:
        """随机获取一条语录"""
        import random
        quotes = self.quotes
        if category:
            quotes = self.get_quotes_by_category(category)
        return random.choice(quotes) if quotes else None
    
    def format_quotes_for_prompt(self, quotes: List[Dict]) -> str:
        """
        将语录格式化为 Prompt 可用的字符串
        
        Args:
            quotes: 语录列表
            
        Returns:
            格式化后的字符串
        """
        if not quotes:
            return ""
        
        formatted = "【张雪峰相关语录参考】\n"
        for i, quote in enumerate(quotes, 1):
            text = quote.get("text", "")
            category = quote.get("_category_name", "")
            tags = ", ".join(quote.get("tags", []))
            formatted += f"{i}. [{category}] {text}\n"
            if tags:
                formatted += f"   标签: {tags}\n"
        
        return formatted


# 单例模式，全局使用
_retriever_instance = None

def get_quote_retriever() -> QuoteRetriever:
    """获取语录检索器单例"""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = QuoteRetriever()
    return _retriever_instance


if __name__ == "__main__":
    # 测试
    retriever = QuoteRetriever()
    
    # 测试搜索
    test_queries = ["金融", "计算机", "医学", "985"]
    for query in test_queries:
        print(f"\n搜索: {query}")
        results = retriever.search(query, top_k=2)
        for r in results:
            print(f"  - {r['text'][:50]}...")
    
    # 测试格式化
    print("\n格式化输出:")
    print(retriever.format_quotes_for_prompt(retriever.search("计算机", top_k=2)))
