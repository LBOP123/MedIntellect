// DOM 元素
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');
const fileUpload = document.getElementById('file-upload');
const dropZone = document.getElementById('drop-zone');
const uploadIndicator = document.querySelector('.upload-indicator');

// 事件监听
document.addEventListener('DOMContentLoaded', function () {
    // 发送按钮点击事件
    sendButton.addEventListener('click', sendMessage);

    // 输入框回车事件
    chatInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // 文件上传事件
    fileUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });

    // 拖放文件处理 - 现在应用于整个聊天容器
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', (e) => {
        // 确保只有当鼠标离开整个区域时才移除类
        const rect = dropZone.getBoundingClientRect();
        if (
            e.clientX < rect.left ||
            e.clientX >= rect.right ||
            e.clientY < rect.top ||
            e.clientY >= rect.bottom
        ) {
            dropZone.classList.remove('drag-over');
        }
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });
});

// 聊天功能
function addMessage(message, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    messageDiv.classList.add(isUser ? 'user-message' : 'bot-message');

    const avatarDiv = document.createElement('div');
    avatarDiv.classList.add('message-avatar');
    avatarDiv.innerHTML = `<img src="/static/images/${isUser ? 'user' : 'ai'}-avatar.svg" alt="${isUser ? '用户' : 'AI'}头像">`;

    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');
    contentDiv.textContent = message;

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 发送消息
// 发送消息
async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    addMessage(message, true);
    chatInput.value = '';

    try {
        const response = await fetch('/api/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ message })
        });

        const data = await response.json();
        addMessage(data.response);

        // 显示文本分析结果
        if (data.results && data.results.text_analysis) {
            const resultsContainer = document.querySelector('.results-container');
            resultsContainer.innerHTML = `
                <div class="analysis-results">
                    <h3>文本分析结果</h3>
                    <div class="pos-tagging-results">
                        <h4>词性标注 <i class="fas fa-info-circle" title="名词-红色&#10;动词-绿色&#10;形容词-蓝色&#10;副词-黄色&#10;代词-紫色&#10;数词-棕色&#10;量词-灰色&#10;介词-棕色&#10;连词-灰色&#10;助词-深灰色&#10;标点-黑色"></i></h4>
                        <div class="result-content">${data.results.text_analysis.pos_tagging}</div>
                    </div>
                    <div class="named-entities-results">
                        <h4>实体识别 <i class="fas fa-info-circle" title="疾病-红色&#10;症状-绿色&#10;药品-蓝色&#10;器官-黄色&#10;治疗-紫色&#10;科室-棕色&#10;检查-灰色"></i></h4>
                        <div class="result-content">${data.results.text_analysis.entity_tagging}</div>
                    </div>
                    <div class="summary-results">
                        <h4>文本摘要</h4>
                        <div class="result-content">${data.results.text_analysis.summary}</div>
                    </div>
                </div>
                        `;
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage('抱歉，发生了错误，请稍后重试。');
    }
}

// 文件上传处理
async function handleFileUpload(file) {
    // 显示上传中状态
    addMessage(`正在上传文件: ${file.name}...`, true);

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        });

        const data = await response.json();
        if (data.success) {
            addMessage(`文件 ${file.name} 上传成功！`);
            if (data.results) {
                displayResults(data.results);
            }
        } else {
            addMessage(`文件上传失败：${data.error}`);
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage('文件上传过程中发生错误，请重试。');
    }
}

// 显示分析结果
function displayResults(results) {
    const resultsContainer = document.querySelector('.results-container');
    resultsContainer.innerHTML = '';

    // 添加标题
    const title = document.createElement('h2');
    title.textContent = '分析结果';
    resultsContainer.appendChild(title);

    // 显示文本分析结果
    if (results.text_analysis) {
        const textResults = document.createElement('div');
        textResults.innerHTML = `
            <h3>文本分析</h3>
            <p>词性标注：${results.text_analysis.pos_tagging}</p>
            <p>实体识别：${results.text_analysis.named_entities}</p>
            <p>文档摘要：${results.text_analysis.summary}</p>
        `;
        resultsContainer.appendChild(textResults);
    }

    // 显示词云图
    if (results.wordcloud) {
        const wordcloudContainer = document.createElement('div');
        wordcloudContainer.classList.add('wordcloud-container');
        wordcloudContainer.innerHTML = results.wordcloud;
        resultsContainer.appendChild(wordcloudContainer);
    }

    // 显示t-SNE聚类结果
    if (results.tsne) {
        const tsneContainer = document.createElement('div');
        tsneContainer.classList.add('tsne-container');
        tsneContainer.innerHTML = results.tsne;
        resultsContainer.appendChild(tsneContainer);
    }
}

// 获取CSRF Token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}