// DOM 元素
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');
const fileUpload = document.getElementById('file-upload');
const imageUpload = document.getElementById('image-upload');
const vqaButton = document.getElementById('vqa-button');
const dropZone = document.getElementById('drop-zone');
const uploadIndicator = document.querySelector('.upload-indicator');
const imagePreview = document.getElementById('image-preview');
const previewImg = document.getElementById('preview-img');
const removeImageBtn = document.getElementById('remove-image');

// 全局变量
let uploadedImageFile = null;
let isVQAMode = false;

// 事件监听
document.addEventListener('DOMContentLoaded', function () {
    // 发送按钮点击事件
    sendButton.addEventListener('click', sendMessage);

    // 视觉问答按钮点击事件
    vqaButton.addEventListener('click', startVQA);

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

    // 图片上传事件
    imageUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleImageUpload(file);
        }
    });

    // 移除图片事件
    removeImageBtn.addEventListener('click', removeImage);

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
            // 根据文件类型决定处理方式
            if (file.type.startsWith('image/')) {
                handleImageUpload(file);
            } else {
                handleFileUpload(file);
            }
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
    
    // 如果是HTML内容，直接设置innerHTML，否则设置textContent
    if (message.includes('<')) {
        contentDiv.innerHTML = message;
    } else {
        contentDiv.textContent = message;
    }

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 图片上传处理
async function handleImageUpload(file) {
    // 验证文件类型
    if (!file.type.startsWith('image/')) {
        alert('请上传图片文件（JPG、PNG、GIF等）');
        return;
    }

    // 验证文件大小（限制为5MB）
    if (file.size > 5 * 1024 * 1024) {
        alert('图片文件大小不能超过5MB');
        return;
    }

    try {
        // 显示预览
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImg.src = e.target.result;
            imagePreview.style.display = 'block';
            
            // 保存文件引用
            uploadedImageFile = file;
            
            // 启用视觉问答按钮
            vqaButton.disabled = false;
            vqaButton.title = '点击开始视觉问答';
            
            addMessage(`图片 "${file.name}" 上传成功！现在可以进行视觉问答了。`, false);
        };
        reader.readAsDataURL(file);
        
        addMessage(`正在上传图片: ${file.name}...`, true);
        
    } catch (error) {
        console.error('Error uploading image:', error);
        addMessage('图片上传失败，请重试。', false);
    }
}

// 移除图片
function removeImage() {
    uploadedImageFile = null;
    imagePreview.style.display = 'none';
    previewImg.src = '';
    vqaButton.disabled = true;
    vqaButton.title = '请先上传图片';
    isVQAMode = false;
    
    // 重置输入框提示
    chatInput.placeholder = "请输入您的问题...\n提示词：1)词性标注：2)实体识别：3)文本摘要：4)文本分析：";
    
    addMessage('图片已移除。', false);
}

// 开始视觉问答
function startVQA() {
    if (isVQAMode) {
        return;
    }
    if (!uploadedImageFile) {
        alert('请先上传图片');
        return;
    }
    
    isVQAMode = true;
    chatInput.placeholder = "请输入关于图片的问题...\n例如：这是什么？图片中有什么？描述一下图片内容。";
    chatInput.focus();
    
    addMessage('视觉问答模式已启动！请输入关于图片的问题。', false);
}

// 发送消息（更新后支持视觉问答）
async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    addMessage(message, true);
    chatInput.value = '';

    try {
        let apiUrl = '/api/chat/';
        let requestData = { message };
        
        // 如果是视觉问答模式且有上传的图片
        if (isVQAMode && uploadedImageFile) {
            apiUrl = '/api/visual_qa/';
            
            // 使用FormData发送图片和问题
            const formData = new FormData();
            formData.append('image', uploadedImageFile);
            formData.append('question', message);
            
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: formData
            });
            
            const data = await response.json();
            if (data.success) {
                addMessage(data.answer);
            } else {
                addMessage(`视觉问答失败：${data.error}`);
            }
            return;
        }

        // 普通文本问答
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();
        addMessage(data.response);

        // 显示文本分析结果
        if (data.results && data.results.text_analysis) {
            const resultsContainer = document.querySelector('.results-container');
            let analysisHtml = '';
            if (data.results.op_type !== 'normal') {
                analysisHtml = '<div class="analysis-results"><h3>文本分析结果</h3>';
            }
            if ((data.results.op_type === 'pos' || data.results.op_type === 'analysis') && data.results.text_analysis.pos_tagging) {
                analysisHtml += `<div class="pos-tagging-results">
                                    <h4>词性标注 <i class="fas fa-info-circle" title="名词-红色&#10;动词-绿色&#10;形容词-蓝色&#10;副词-黄色&#10;代词-紫色&#10;数词-棕色&#10;量词-灰色&#10;介词-棕色&#10;连词-灰色&#10;助词-深灰色&#10;标点-黑色"></i></h4>
                                    <div class="result-content">${data.results.text_analysis.pos_tagging}</div>
                                </div>`;
            }

            if ((data.results.op_type === 'entity' || data.results.op_type === 'analysis') && data.results.text_analysis.entity_tagging) {
                analysisHtml += `<div class="named-entities-results">
                                    <h4>实体识别 <i class="fas fa-info-circle" title="疾病-红色&#10;症状-绿色&#10;药品-蓝色&#10;器官-黄色&#10;治疗-紫色&#10;科室-棕色&#10;检查-灰色"></i></h4>
                                    <div class="result-content">${data.results.text_analysis.entity_tagging}</div>
                                </div>`;
            }

            if ((data.results.op_type === 'summary' || data.results.op_type === 'analysis') && data.results.text_analysis.summary) {
                analysisHtml += `<div class="summary-results">
                                    <h4>文本摘要</h4>
                                    <div class="result-content">${data.results.text_analysis.summary}</div>
                                </div>`;
            }

            analysisHtml += '</div>';
            resultsContainer.innerHTML = analysisHtml;
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage('抱歉，发生了错误，请稍后重试。');
    }
}

// 文件上传处理（原有功能保持不变）
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

    // 显示文本分析结果
    if (results.text_analysis) {
        resultsContainer.innerHTML = `
                <div class="analysis-results">
                    <h3>文本分析结果</h3>
                    <div class="pos-tagging-results">
                        <h4>词性标注 <i class="fas fa-info-circle" title="名词-红色&#10;动词-绿色&#10;形容词-蓝色&#10;副词-黄色&#10;代词-紫色&#10;数词-棕色&#10;量词-灰色&#10;介词-棕色&#10;连词-灰色&#10;助词-深灰色&#10;标点-黑色"></i></h4>
                        <div class="result-content">${results.text_analysis.pos_tagging}</div>
                    </div>
                    <div class="named-entities-results">
                        <h4>实体识别 <i class="fas fa-info-circle" title="疾病-红色&#10;症状-绿色&#10;药品-蓝色&#10;器官-黄色&#10;治疗-紫色&#10;科室-棕色&#10;检查-灰色"></i></h4>
                        <div class="result-content">${results.text_analysis.named_entities}</div>
                    </div>
                    <div class="summary-results">
                        <h4>文本摘要</h4>
                        <div class="result-content">${results.text_analysis.summary}</div>
                    </div>
                </div>
                        `;
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