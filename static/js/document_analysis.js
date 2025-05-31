// DOM 元素
const documentUpload = document.getElementById('document-upload');
const batchUpload = document.getElementById('batch-upload');
const downloadResults = document.getElementById('download-results');

// 事件监听
// 在DOMContentLoaded事件中启用批量上传
document.addEventListener('DOMContentLoaded', function() {
    // 标签切换功能
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            // 移除所有活动状态
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            // 添加新的活动状态
            button.classList.add('active');
            document.getElementById(button.dataset.tab).classList.add('active');
        });
    });

    // 文件上传处理
    const documentUpload = document.getElementById('document-upload');
    const batchUpload = document.getElementById('batch-upload');
    const downloadResults = document.getElementById('download-results');
    
    if (documentUpload) {
        documentUpload.addEventListener('change', handleDocumentUpload);
    }
    
    if (batchUpload) {
        batchUpload.addEventListener('change', handleBatchUpload);
    }
    
    if (downloadResults) {
        downloadResults.addEventListener('click', handleDownload);
    }
});

// 文档上传处理
async function handleDocumentUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    
    // 获取选中的分析选项
    const selectedOptions = Array.from(document.querySelectorAll('input[name="analysis_type"]:checked'))
        .map(checkbox => checkbox.value);
    formData.append('analysis_options', JSON.stringify(selectedOptions));

    try {
        // 修改为调用upload_file接口
        const response = await fetch('/api/upload/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        });

        const data = await response.json();
        if (data.success) {
            displayAnalysisResults(data.results);
        } else {
            alert('分析过程中发生错误：' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('上传或分析过程中发生错误，请重试。');
    }
}

// 显示分析结果
function displayAnalysisResults(results) {
    // 检查是否有text_analysis对象
    const textAnalysis = results.text_analysis || results;
    
    // 显示词性标注结果
    if (textAnalysis.pos_tagging) {
        document.querySelector('.pos-tagging-results .result-content').innerHTML = textAnalysis.pos_tagging;
    }

    // 显示实体识别结果
    if (textAnalysis.named_entities) {
        document.querySelector('.ner-results .result-content').innerHTML = textAnalysis.named_entities;
    }

    // 显示文档摘要
    if (textAnalysis.summary) {
        document.querySelector('.summary-results .result-content').innerHTML = textAnalysis.summary;
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

// 修改后的下载功能 - 添加到document_analysis.js中

// 修改下载结果处理函数
async function handleDownload() {
    try {
        // 显示下载状态
        const downloadButton = document.getElementById('download-results');
        const originalText = downloadButton.textContent;
        downloadButton.textContent = '正在生成下载文件...';
        downloadButton.disabled = true;

        const response = await fetch('/api/download-results/', {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        if (response.ok) {
            // 检查响应类型
            const contentType = response.headers.get('Content-Type');
            
            if (contentType && contentType.includes('application/json')) {
                // 如果返回的是JSON，说明有错误
                const errorData = await response.json();
                alert('下载失败: ' + errorData.error);
            } else {
                // 如果返回的是文件，则下载
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'analysis_results.zip';
                a.style.display = 'none';
                document.body.appendChild(a);
                a.click();
                
                // 清理
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                // 显示成功消息
                showNotification('分析结果已成功下载！', 'success');
            }
        } else {
            // 处理HTTP错误
            const errorText = await response.text();
            let errorMessage = '下载失败';
            
            try {
                const errorData = JSON.parse(errorText);
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                errorMessage = `服务器错误 (${response.status})`;
            }
            
            alert(errorMessage);
        }
    } catch (error) {
        console.error('Download error:', error);
        alert('下载过程中发生网络错误，请检查网络连接后重试。');
    } finally {
        // 恢复按钮状态
        const downloadButton = document.getElementById('download-results');
        downloadButton.textContent = originalText;
        downloadButton.disabled = false;
    }
}

// 添加通知显示函数
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" style="margin-left: 10px; background: none; border: none; color: white; cursor: pointer;">&times;</button>
    `;
    
    // 添加样式
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        color: white;
        z-index: 1000;
        max-width: 300px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        ${type === 'success' ? 'background-color: #28a745;' : 
          type === 'error' ? 'background-color: #dc3545;' : 
          'background-color: #17a2b8;'}
    `;
    
    document.body.appendChild(notification);
    
    // 自动移除通知
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// 修改文档上传处理函数，添加更好的错误处理
async function handleDocumentUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // 验证文件类型
    const allowedTypes = ['text/plain', 'application/octet-stream'];
    const fileExtension = file.name.toLowerCase().split('.').pop();
    const allowedExtensions = ['txt', 'text'];
    
    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
        alert('请上传文本文件 (.txt)');
        event.target.value = ''; // 清空文件选择
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    
    // 显示上传状态
    const uploadStatus = document.createElement('div');
    uploadStatus.textContent = '正在分析文档，请稍候...';
    uploadStatus.className = 'upload-status';
    uploadStatus.style.cssText = 'margin: 10px 0; padding: 10px; background: #e3f2fd; border-radius: 4px; color: #1976d2;';
    
    const uploadContainer = document.querySelector('.upload-section');
    uploadContainer.appendChild(uploadStatus);

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
            displayAnalysisResults(data.results);
            showNotification('文档分析完成！', 'success');
            
            // 启用下载按钮
            const downloadButton = document.getElementById('download-results');
            downloadButton.disabled = false;
            downloadButton.textContent = '下载分析结果';
        } else {
            alert('分析过程中发生错误：' + data.error);
            showNotification('文档分析失败', 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('上传或分析过程中发生错误，请重试。');
        showNotification('上传失败', 'error');
    } finally {
        // 移除上传状态
        if (uploadStatus.parentElement) {
            uploadStatus.remove();
        }
    }
}

// 修改批量上传处理函数
async function handleBatchUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // 检查文件类型
    if (!file.name.toLowerCase().endsWith('.csv')) {
        alert('请上传CSV格式的文件，文件需包含content列');
        event.target.value = '';
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    // 显示加载状态
    const clusteringResults = document.querySelector('.clustering-results');
    clusteringResults.innerHTML = `
        <div class="loading" style="text-align: center; padding: 20px;">
            <div style="margin-bottom: 10px;">正在处理文本聚类，请稍候...</div>
            <div style="width: 100%; background: #f0f0f0; border-radius: 10px; overflow: hidden;">
                <div class="progress-bar" style="width: 0%; height: 4px; background: #007bff; transition: width 0.3s;"></div>
            </div>
        </div>
    `;

    try {
        const response = await fetch('/api/analyze-batch/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        });

        const data = await response.json();
        
        if (data.success) {
            displayClusteringResults(data.results);
            showNotification('文本聚类分析完成！', 'success');
            
            // 启用下载按钮
            const downloadButton = document.getElementById('download-results');
            downloadButton.disabled = false;
            downloadButton.textContent = '下载分析结果';
        } else {
            clusteringResults.innerHTML = `<div class="error">批量分析失败: ${data.error}</div>`;
            showNotification('聚类分析失败', 'error');
        }
    } catch (error) {
        console.error('Batch upload error:', error);
        clusteringResults.innerHTML = '<div class="error">上传或分析过程中发生错误，请重试。</div>';
        showNotification('上传失败', 'error');
    }
}

function displayClusteringResults(results, info) {
    const clusteringResults = document.querySelector('.clustering-results');
    
    // 构建信息摘要
    const infoSummary = info ? `
        <div class="analysis-info" style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h5 style="margin-top: 0;">分析摘要</h5>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                <div><strong>文本总数：</strong>${info.total_texts}</div>
                <div><strong>聚类数量：</strong>${info.n_clusters}</div>
                <div><strong>文件编码：</strong>${info.encoding_used}</div>
            </div>
        </div>
    ` : '';
    
    clusteringResults.innerHTML = `
        <h4>文本聚类结果</h4>
        ${infoSummary}
        <div class="results-container">
            <div class="tsne-visualization">
                <h5>📊 t-SNE聚类可视化</h5>
                <div class="image-container">
                    ${results.tsne}
                </div>
                <p class="image-description" style="font-size: 12px; color: #666; margin-top: 10px;">
                    t-SNE将高维文本数据降维到2D空间，相似的文本会聚集在一起，不同颜色代表不同的聚类。
                </p>
            </div>
            <div class="wordcloud-visualization">
                <h5>☁️ 词云图</h5>
                <div class="image-container">
                    ${results.wordcloud}
                </div>
                <p class="image-description" style="font-size: 12px; color: #666; margin-top: 10px;">
                    词云图显示了文本集合中最常出现的词汇，字体大小反映词汇的重要程度。
                </p>
            </div>
        </div>
    `;

    // 添加样式
    const style = document.createElement('style');
    style.textContent = `
        .results-container {
            display: grid;
            gap: 25px;
            margin-top: 20px;
        }
        .image-container {
            text-align: center;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: #fafafa;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .image-container img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .loading-container {
            animation: fadeIn 0.5s ease-in;
        }
        .error-container {
            animation: fadeIn 0.5s ease-in;
        }
        .analysis-info {
            animation: slideIn 0.5s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideIn {
            from { transform: translateY(-10px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .tsne-visualization, .wordcloud-visualization {
            transition: transform 0.2s ease;
        }
        .tsne-visualization:hover, .wordcloud-visualization:hover {
            transform: translateY(-2px);
        }
    `;
    
    if (!document.head.querySelector('#dynamic-styles')) {
        style.id = 'dynamic-styles';
        document.head.appendChild(style);
    }

    // 切换到聚类结果标签页
    const clusteringTab = document.querySelector('[data-tab="clustering"]');
    if (clusteringTab) {
        clusteringTab.click();
    }
}
// 文本问答CSV文件上传和评估处理
document.getElementById('csv-upload').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    // 显示上传中的消息
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messageDiv.innerHTML = `
        <div class="message-avatar">
            <img src="/static/images/ai-avatar.svg" alt="AI头像">
        </div>
        <div class="message-content">
            正在分析文本问答测试集数据，请稍候...
        </div>
    `;
    document.getElementById('chat-messages').appendChild(messageDiv);

    // 发送文件到服务器进行评估
    fetch('/api/evaluate_qa', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const results = data.results;
            // 显示评估结果
            const resultDiv = document.createElement('div');
            resultDiv.className = 'message bot-message';
            resultDiv.innerHTML = `
                <div class="message-avatar">
                    <img src="/static/images/ai-avatar.svg" alt="AI头像">
                </div>
                <div class="message-content">
                    <div class="evaluation-results">
                        <h4>文本问答系统评估结果</h4>
                        <ul>
                            <li>系统准确率：${results.accuracy}%</li>
                            <li>测试问题总数：${results.total_questions}</li>
                            <li>成功匹配数：${results.matched_questions}</li>
                            <li>平均相似度：${results.avg_similarity}%</li>
                            <li>相似度阈值：${results.threshold}%</li>
                        </ul>
                    </div>
                </div>
            `;
            document.getElementById('chat-messages').appendChild(resultDiv);
        } else {
            throw new Error(data.error || '评估失败');
        }
    })
    .catch(error => {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message bot-message';
        errorDiv.innerHTML = `
            <div class="message-avatar">
                <img src="/static/images/ai-avatar.svg" alt="AI头像">
            </div>
            <div class="message-content error">
                评估过程出错：${error.message}
            </div>
        `;
        document.getElementById('chat-messages').appendChild(errorDiv);
    });

    // 清除文件选择
    e.target.value = '';
});

// 视觉问答CSV文件上传和评估处理
document.getElementById('vqa-csv-upload').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    // 显示上传中的消息
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messageDiv.innerHTML = `
        <div class="message-avatar">
            <img src="/static/images/ai-avatar.svg" alt="AI头像">
        </div>
        <div class="message-content">
            正在分析视觉问答测试集数据，请稍候...
        </div>
    `;
    document.getElementById('chat-messages').appendChild(messageDiv);

    // 发送文件到服务器进行评估
    fetch('/api/evaluate_vqa', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const results = data.results;
            // 显示评估结果
            const resultDiv = document.createElement('div');
            resultDiv.className = 'message bot-message';
            resultDiv.innerHTML = `
                <div class="message-avatar">
                    <img src="/static/images/ai-avatar.svg" alt="AI头像">
                </div>
                <div class="message-content">
                    <div class="evaluation-results">
                        <h4>视觉问答系统评估结果</h4>
                        <ul>
                            <li>系统准确率：${results.vqa_accuracy}%</li>
                            <li>测试问题总数：${results.total_questions}</li>
                            <li>成功匹配数：${results.matched_questions}</li>
                            <li>平均相似度：${results.avg_similarity}%</li>
                            <li>相似度阈值：${results.threshold}%</li>
                        </ul>
                    </div>
                </div>
            `;
            document.getElementById('chat-messages').appendChild(resultDiv);
        } else {
            throw new Error(data.error || '评估失败');
        }
    })
    .catch(error => {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message bot-message';
        errorDiv.innerHTML = `
            <div class="message-avatar">
                <img src="/static/images/ai-avatar.svg" alt="AI头像">
                </div>
            <div class="message-content error">
                评估过程出错：${error.message}
            </div>
        `;
        document.getElementById('chat-messages').appendChild(errorDiv);
    });

    // 清除文件选择
    e.target.value = '';
});