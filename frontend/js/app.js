const API_URL = 'http://127.0.0.1:8000';
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const endChatModal = document.getElementById('endChatModal');

// 会话管理
let currentSessionId = null;
let currentStage = 'initial';
let collectedInfo = {};

// 感谢词列表
const gratitudeKeywords = [
    '谢谢', '感谢', '多谢', '谢谢老师', '谢谢张老师', '谢谢张雪峰', 
    '谢谢您', '谢谢帮助', '谢谢建议', '谢谢指导', '谢谢解答',
    '明白了', '懂了', '清楚了', '知道了', '了解了', '受教了',
    '很有帮助', '很有用', '太感谢了', '非常感谢', '万分感谢'
];

// 检测是否包含感谢词
function containsGratitude(message) {
    return gratitudeKeywords.some(keyword => message.includes(keyword));
}

function addMessage(text, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'ai'}`;
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-label">${isUser ? '你' : '张雪峰老师'}</div>
            <div class="message-text">${text}</div>
        </div>
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function updateStatusBar() {
    // 更新状态显示（如果有状态栏的话）
    const statusBar = document.getElementById('statusBar');
    if (statusBar) {
        const stageText = {
            'initial': '初次对话',
            'identity': '确认身份',
            'basic_info': '了解基本情况',
            'preferences': '了解意向',
            'complete': '信息完整'
        }[currentStage] || '对话中';
        
        statusBar.textContent = `当前阶段：${stageText}`;
    }
}

async function getAIResponse(userMessage) {
    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                message: userMessage,
                session_id: currentSessionId 
            })
        });
        
        if (!response.ok) {
            throw new Error('网络请求失败');
        }
        
        const data = await response.json();
        
        // 更新会话信息
        if (data.session_id) {
            currentSessionId = data.session_id;
        }
        if (data.stage) {
            currentStage = data.stage;
        }
        if (data.collected_info) {
            collectedInfo = data.collected_info;
        }
        updateStatusBar();
        
        return data.reply;
    } catch (error) {
        console.error('请求错误:', error);
        return '抱歉，连接服务器失败，请检查后端服务是否启动。';
    }
}

async function getAIResponseStream(userMessage, loadingDiv) {
    try {
        const response = await fetch(`${API_URL}/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                message: userMessage,
                session_id: currentSessionId 
            })
        });
        
        if (!response.ok) {
            throw new Error('网络请求失败');
        }
        
        // 检查 response.body 是否存在
        if (!response.body) {
            console.error('Response body is not available');
            // 回退到非流式请求
            return getAIResponse(userMessage);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let reply = '';
        let buffer = '';  // SSE 数据缓冲区，处理跨 chunk 的不完整行
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            // 保留最后一个可能不完整的行
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const content = line.substring(6);
                    
                    // 检查是否是会话信息
                    if (content.startsWith('[SESSION]') && content.includes('[END_SESSION]')) {
                        const sessionData = content.replace('[SESSION]', '').replace('[END_SESSION]', '');
                        const parts = sessionData.split('|');
                        if (parts.length >= 2) {
                            currentSessionId = parts[0];
                            currentStage = parts[1];
                        }
                        updateStatusBar();
                    } else if (content === '[DONE]') {
                        // 流结束标记，不做处理
                    } else if (content) {
                        // 直接拼接内容，不做有缺陷的去重检查
                        reply += content;
                        // 更新显示
                        loadingDiv.innerHTML = `
                            <div class="message-content">
                                <div class="message-label">张雪峰老师</div>
                                <div class="message-text">${reply}</div>
                            </div>
                        `;
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                }
            }
        }
        
        return reply;
    } catch (error) {
        console.error('请求错误:', error);
        // 出错时回退到非流式请求
        return getAIResponse(userMessage);
    }
}

// 保存用户最后一条消息，用于取消结束对话后继续
let pendingMessage = '';

