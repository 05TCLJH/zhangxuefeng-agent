""""
用户问题
   ↓
Agent (管理对话状态)
   ↓
skill.py 提供角色 prompt
   ↓
model.py 提供模型调用能力
   ↓
生成回复
"""

from backend.model.model_qwen import get_model_qwen
from backend.skills.zhangxuefeng.skill import ZhangXueFengSkill
from backend.data.zhangxuefeng_quotes.quote_retriever import get_quote_retriever
from backend.data.professional_market.market_retriever import get_market_retriever
from backend.data.gaokao_scores.score_retriever import get_score_retriever
from typing import Dict, List, Optional
import uuid
from datetime import datetime

"""
对话会话状态
"""
class ConversationSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        
        # 信息收集阶段
        # "initial" -> "identity" -> "basic_info" -> "preferences" -> "complete"
        self.stage = "initial"
        
        # 已收集的信息
        self.collected_info = {
            "identity": None,        # "student" | "parent" | None
            "score": None,          # 分数
            "province": None,       # 省份
            "family_bg": None,      # 家庭条件描述
            "target_city": None,    # 意向城市
            "interest_major": None, # 感兴趣的专业
            "questions": []         # 用户具体问题
        }
        
        # 对话历史
        self.messages: List[Dict] = []
    
    def update_stage(self, new_stage: str):
        """更新对话阶段"""
        self.stage = new_stage
        self.last_active = datetime.now()
    
    def add_message(self, role: str, content: str):
        """添加对话记录"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })
        self.last_active = datetime.now()
    
    def update_info(self, key: str, value):
        """更新收集到的信息"""
        if key in self.collected_info:
            self.collected_info[key] = value
            self.last_active = datetime.now()
    
    def is_info_complete(self) -> bool:
        """检查必要信息是否收集完整"""
        required = ["identity", "score", "province"]
        return all(self.collected_info.get(k) for k in required)


"""
张雪峰教育智能体
负责：对话状态管理 + 角色技能 + 模型调用
"""
class ZhangXueFengAgent:

    # 初始化角色技能和模型
    def __init__(self):
        self.skill = ZhangXueFengSkill()
        self.model, self.model_stream = get_model_qwen()
        self.quote_retriever = None
        self.market_retriever = None
        self.score_retriever = None
        # 会话存储：session_id -> ConversationSession
        self.sessions: Dict[str, ConversationSession] = {}
        # 初始化数据检索器
        self._init_retrievers()
        
    def _init_retrievers(self):
        """初始化数据检索器"""
        # 初始化语录检索器
        try:
            from backend.data.zhangxuefeng_quotes.quote_retriever import get_quote_retriever
            self.quote_retriever = get_quote_retriever()
            print("[Agent] 语录检索器初始化完成")
        except Exception as e:
            print(f"[Agent] 初始化语录检索器失败: {e}")
            self.quote_retriever = None
        
        # 初始化专业行情检索器
        try:
            from backend.data.professional_market.market_retriever import get_market_retriever
            self.market_retriever = get_market_retriever()
            print("[Agent] 专业行情检索器初始化完成")
        except Exception as e:
            print(f"[Agent] 初始化专业行情检索器失败: {e}")
            self.market_retriever = None
        
        # 初始化分数线检索器
        try:
            from backend.data.gaokao_scores.score_retriever import get_score_retriever
            self.score_retriever = get_score_retriever()
            print("[Agent] 分数线检索器初始化完成")
        except Exception as e:
            print(f"[Agent] 初始化分数线检索器失败: {e}")
            self.score_retriever = None
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> ConversationSession:
        """获取或创建会话"""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        
        # 创建新会话
        new_session_id = session_id or str(uuid.uuid4())
        session = ConversationSession(new_session_id)
        self.sessions[new_session_id] = session
        return session
    
    def _build_system_prompt(self, session: ConversationSession, user_message: str = "") -> str:
        """构建系统提示词，包含当前会话状态和检索到的语录"""
        print(f"[BuildPrompt] 开始构建提示词，stage={session.stage}, user_message={user_message[:50]}...")
        # 加载张雪峰的基础人设
        base_prompt = self.skill.get_system_prompt()
        
        # 添加当前状态信息
        score_info = session.collected_info.get('score') or '未提供'
        # 确保排名信息完整显示
        if score_info and ('名' in str(score_info)):
            score_display = f"{score_info}(排名)"
        else:
            score_display = score_info
        
        state_info = f"""

