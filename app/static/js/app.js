// ===== 全局变量 =====
const API_BASE_URL = '';
let currentThreadId = null;
let isStreaming = false;
let chatHistory = [];
let selectedImage = null;

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    // 生成或获取会话ID
    currentThreadId = localStorage.getItem('currentThreadId') || generateThreadId();
    localStorage.setItem('currentThreadId', currentThreadId);
    
    // 加载历史会话列表
    loadChatHistory();
    
    // 加载当前会话消息
    loadCurrentChat();
    
    // 绑定事件
    bindEvents();
}

function bindEvents() {
    // 文件输入变化
    const imageInput = document.getElementById('imageInput');
    if (imageInput) {
        imageInput.addEventListener('change', async (event) => {
            await handleImageSelect(event);
        });
    }
}

// ===== 工具函数 =====
function generateThreadId() {
    return generateUUID();
}

function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function formatTime(date) {
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast show';
    
    if (type === 'error') {
        toast.style.background = 'rgba(239, 68, 68, 0.9)';
    } else if (type === 'success') {
        toast.style.background = 'rgba(34, 197, 94, 0.9)';
    } else {
        toast.style.background = 'rgba(0, 0, 0, 0.8)';
    }
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// ===== 会话管理 =====
function loadChatHistory() {
    const history = localStorage.getItem('chatHistory');
    if (history) {
        chatHistory = JSON.parse(history);
    }
    renderChatHistory();
}

function saveChatHistory() {
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
}

function renderChatHistory() {
    const container = document.getElementById('chatHistory');
    if (!container) return;
    
    container.innerHTML = '';
    
    chatHistory.forEach(chat => {
        const item = document.createElement('div');
        item.className = `chat-item ${chat.id === currentThreadId ? 'active' : ''}`;
        item.onclick = () => switchChat(chat.id);
        
        item.innerHTML = `
            <i class="fas fa-comment-alt"></i>
            <div class="chat-item-text">
                <div class="chat-item-title">${chat.title || '新会话'}</div>
                <div class="chat-item-time">${formatTime(new Date(chat.timestamp))}</div>
            </div>
            <div class="chat-item-actions">
                <button class="chat-item-btn" onclick="event.stopPropagation(); deleteChat('${chat.id}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        container.appendChild(item);
    });
}

function createNewChat() {
    currentThreadId = generateThreadId();
    localStorage.setItem('currentThreadId', currentThreadId);
    
    // 添加到历史记录
    const newChat = {
        id: currentThreadId,
        title: '新会话',
        timestamp: Date.now()
    };
    chatHistory.unshift(newChat);
    saveChatHistory();
    
    // 清空当前显示
    document.getElementById('messages').innerHTML = '';
    document.getElementById('emptyState').style.display = 'flex';
    document.getElementById('currentChatTitle').textContent = '新会话';
    
    renderChatHistory();
    showToast('已创建新会话');
}

function switchChat(threadId) {
    currentThreadId = threadId;
    localStorage.setItem('currentThreadId', currentThreadId);
    
    const chat = chatHistory.find(c => c.id === threadId);
    if (chat) {
        document.getElementById('currentChatTitle').textContent = chat.title || '新会话';
    }
    
    renderChatHistory();
    loadCurrentChat();
}

function deleteChat(threadId) {
    if (!confirm('确定要删除这个会话吗？')) return;
    
    chatHistory = chatHistory.filter(c => c.id !== threadId);
    saveChatHistory();
    
    // 如果删除的是当前会话，创建新会话
    if (threadId === currentThreadId) {
        createNewChat();
    } else {
        renderChatHistory();
    }
    
    showToast('会话已删除');
}

function updateChatTitle(message) {
    const chat = chatHistory.find(c => c.id === currentThreadId);
    if (chat && chat.title === '新会话') {
        // 从消息中提取标题（前20个字符）
        chat.title = message.slice(0, 20) + (message.length > 20 ? '...' : '');
        chat.timestamp = Date.now();
        saveChatHistory();
        renderChatHistory();
        document.getElementById('currentChatTitle').textContent = chat.title;
    }
}

// ===== 消息管理 =====
async function loadCurrentChat() {
    try {
        console.log('加载历史消息，threadId:', currentThreadId);
        const response = await fetch(`${API_BASE_URL}/api/chat/messages?thread_id=${currentThreadId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const messages = await response.json();
        console.log('获取到的消息:', messages);
        
        const messagesContainer = document.getElementById('messages');
        const emptyState = document.getElementById('emptyState');
        
        if (messages && messages.length > 0) {
            emptyState.style.display = 'none';
            messagesContainer.innerHTML = '';
            
            messages.forEach(msg => {
                appendMessage(msg.role, msg.content);
            });
            
            scrollToBottom();
        } else {
            emptyState.style.display = 'flex';
            messagesContainer.innerHTML = '';
        }
    } catch (error) {
        console.error('加载消息失败:', error);
        // 加载失败时显示空状态，而不是错误提示
        const messagesContainer = document.getElementById('messages');
        const emptyState = document.getElementById('emptyState');
        emptyState.style.display = 'flex';
        messagesContainer.innerHTML = '';
    }
}

function appendMessage(role, content, imageUrl = null) {
    const container = document.getElementById('messages');
    const emptyState = document.getElementById('emptyState');
    
    if (emptyState) {
        emptyState.style.display = 'none';
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const avatarIcon = role === 'user' ? 'fa-user' : 'fa-robot';
    
    let imageHtml = '';
    if (imageUrl) {
        imageHtml = `
            <div class="message-image">
                <img src="${imageUrl}" alt="上传的图片">
            </div>
        `;
    }
    
    messageDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fas ${avatarIcon}"></i>
        </div>
        <div class="message-content">
            ${imageHtml}
            <div class="message-bubble">${formatMessage(content)}</div>
            <div class="message-time">${new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</div>
        </div>
    `;
    
    container.appendChild(messageDiv);
    scrollToBottom();
    
    return messageDiv;
}

function formatMessage(content) {
    // 简单的 Markdown 格式化
    let formatted = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    
    // 代码块
    formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    
    // 行内代码
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // 粗体
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // 斜体
    formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    
    // 换行
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

function scrollToBottom() {
    const container = document.getElementById('chatContainer');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

// ===== 图片处理 =====
async function handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // 验证文件类型
    if (!file.type.startsWith('image/')) {
        showToast('请选择图片文件', 'error');
        return;
    }
    
    // 验证文件大小（最大 5MB）
    if (file.size > 5 * 1024 * 1024) {
        showToast('图片大小不能超过 5MB', 'error');
        return;
    }

    showLoading();

    try {
        const reader = new FileReader();
        reader.onload = function(e) {
            selectedImage = e.target.result;
            const preview = document.getElementById('imagePreview');
            const container = document.getElementById('imagePreviewContainer');
            preview.src = selectedImage;
            container.style.display = 'block';
            showToast('图片上传成功', 'success');
            hideLoading();
        };
        reader.onerror = function() {
            throw new Error('读取图片失败');
        };
        reader.readAsDataURL(file);
    } catch (error) {
        console.error('上传图片失败:', error);
        showToast(`上传图片失败: ${error.message}`, 'error');
        hideLoading();
    }
}

function removeImage() {
    selectedImage = null;
    document.getElementById('imagePreview').src = '';
    document.getElementById('imagePreviewContainer').style.display = 'none';
    document.getElementById('imageInput').value = '';
}

// ===== 消息发送 ===
function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function setQuickMessage(message) {
    const input = document.getElementById('messageInput');
    input.value = message;
    autoResize(input);
    input.focus();
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message && !selectedImage) {
        showToast('请输入消息或上传图片', 'error');
        return;
    }
    
    if (isStreaming) {
        showToast('请等待当前回复完成', 'error');
        return;
    }
    
    // 添加用户消息到界面
    appendMessage('user', message, selectedImage);
    
    // 更新会话标题
    if (message) {
        updateChatTitle(message);
    }
    
    // 清空输入
    input.value = '';
    input.style.height = 'auto';
    
    // 显示加载动画
    showLoading();
    
    // 发送请求
    try {
        await streamChat(message);
    } catch (error) {
        console.error('发送消息失败:', error);
        showToast('发送消息失败，请重试', 'error');
        hideLoading();
    }
}

async function streamChat(message) {
    isStreaming = true;
    
    // 创建AI消息容器
    const container = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-robot"></i>
        </div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
    `;
    container.appendChild(messageDiv);
    scrollToBottom();
    
    const bubble = messageDiv.querySelector('.message-bubble');
    
    try {
        // 构建请求体
        const requestBody = {
            message: message,
            thread_id: currentThreadId
        };
        
        const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            fullContent += chunk;
            
            // 更新消息内容
            bubble.innerHTML = formatMessage(fullContent);
            scrollToBottom();
        }
        
        // 添加时间戳
        const contentDiv = messageDiv.querySelector('.message-content');
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        contentDiv.appendChild(timeDiv);
        
        hideLoading();
        showToast('回复完成', 'success');
        
    } catch (error) {
        console.error('流式响应错误:', error);
        bubble.innerHTML = '<span style="color: #ef4444;">抱歉，发生了错误，请重试。</span>';
        hideLoading();
    } finally {
        isStreaming = false;
    }
}

// ===== 清空对话 =====
async function clearCurrentChat() {
    if (!confirm('确定要清空当前对话吗？')) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/chat/clear?thread_id=${currentThreadId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            document.getElementById('messages').innerHTML = '';
            document.getElementById('emptyState').style.display = 'flex';
            showToast('对话已清空');
        } else {
            throw new Error('清空失败');
        }
    } catch (error) {
        console.error('清空对话失败:', error);
        showToast('清空对话失败', 'error');
    }
}

// ===== 侧边栏切换 =====
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

// ===== 加载动画 =====
function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// ===== 点击外部关闭侧边栏 =====
document.addEventListener('click', (e) => {
    const sidebar = document.getElementById('sidebar');
    const menuToggle = document.getElementById('menuToggle');
    
    if (window.innerWidth <= 768 && 
        sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !menuToggle.contains(e.target)) {
        sidebar.classList.remove('open');
    }
});