// 显示结束对话弹窗
function showEndChatModal(message = '') {
    pendingMessage = message;
    endChatModal.style.display = 'flex';
}

// 关闭结束对话弹窗
function closeEndChatModal() {
    endChatModal.style.display = 'none';
    // 如果用户取消，继续获取AI回复
    if (pendingMessage) {
        continueChat(pendingMessage);
        pendingMessage = '';
    }
}

// 继续对话（用户取消结束对话后）
async function continueChat(message) {
    // 显示加载状态
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message ai loading';
    loadingDiv.innerHTML = `
        <div class="message-content">
            <div class="message-label">张雪峰老师</div>
            <div class="message-text">思考中...</div>
        </div>
    `;
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // 获取 AI 回复（流式）
    const response = await getAIResponseStream(message, loadingDiv);
    
    // 移除加载状态类
    loadingDiv.classList.remove('loading');
}

// 确认结束对话
async function confirmEndChat() {
    console.log('确认结束对话被点击');
    // 直接关闭弹窗，不触发取消逻辑
    endChatModal.style.display = 'none';
    pendingMessage = ''; // 清空待处理消息
    
    // 调用后端结束会话接口
    try {
        // 构建请求体，如果没有session_id就不传
        const requestBody = {};
        if (currentSessionId) {
            requestBody.session_id = currentSessionId;
        }
        console.log('调用结束会话接口, 请求体:', requestBody);
        
        const response = await fetch(`${API_URL}/chat/end`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            console.error('接口返回错误:', response.status, response.statusText);
        }
        
        const data = await response.json();
        console.log('接口返回数据:', data);
        
        // 显示结束语（鸡汤）
        if (data.farewell_message) {
            console.log('显示鸡汤:', data.farewell_message);
            // 创建一个新的消息div来显示鸡汤
            const farewellDiv = document.createElement('div');
            farewellDiv.className = 'message ai';
            farewellDiv.innerHTML = `
                <div class="message-content">
                    <div class="message-label">张雪峰老师</div>
                    <div class="message-text">${data.farewell_message}</div>
                </div>
            `;
            chatMessages.appendChild(farewellDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // 5秒后重置聊天（给用户时间看鸡汤）
            setTimeout(() => {
                console.log('5秒后重置聊天');
                resetChat();
            }, 5000);
        } else {
            console.log('没有鸡汤，直接重置');
            // 如果没有鸡汤，直接重置
            resetChat();
        }
        
    } catch (error) {
        console.error('结束会话错误:', error);
        resetChat();
    }
}

// 重置聊天
function resetChat() {
    currentSessionId = null;
    currentStage = 'initial';
    collectedInfo = {};
    chatMessages.innerHTML = `
        <div class="message ai">
            <div class="message-content">
                <div class="message-label">张雪峰老师</div>
                <div class="message-text">
                    高考志愿填报，选对了路比瞎努力重要。我看数据说话，就业、薪资、录取线，这些才是实在的。

来，先告诉我，你是学生本人还是家长？
                </div>
            </div>
        </div>
    `;
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    addMessage(message, true);
    messageInput.value = '';
    messageInput.style.height = '52px';

    // 检测是否包含感谢词
    if (containsGratitude(message)) {
        showEndChatModal(message);
        // 如果包含感谢词，不继续获取AI回复，等用户选择是否结束对话
        return;
    }

    // 显示加载状态
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message ai loading';
    loadingDiv.innerHTML = `
        <div class="message-content">
            <div class="message-label">张雪峰老师</div>
            <div class="message-text">思考中...</div>
        </div>
    `;
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // 获取 AI 回复（流式）
    const response = await getAIResponseStream(message, loadingDiv);
    
    // 移除加载状态类
    loadingDiv.classList.remove('loading');
}

messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
});

document.querySelectorAll('.quick-question').forEach(btn => {
    btn.addEventListener('click', () => {
        messageInput.value = btn.textContent;
        sendMessage();
    });
});
