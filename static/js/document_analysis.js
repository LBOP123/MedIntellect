// DOM 元素
const documentUpload = document.getElementById('document-upload');
const batchUpload = document.getElementById('batch-upload');
const downloadResults = document.getElementById('download-results');

// 事件监听
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
    documentUpload.addEventListener('change', handleDocumentUpload);
    batchUpload.addEventListener('change', handleBatchUpload);
    downloadResults.addEventListener('click', handleDownload);
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

// 批量上传处理
async function handleBatchUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // 检查文件类型
    if (!file.name.toLowerCase().endsWith('.csv')) {
        alert('请上传CSV格式的文件，文件需包含content列');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        // 显示加载状态
        document.querySelector('.clustering-results').innerHTML = '<div class="loading">正在处理文本聚类，请稍候...</div>';

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
        } else {
            alert('批量分析过程中发生错误：' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('上传或分析过程中发生错误，请重试。');
    }
}

// 显示聚类结果
function displayClusteringResults(results) {
    const clusteringResults = document.querySelector('.clustering-results');
    clusteringResults.innerHTML = '<h4>文本聚类结果</h4>';

    // 创建t-SNE可视化容器
    const tsneContainer = document.createElement('div');
    tsneContainer.className = 'tsne-visualization';
    tsneContainer.innerHTML = `
        <h5>t-SNE聚类可视化</h5>
        ${results.tsne}
    `;
    clusteringResults.appendChild(tsneContainer);

    // 创建词云图容器
    const wordcloudContainer = document.createElement('div');
    wordcloudContainer.className = 'wordcloud-visualization';
    wordcloudContainer.innerHTML = `
        <h5>词云图</h5>
        ${results.wordcloud}
    `;
    clusteringResults.appendChild(wordcloudContainer);

    // 切换到聚类结果标签页
    document.querySelector('[data-tab="clustering"]').click();
}

// 显示分析结果
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

// 下载结果处理
async function handleDownload() {
    try {
        const response = await fetch('/api/download-results/', {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'analysis_results.zip';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            alert('下载结果时发生错误，请重试。');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('下载过程中发生错误，请重试。');
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