【当前对话状态】
- 阶段：{session.stage}
- 已收集信息：
  * 身份：{session.collected_info.get('identity') or '未确认'}
  * 分数/排名：{score_display}
  * 省份：{session.collected_info.get('province') or '未提供'}
  * 家庭条件：{session.collected_info.get('family_bg') or '未提供'}
  * 意向城市：{session.collected_info.get('target_city') or '未提供'}
  * 感兴趣专业：{session.collected_info.get('interest_major') or '未提供'}

【当前阶段行动指南】
"""
        
        # 根据阶段添加具体指导（禁止AI套话，要像直播一样直接）
        if session.stage == "initial":
            state_info += """
这是对话开始。用户已经看到开场白了，直接问：
"你是学生本人还是家长？"
禁止说："你好我是张雪峰"、"为了更好地帮助你"、"请告诉我"等套话。
"""
        elif session.stage == "identity":
            identity = session.collected_info.get('identity')
            if identity == "parent":
                state_info += """
用户刚说自己是家长。必须热情回应！
正确示范："哎家长您好！孩子考了多少分？"
错误示范："好的，你是家长。孩子考了多少分？"（AI味太重！）
"""
            elif identity == "student":
                state_info += """
用户刚说自己是学生。必须热情回应！
正确示范："学生本人是吧？行！分数多少？排多少名？"
错误示范："好的，你是学生。考了多少分？"（AI味太重！）
"""
            # 只有在还没有分数信息时才追问分数
            if session.collected_info.get('score') is None:
                state_info += """
追问分数或排名：
"考了多少分？" "排名多少？" "哪个省的？"
一个一个问，不要一次性问太多。
注意：如果用户说"前XXX名"、"理科前XXX名"，这也是有效的分数信息，接受它！
正常回答时直接回应，不要说"停停停"！
禁止说："接下来我得再问几个问题"、"这些信息对我很重要"等套话。
禁止重复确认对方的话（不要说"好的，你是家长"这种话）！
"""
            # 如果已经有了分数信息，直接进入下一阶段
            elif session.collected_info.get('province') is None:
                state_info += """
用户已经提供了分数信息，现在追问省份：
"哪个省的？"
正常回答时直接回应，不要说"停停停"！
禁止说："接下来我得再问几个问题"、"这些信息对我很重要"等套话。
"""
            else:
                identity = session.collected_info.get('identity')
                if identity == "parent":
                    state_info += """
用户已经提供了分数和省份信息，现在追问家庭条件：
"家里经济条件怎么样？" "有特别想去的城市吗？"
正常回答时直接回应，不要说"停停停"！
禁止说："接下来我得再问几个问题"、"这些信息对我很重要"等套话。
"""
                else:
                    state_info += """
用户已经提供了分数和省份信息，现在追问家庭条件：
"家里是做什么的？" "经济条件怎么样？" "有特别想去的城市吗？"
正常回答时直接回应，不要说"停停停"！
禁止说："接下来我得再问几个问题"、"这些信息对我很重要"等套话。
"""
        elif session.stage == "basic_info":
            identity = session.collected_info.get('identity')
            if identity == "parent":
                state_info += """
已有基本信息（分数/排名和省份都有了），直接问家庭条件：
"经济条件怎么样？" "有特别想去的城市吗？"
用直播追问的语气，不要解释为什么要问这些。
"""
            else:
                state_info += """
已有基本信息（分数/排名和省份都有了），直接问家庭条件：
"家里是做什么的？" "经济条件怎么样？" "有特别想去的城市吗？"
用直播追问的语气，不要解释为什么要问这些。
"""
        elif session.stage == "preferences":
            state_info += """
