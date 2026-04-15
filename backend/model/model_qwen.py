"""
模型工厂——创建 LLM 模型实例
"""
import os
import dashscope

# 模型默认是千问
def get_model_qwen():
    dashscope.api_key=os.getenv("DASHSCOPE_API_KEY") or "你的通义API密钥"
    model="qwen3-max" # 使用最新的千问3.0模型版本
    
    def chat(messages):
        # 模型回答
        response = dashscope.Generation.call(
            model=model,
            messages=messages,  # 把整个聊天历史发给 AI
            result_format="message",
            temperature=0.7,  # 控制随机性，越低越稳定
            max_tokens=4000,  # 限制输出长度
            enable_thinking=False  # 显式关闭思考模式，避免思考内容干扰输出
        )
        if response.status_code == 200:  # 调用成功
            return response.output.choices[0].message.content
        raise Exception(f"通义调用失败：{response.message}")
    
    def chat_stream(messages):
        # 流式输出 - 使用增量模式（官方推荐）
        try:
            response = dashscope.Generation.call(
                model=model,
                messages=messages,
                result_format="message",
                stream=True,
                incremental_output=True,  # 增量输出，每个chunk只返回新增部分
                temperature=0.7,  # 控制随机性
                max_tokens=4000,  # 限制输出长度
                enable_thinking=False  # 显式关闭思考模式，避免思考内容干扰流式输出
            )
                
            has_content = False
                
            for chunk in response:
                if chunk.status_code == 200:
                    try:
                        # 直接访问 chunk 的属性
                        if hasattr(chunk, 'output') and chunk.output:
                            output = chunk.output
                            if hasattr(output, 'choices') and output.choices:
                                choice = output.choices[0]
                                
                                # 尝试从 message.content 获取内容
                                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                                    content = choice.message.content
                                    if content:
                                        has_content = True
                                        # 增量模式：content 就是新增的部分，直接 yield
                                        yield content
                    except Exception as e:
                        print(f"流式输出错误: {e}")
                        continue
            
            # 如果没有内容，用非流式方式兜底
            if not has_content:
                try:
                    reply = chat(messages)
                    yield reply
                except Exception as e:
                    print(f"兜底请求错误: {e}")
                    yield "抱歉，获取回复失败，请稍后重试。"
        except Exception as e:
            print(f"流式请求错误: {e}")
            # 出错时使用非流式方式兜底
            try:
                reply = chat(messages)
                yield reply
            except Exception as e:
                print(f"兜底请求错误: {e}")
                yield "抱歉，获取回复失败，请稍后重试。"
        
    return chat, chat_stream