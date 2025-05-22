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

// 处理分析结果的显示
function displayAnalysisResults(results) {
    if (!results || !results.text_analysis) return;

    const textAnalysis = results.text_analysis;
    let analysisHtml = '';

    // 词性标注结果
    if (textAnalysis.pos_tagging) {
        analysisHtml += '<div class="analysis-section">';
        analysisHtml += '<h4>词性标注结果：</h4>';
        analysisHtml += '<div class="pos-result">' + textAnalysis.pos_tagging + '</div>';
        analysisHtml += '</div>';
    }

    // 实体识别结果
    if (textAnalysis.entity_tagging) {
        analysisHtml += '<div class="analysis-section">';
        analysisHtml += '<h4>实体识别结果：</h4>';
        analysisHtml += '<div class="entity-result">' + textAnalysis.entity_tagging + '</div>';
        analysisHtml += '</div>';
    }

    // 文本摘要结果
    if (textAnalysis.summary) {
        analysisHtml += '<div class="analysis-section">';
        analysisHtml += '<h4>文本摘要：</h4>';
        analysisHtml += '<div class="summary-result">' + textAnalysis.summary + '</div>';
        analysisHtml += '</div>';
    }

    // 如果有分析结果，添加到聊天窗口
    if (analysisHtml) {
        var answer_html = '<div class="item item-left">' +
            '<div class="avatar avatar-bot"></div>' +
            '<div class="bubble bubble-left analysis-results">' + analysisHtml + '</div>' +
            '</div>';
        $('.content').append(answer_html);
    }
}

// 点击发送按钮，发请求
$("#chatbotsendbtn").on("click", function () {
    var searchtext = $.trim($('#chattextarea').val());
    if (searchtext === "") {
        alert("请输入您的问题");
        return;
    }

    // 将问题添加到聊天窗口的末尾
    var question_html = '<div class="item item-right">' +
        '<div class="bubble bubble-right">' + searchtext + '</div>' +
        '<div class="avatar avatar-user"></div>' +
        '</div>';
    $('.content').append(question_html);

    // 清空问题文本框
    $('#chattextarea').val('');
    $('#chattextarea').focus();

    // 滚动条置底
    var contentDiv = $('.content');
    contentDiv.scrollTop(contentDiv.prop("scrollHeight"));

    // 处理不同类型的操作
    var opType = "normal"; // 默认为普通问答
    if (searchtext.includes("词性标注：")) {
        opType = "pos";
    } else if (searchtext.includes("实体识别：")) {
        opType = "entity";
    } else if (searchtext.includes("文本摘要：")) {
        opType = "summary";
    } else if (searchtext.includes("文本分析：")) {
        opType = "analysis";
    }

    $.ajax({
        type: "POST",
        url: "/chat_api",
        contentType: "application/json",
        data: JSON.stringify({
            message: searchtext
        }),
        dataType: "json",
        beforeSend: function () {
            $("#chatbotsendbtn").attr("disabled", "disabled");
        },
        complete: function () {
            $("#chatbotsendbtn").removeAttr("disabled");
        },
        success: function (result) {
            // 显示分析结果
            if (result.results && result.results.text_analysis) {
                displayAnalysisResults(result.results);
            }

            // 显示回答（如果是普通问答）
            if (opType === "normal" && result.response) {
                var answer_html = '<div class="item item-left">' +
                    '<div class="avatar avatar-bot"></div>' +
                    '<div class="bubble bubble-left">' + result.response + '</div>' +
                    '</div>';
                $('.content').append(answer_html);
            }

            // 滚动到底部
            contentDiv.scrollTop(contentDiv.prop("scrollHeight"));
        },
        error: function (xhr, status, error) {
            console.error("Error:", error);
            alert("请求失败，请稍后重试");
        }
    });
});