信息基本齐全，直接问意向：
"你想学什么专业？" "有没有特别感兴趣的方向？"
不要说"为了更好地给你建议"，直接问！
"""
        elif session.stage == "complete":
            state_info += """
信息已收集完整，直接给建议：
用张雪峰的风格，基于收集到的信息给出明确、直接的判断。
不要铺垫，不要"根据你提供的信息"，直接说观点！

【分数评价指南】
对于江西理科：500 分左右属于中等偏上水平，能上不错的二本院校，但 985/211 比较困难
分数高就直说高，分数一般就说一般，不捧杀、不画饼、不说安慰话
该打击就打击，该现实就现实，张雪峰不说漂亮话，只说大实话
不要用 “很棒”“很不错” 这种虚夸，要讲能上什么层次、什么档次、什么段位
能上一本就说一本，擦线就说擦线，上不了 211 就直接说 “211 别想了”
重点讲位次、段位、区间，比如 “中下游”“中等偏上”“擦线水平”“没戏”
张雪峰风格：直接、务实、有数据支撑、不绕弯子、一针见血、不留情面
"""
        
        # 检索相关语录、专业行情和分数线数据
        # 注意：identity阶段（刚确认身份）不检索，避免简单回复变慢
        quotes_section = ""
        market_section = ""
        score_section = ""
        
        # 只要用户询问专业/学校/分数相关问题，就进行检索
        # 避免在 identity 阶段（如用户说"我是家长"）时进行不必要的检索
        if user_message:
            print(f"[BuildPrompt] 用户消息: {user_message}")
            if any(keyword in user_message for keyword in ["专业", "学校", "大学", "就业", "薪资", "前景", "怎么样", "好不好", "推荐", "分数", "分数线", "一本", "二本", "特控线", "本科线"]):
                print(f"[BuildPrompt] 开始检索相关信息")
                try:
                    # 从用户消息中提取关键词进行检索
                    search_keywords = self._extract_search_keywords(user_message, session)
                    print(f"[BuildPrompt] 提取的搜索关键词: {search_keywords}")
                    
                    # 1. 检索本地语录库
                    if search_keywords and self.quote_retriever:
                        print(f"[BuildPrompt] 开始检索本地语录库")
                        try:
                            related_quotes = self.quote_retriever.search(search_keywords, top_k=3)
                            print(f"[BuildPrompt] 检索到 {len(related_quotes)} 条相关语录")
                            if related_quotes:
                                quotes_section = "\n\n" + self.quote_retriever.format_quotes_for_prompt(related_quotes)
                                quotes_section += "\n【使用说明】以上是与当前话题相关的张雪峰经典语录，你可以在回答中引用或化用这些观点，让回答更有'张雪峰味儿'。但不要生硬照搬，要自然融入对话。"
                                print(f"[BuildPrompt] 语录格式化完成")
                        except Exception as e:
                            print(f"[QuoteRetriever] 检索语录出错: {e}")
                    
                    # 2. 检索专业行情数据（当用户询问专业相关问题时）
                    if any(keyword in user_message for keyword in ["专业", "就业", "薪资", "前景", "好不好", "推荐"]):
                        if search_keywords and self.market_retriever:
                            print(f"[BuildPrompt] 开始检索专业行情数据")
                            try:
                                market_results = self.market_retriever.search(search_keywords, top_k=2)
                                print(f"[BuildPrompt] 检索到 {len(market_results)} 条专业行情数据")
                                if market_results:
                                    market_section = "\n\n" + self.market_retriever.format_market_for_prompt(market_results)
                                    market_section += "\n【使用说明】以上是最新的专业行情数据，请结合张雪峰的经典观点和这些数据，用张雪峰的风格给出建议。记住要保持直接、务实、有数据支撑的风格。"
                                    print(f"[BuildPrompt] 专业行情格式化完成")
                            except Exception as e:
                                print(f"[MarketRetriever] 检索专业行情出错: {e}")
                    
                    # 3. 检索分数线数据（当用户询问分数相关问题时）
                    if any(keyword in user_message for keyword in ["分数", "分数线", "一本", "二本", "特控线", "本科线"]):
                        if session.collected_info.get("province") and self.score_retriever:
                            province = session.collected_info["province"]
                            print(f"[BuildPrompt] 开始检索 {province} 分数线数据")
                            try:
                                score_data = self.score_retriever.search(province, 2025)
                                if score_data:
                                    score_section = "\n\n" + self.score_retriever.format_score_for_prompt(score_data, 2025)
                                    score_section += "\n【使用说明】以上是最新的高考分数线数据，请结合这些数据和张雪峰的风格，给出符合实际的志愿填报建议。"
                                    print(f"[BuildPrompt] 分数线数据格式化完成")
                            except Exception as e:
                                print(f"[ScoreRetriever] 检索分数线出错: {e}")
                except Exception as e:
                    print(f"[BuildPrompt] 检索信息出错: {e}")
        else:
            print(f"[BuildPrompt] 跳过检索，stage={session.stage}，用户消息: {user_message[:50]}...")

        """"
        最终提示词 = 基础人设 + 当前对话状态 + 查到的语录 + 专业行情 + 分数线
        """
        prompt = base_prompt + state_info + quotes_section + market_section + score_section
        print(f"[BuildPrompt] 提示词构建完成，总长度: {len(prompt)}")
        return prompt
    
    def _extract_search_keywords(self, user_message: str, session: ConversationSession) -> str:
        """从用户消息和会话信息中提取检索关键词"""
        keywords = []
        
        # 从用户消息中提取专业名称
        import re
        major_patterns = [
            r'(计算机|软件|人工智能|金融|经济|会计|医学|临床|法学|教育|师范|机械|电气|土木|建筑|新闻|传媒|外语|英语|中文|历史|哲学|数学|物理|化学|生物|环境|材料|化工)',
            r'(985|211|双一流|一本|二本|专科)',
            r'(就业|薪资|工资|前景|发展|考研|考公)'
        ]
        
        for pattern in major_patterns:
            matches = re.findall(pattern, user_message)
            keywords.extend(matches)
        
        # 如果用户消息中没有，从会话信息中获取
        if not keywords and session.collected_info.get("interest_major"):
            keywords.append(session.collected_info["interest_major"])
        
        # 去重并组合
        keywords = list(set(keywords))
        return " ".join(keywords) if keywords else user_message[:20]
    
    def _extract_info_from_message(self, session: ConversationSession, user_message: str):
        """从用户消息中提取信息（简单规则匹配）"""
        msg = user_message.lower()
        
        # 提取身份
        if session.collected_info["identity"] is None:
            if any(kw in msg for kw in ["我是家长", "孩子", "我儿子", "我女儿", "我家"]):
                session.update_info("identity", "parent")
                session.update_stage("identity")
            elif any(kw in msg for kw in ["我是学生","我自己", "我今年", "我高考", "我考了"]):
                session.update_info("identity", "student")
                session.update_stage("identity")
        
        # 提取分数或排名信息
        import re
        if session.collected_info["score"] is None:
            # 匹配 "XXX分"
            score_match = re.search(r'(\d{2,3})\s*分', user_message)
            if score_match:
                session.update_info("score", score_match.group(1) + "分")
                if session.stage == "identity":
                    session.update_stage("basic_info")
            else:
                # 匹配 "前XXX名"、"理科前XXX名"、"文科前XXX名"
                rank_match = re.search(r'(理科|文科)?前(\d{1,5})名', user_message)
                if rank_match:
                    rank_info = rank_match.group(0)  # 完整匹配，如"理科前5000名"
                    session.update_info("score", rank_info)
                    if session.stage == "identity":
                        session.update_stage("basic_info")
        
        # 提取省份
        if session.collected_info["province"] is None:
            provinces = ["北京", "上海", "广东", "江苏", "浙江", "山东", "河南", "河北", 
                        "四川", "湖北", "湖南", "安徽", "江西", "福建", "山西", "陕西"]
            for prov in provinces:
                if prov in user_message:
                    session.update_info("province", prov)
                    break
        
        # 检查是否可以进入下一阶段
        if session.stage == "basic_info" and session.collected_info["province"]:
            if any(kw in msg for kw in ["家里", "父母", "经济", "条件"]):
                session.update_stage("preferences")
        
        if session.stage == "preferences" and session.is_info_complete():
            session.update_stage("complete")
    
    # 处理用户消息并返回回复（非流式）
    def chat(self, user_message: str, session_id: Optional[str] = None) -> Dict:
        """
        用户输入 → AI处理 → 提取信息 → 构建提示词 → 调用模型 → 保存记录 → 返回答案
        """
        session = self.get_or_create_session(session_id)
        
        # 从消息中提取信息
        self._extract_info_from_message(session, user_message)
        
        # 构建提示词（传入用户消息用于检索语录）
        system_prompt = self._build_system_prompt(session, user_message)
        
        # 构建消息列表（包含历史）
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史对话（最近5轮）
        recent_messages = session.messages[-20:] if len(session.messages) > 20 else session.messages
        for msg in recent_messages:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 添加当前消息
        messages.append({"role": "user", "content": user_message})
        
        # 调用模型
        reply = self.model(messages)
        
        # 保存对话记录
        session.add_message("user", user_message)
        session.add_message("assistant", reply)
        
        return {
            "reply": reply,
            "session_id": session.session_id,
            "stage": session.stage,
            "collected_info": session.collected_info
        }
    
    # 流式处理用户消息
    def chat_stream(self, user_message: str, session_id: Optional[str] = None):
        print(f"[ChatStream] 开始处理消息: {user_message}, session_id: {session_id}")
        session = self.get_or_create_session(session_id)
        print(f"[ChatStream] 会话信息: session_id={session.session_id}, stage={session.stage}")
        
        # 从消息中提取信息
        print(f"[ChatStream] 提取信息前，stage={session.stage}")
        self._extract_info_from_message(session, user_message)
        print(f"[ChatStream] 提取信息后，stage={session.stage}, identity={session.collected_info.get('identity')}")
        
        # 构建提示词（传入用户消息用于检索语录）
        print(f"[ChatStream] 开始构建提示词")
        system_prompt = self._build_system_prompt(session, user_message)
        print(f"[ChatStream] 提示词构建完成，长度: {len(system_prompt)}")
        
        # 构建消息列表
        messages = [{
            "role": "system",
            "content": system_prompt
        }]
        
        # 添加历史对话
        recent_messages = session.messages[-20:] if len(session.messages) > 20 else session.messages
        print(f"[ChatStream] 添加 {len(recent_messages)} 条历史消息")
        for msg in recent_messages:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        messages.append({"role": "user", "content": user_message})
        print(f"[ChatStream] 消息列表构建完成，共 {len(messages)} 条消息")
        
        # 保存用户消息
        session.add_message("user", user_message)
        print(f"[ChatStream] 保存用户消息完成")
        
        # 生成回复并保存
        full_reply = ""
        print(f"[ChatStream] 开始调用模型")
        try:
            for chunk in self.model_stream(messages):
                if chunk:
                    print(f"[ChatStream] 收到模型回复 chunk: {chunk[:50]}...")
                    full_reply += str(chunk)
                    yield chunk
        except Exception as e:
            print(f"[ChatStream] 模型调用出错: {e}")
            yield "抱歉，获取回复失败，请稍后重试。"
        
        print(f"[ChatStream] 模型调用完成，回复长度: {len(full_reply)}")
        
        # 保存助手回复
        session.add_message("assistant", full_reply)
        print(f"[ChatStream] 保存助手回复完成")
        
        # 最后返回会话信息
        session_info = f"\n[SESSION_INFO]{session.session_id}|{session.stage}[END]"
        print(f"[ChatStream] 返回会话信息: {session_info}")
        yield session_info



    

    