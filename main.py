"""
前端发请求 (带 session_id)
   ↓
FastAPI 接口收到 message + session_id
   ↓
调用 agent.chat(message, session_id)
   ↓
把 reply + session_id 返回给前端
"""

from fastapi import FastAPI     #用来创建后端接口服务
from pydantic import BaseModel  #用来定义数据模型
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio
import queue
import threading

from backend.agent.zhangxuefeng_agent import ZhangXueFengAgent
from backend.data.zhangxuefeng_quotes.farewell_quotes import get_farewell_with_quote

# 创建 FastAPI 应用
app = FastAPI(title="张雪峰教育智能体")

# 解决跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 前端传过来的数据格式
class ChatRequest(BaseModel):
    message: Optional[str] = None  # 可选，结束会话时不需要
    session_id: Optional[str] = None  # 可选，不传则创建新会话

# 创建Agent全局实例
# 延迟初始化，避免启动时阻塞
agent = None

def get_agent():
    """获取Agent实例"""
    global agent
    if agent is None:
        try:
            agent = ZhangXueFengAgent()
            print("[Main] Agent 初始化完成")
        except Exception as e:
            print(f"[Main] Agent 初始化失败: {e}")
            # 创建一个最小化的Agent实例，确保服务器能够正常运行
            class MinimalAgent:
                def __init__(self):
                    self.sessions = {}
                def chat(self, message, session_id):
                    return {
                        "reply": "抱歉，服务暂时不可用，请稍后重试。",
                        "session_id": session_id or "test_session",
                        "stage": "initial",
                        "collected_info": {}
                    }
                def chat_stream(self, message, session_id):
                    yield "抱歉，服务暂时不可用，请稍后重试。"
                    yield f"\n[SESSION_INFO]{session_id or 'test_session'}|initial[END]"
            agent = MinimalAgent()
    return agent

# 根路由测试接口
@app.get("/")
def root():
    return {"message": "后端服务已启动"}

# 聊天接口
@app.post("/chat")
def chat(data: ChatRequest):
    agent_instance = get_agent()
    result = agent_instance.chat(data.message, data.session_id)
    return {
        "reply": result["reply"],
        "session_id": result["session_id"],
        "stage": result["stage"],
        "collected_info": result["collected_info"]
    }

# 流式聊天接口
@app.post("/chat/stream")
async def chat_stream(data: ChatRequest):
    async def generate():
        try:
            agent_instance = get_agent()
            session_info = None
            
            # 使用队列在线程间传递数据，避免同步生成器阻塞异步事件循环
            chunk_queue = queue.Queue()
            exception_holder = [None]  # 用列表存储线程中的异常
            
            def run_sync_stream():
                """在独立线程中运行同步生成器"""
                try:
                    for chunk in agent_instance.chat_stream(data.message, data.session_id):
                        chunk_queue.put(chunk)
                except Exception as e:
                    exception_holder[0] = e
                finally:
                    chunk_queue.put(None)  # 发送结束信号
            
            # 启动线程运行同步流式生成器
            thread = threading.Thread(target=run_sync_stream, daemon=True)
            thread.start()
            
            # 异步地从队列中读取数据并发送
            while True:
                # 让出事件循环控制权，避免阻塞
                await asyncio.sleep(0)
                
                try:
                    chunk = chunk_queue.get_nowait()
                except queue.Empty:
                    # 队列为空，短暂等待后重试
                    await asyncio.sleep(0.01)
                    continue
                
                if chunk is None:
                    # 结束信号
                    break
                
                chunk_str = str(chunk)
                # 检查是否是会话信息标记
                if chunk_str.startswith("\n[SESSION_INFO]") and chunk_str.endswith("[END]"):
                    session_info = chunk_str.replace("\n[SESSION_INFO]", "").replace("[END]", "")
                else:
                    yield f"data: {chunk_str}\n\n"
            
            # 检查线程中是否有异常
            if exception_holder[0]:
                print(f"流式生成线程错误: {exception_holder[0]}")
                yield f"data: 错误: {str(exception_holder[0])}\n\n"
            
            # 发送会话信息
            if session_info:
                yield f"data: [SESSION]{session_info}[END_SESSION]\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"流式接口错误: {e}")
            yield f"data: 错误: {str(e)}\n\n"
    
    return StreamingResponse(
        generate(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )

# 结束会话接口
@app.post("/chat/end")
def end_chat(data: ChatRequest):
    """结束会话，返回心灵鸡汤"""
    agent_instance = get_agent()
    # 如果有会话ID，从agent中移除该会话
    if data.session_id and hasattr(agent_instance, 'sessions') and data.session_id in agent_instance.sessions:
        del agent_instance.sessions[data.session_id]
        print(f"[EndChat] 会话 {data.session_id} 已结束")
    else:
        print(f"[EndChat] 没有有效的会话ID，直接返回鸡汤")
    
    # 返回随机心灵鸡汤
    farewell = get_farewell_with_quote()
    print(f"[EndChat] 返回鸡汤: {farewell}")
    return {
        "farewell_message": farewell,
        "session_ended": True
    }
