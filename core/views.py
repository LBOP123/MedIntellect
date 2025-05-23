from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import MedicalQA, Document, AnalysisResult, SystemStats
import json
import jieba
import jieba.analyse
import pandas as pd
from django.db.models import Q
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.manifold import TSNE
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import base64
from PIL import Image
import numpy as np
import matplotlib
matplotlib.use('Agg') 

def home(request):
    """首页视图"""
    stats = SystemStats.objects.first()
    if not stats:
        stats = SystemStats.objects.create()
    
    context = {
        'qa_count': stats.qa_count,
        'doc_count': stats.doc_count,
        'accuracy': round(stats.accuracy, 2)
    }
    return render(request, 'home.html', context)

def chat(request):
    """聊天页面视图"""
    return render(request, 'chat.html')

def document_analysis(request):
    """文档分析页面视图"""
    return render(request, 'document_analysis.html')

def about(request):
    """关于页面视图"""
    return render(request, 'about.html')

@csrf_exempt
def chat_api(request):
    """聊天API接口"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)

    try:
        data = json.loads(request.body)
        question = data.get('message', '')
        
        # 判断操作类型
        op_type = 'normal'  # 默认为普通问答
        if '词性标注' in question:
            op_type = 'pos'
            question = question.replace('词性标注：', '').strip()
        elif '实体识别' in question:
            op_type = 'entity'
            question = question.replace('实体识别：', '').strip()
        elif '文本摘要' in question:
            op_type = 'summary'
            question = question.replace('文本摘要：', '').strip()
        elif '文本分析' in question:
            op_type = 'analysis'
            question = question.replace('文本分析：', '').strip()

        # 初始化数据处理器
        from .data_processor import DataProcessor
        processor = DataProcessor()

        # 对问题进行预处理（分词、去停用词）
        processed_text = processor.process_text(question)
        
        # 提取关键词（已去除停用词）
        keywords = processor.extract_keywords(question, topK=2)

        # 词性标注
        pos_tags = []
        pos_colors = {
            'n': '#ff6b6b',   # 名词-红色
            'v': '#51cf66',   # 动词-绿色
            'a': '#339af0',   # 形容词-蓝色
            'd': '#ffd43b',   # 副词-黄色
            'r': '#845ef7',   # 代词-紫色
            'm': '#a8701a',   # 数词-棕色
            'q': '#868e96',   # 量词-灰色
            'p': '#a8701a',   # 介词-棕色
            'c': '#868e96',   # 连词-灰色
            'u': '#495057',   # 助词-深灰色
            'w': '#212529'    # 标点-黑色
        }
        
        pos_result = []
        for word, flag in jieba.posseg.cut(question):
            color = pos_colors.get(flag[0], '#212529')
            pos_result.append(f'<span style="color: {color}" title="{flag}">{word}</span>')

        # 医疗实体规则和颜色映射
        medical_rules = {
            'disease': {'keywords': ['病', '症', '炎', '癌', '瘤'], 'color': '#ff6b6b'},      # 疾病-红色
            'symptom': {'keywords': ['痛', '胀', '肿', '痒', '咳', '喘', '麻', '晕'], 'color': '#51cf66'},  # 症状-绿色
            'medicine': {'keywords': ['药', '素', '剂', '丸', '片'], 'color': '#339af0'},    # 药品-蓝色
            'organ': {'keywords': ['胃', '肝', '肺', '肾', '心', '脑', '血'], 'color': '#ffd43b'},     # 器官-黄色
            'treatment': {'keywords': ['手术', '治疗', '化疗', '放疗', '用药'], 'color': '#845ef7'}, # 治疗-紫色
            'department': {'keywords': ['科', '医院', '诊所', '中心'], 'color': '#a8701a'},   # 科室-棕色
            'test': {'keywords': ['检查', '化验', 'CT', 'MRI', '超声'], 'color': '#868e96'}    # 检查-灰色
        }

        # 实体识别
        entities = []
        entity_result = []
        for word, flag in jieba.posseg.cut(question):
            entity_type = None
            for type_name, rule in medical_rules.items():
                if any(kw in word for kw in rule['keywords']):
                    entity_type = type_name
                    entities.append(f'<span style="color: {rule["color"]}" title="{type_name}">{word}</span>')
                    entity_result.append(f'<span style="color: {rule["color"]}" title="{type_name}">{word}</span>')
                    break
            if not entity_type:
                entity_result.append(word)

        # 生成文档摘要（这里使用关键词组合作为简单摘要）
        summary = '。'.join([kw for kw in keywords])

        # 根据操作类型设置响应内容
        response = ""
        if op_type == 'normal':
            # 首先尝试关键词匹配，这样更快
            if keywords:
                qa_results = MedicalQA.objects.filter(keywords__contains=keywords[0]).order_by('-created_at').first()
                if qa_results:
                    response = qa_results.answer
                else:
                    # 如果关键词匹配失败，再尝试相似度匹配
                    all_qa = MedicalQA.objects.all()[:1000]  # 限制数量提高性能
                    questions = [qa.question for qa in all_qa]
                    
                    # 构建问题索引
                    tfidf_matrix = processor.build_index(questions)
                    
                    # 搜索相似问题，降低相似度要求
                    if tfidf_matrix is not None:
                        top_indices, similarities = processor.search_similar(question, tfidf_matrix, top_k=1)
                        if len(top_indices) > 0 and similarities[0] > 0.3:  # 降低相似度阈值
                            qa_results = all_qa[int(top_indices[0])]
                            response = qa_results.answer
                        else:
                            response = "抱歉，我暂时无法回答这个问题。"
                    else:
                        response = "抱歉，我暂时无法回答这个问题。"

            # 更新系统统计数据
            stats = SystemStats.objects.first() or SystemStats.objects.create()
            stats.qa_count += 1
            stats.save()

        elif op_type == 'pos':
            response = "词性标注已完成，请查看下方标注结果。"
        elif op_type == 'entity':
            response = "实体识别已完成，请查看下方识别结果。"
        elif op_type == 'summary':
            response = "文本摘要已生成，请查看下方摘要内容。"
        elif op_type == 'analysis':
            response = "文本分析已完成，请查看下方分析结果。"

        # 根据操作类型返回不同的结果
        text_analysis = {}
        if op_type == 'pos':
            # 只进行词性标注
            pos_result = []
            for word, flag in jieba.posseg.cut(question):
                color = pos_colors.get(flag[0], '#212529')
                pos_result.append(f'<span style="color: {color}" title="{flag}">{word}</span>')
            text_analysis['pos_tagging'] = ' '.join(pos_result)
        elif op_type == 'entity':
            # 只进行实体识别
            entity_result = []
            for word, flag in jieba.posseg.cut(question):
                entity_type = None
                for type_name, rule in medical_rules.items():
                    if any(kw in word for kw in rule['keywords']):
                        entity_type = type_name
                        entity_result.append(f'<span style="color: {rule["color"]}" title="{type_name}">{word}</span>')
                        break
                if not entity_type:
                    entity_result.append(word)
            text_analysis['entity_tagging'] = ' '.join(entity_result)
        elif op_type == 'summary':
            # 只生成文本摘要
            summary = '。'.join([kw for kw in keywords])
            text_analysis['summary'] = summary
        elif op_type == 'analysis':
            # 进行完整的文本分析
            # 词性标注
            pos_result = []
            for word, flag in jieba.posseg.cut(question):
                color = pos_colors.get(flag[0], '#212529')
                pos_result.append(f'<span style="color: {color}" title="{flag}">{word}</span>')
            text_analysis['pos_tagging'] = ' '.join(pos_result)
            
            # 实体识别
            entity_result = []
            for word, flag in jieba.posseg.cut(question):
                entity_type = None
                for type_name, rule in medical_rules.items():
                    if any(kw in word for kw in rule['keywords']):
                        entity_type = type_name
                        entity_result.append(f'<span style="color: {rule["color"]}" title="{type_name}">{word}</span>')
                        break
                if not entity_type:
                    entity_result.append(word)
            text_analysis['entity_tagging'] = ' '.join(entity_result)
            
            # 文本摘要
            summary = '。'.join([kw for kw in keywords])
            text_analysis['summary'] = summary

        return JsonResponse({
            'response': response,
            'results': {
                'op_type': op_type,
                'text_analysis': text_analysis
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def analyze_document(request):
    """文档分析API接口"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)

    try:
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'error': '未上传文件'}, status=400)

        # 读取文件内容
        content = file.read().decode('utf-8')

        # 创建文档记录
        document = Document.objects.create(
            title=file.name,
            file_type='txt',  # 这里简化处理，假设都是文本文件
            content=content
        )

        # 分词和关键词提取
        words = jieba.cut(content)
        text = ' '.join(words)
        keywords = jieba.analyse.extract_tags(content, topK=10)

        # 词性标注
        import jieba.posseg as pseg
        pos_tags = []
        for word, flag in pseg.cut(content):
            pos_tags.append(f'{word}/{flag}')

        # 更新文档分析结果
        document.keywords = ','.join(keywords)
        document.pos_tags = ' '.join(pos_tags[:100])  # 只保存前100个结果
        document.save()

        # 更新系统统计
        stats = SystemStats.objects.first() or SystemStats.objects.create()
        stats.doc_count += 1
        stats.save()

        return JsonResponse({
            'success': True,
            'results': {
                'keywords': keywords,
                'pos_tagging': pos_tags[:50],  # 只返回前50个结果
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def analyze_batch(request):
    """批量文本分析API接口"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)

    try:
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'error': '未上传文件'}, status=400)

        # 读取数据集
        df = pd.read_csv(file)
        texts = df['content'].tolist()  # 假设数据集中有content列

        # 文本向量化
        vectorizer = TfidfVectorizer(max_features=1000)
        X = vectorizer.fit_transform(texts)

        # t-SNE降维
        tsne = TSNE(n_components=2)
        X_tsne = tsne.fit_transform(X.toarray())

        # 生成t-SNE可视化
        plt.figure(figsize=(10, 10))
        plt.scatter(X_tsne[:, 0], X_tsne[:, 1], alpha=0.5)
        plt.title('t-SNE Visualization')

        # 将图像转换为base64字符串
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png')
        img_buf.seek(0)
        img_base64 = base64.b64encode(img_buf.read()).decode('utf-8')
        plt.close()

        # 生成词云图
        text = ' '.join(texts)
        mask = np.array(Image.open('static/images/cat.jpg'))
        wordcloud = WordCloud(width=1200, height=600, background_color='white', mask=mask, mode='RGB', font_path='simhei.ttf', prefer_horizontal=0.9)
        wordcloud.generate(text)
    
        # 将词云图转换为base64字符串
        img_buf = io.BytesIO()
        wordcloud.to_image().save(img_buf, format='PNG')
        img_buf.seek(0)
        wordcloud_base64 = base64.b64encode(img_buf.read()).decode('utf-8')

        return JsonResponse({
            'success': True,
            'results': {
                'tsne': f'<img src="data:image/png;base64,{img_base64}" alt="t-SNE Visualization">',
                'wordcloud': f'<img src="data:image/png;base64,{wordcloud_base64}" alt="Word Cloud">'
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

        
@csrf_exempt
def upload_file(request):
    """文件上传API接口"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)

    try:
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'error': '未上传文件'}, status=400)

        # 读取文件内容
        content = file.read().decode('utf-8')

        # 创建文档记录
        document = Document.objects.create(
            title=file.name,
            file_type=file.name.split('.')[-1].lower(),
            content=content
        )

        # 分词和关键词提取
        words = jieba.cut(content)
        text = ' '.join(words)
        keywords = jieba.analyse.extract_tags(content, topK=10)

        # 词性标注（添加颜色样式）
        # import jieba.posseg as pseg
        pos_tags = []
        pos_colors = {
            'n': '#ff6b6b',   # 名词-红色
            'v': '#51cf66',   # 动词-绿色
            'a': '#339af0',   # 形容词-蓝色
            'd': '#ffd43b',   # 副词-黄色
            'r': '#845ef7',   # 代词-紫色
            'm': '#a8701a',   # 数词-棕色
            'q': '#868e96',   # 量词-灰色
            'p': '#a8701a',   # 介词-棕色
            'c': '#868e96',   # 连词-灰色
            'u': '#495057',   # 助词-深灰色
            'w': '#212529'    # 标点-黑色
        }
        for word, flag in jieba.posseg.cut(content):
            color = pos_colors.get(flag[0], '#212529')  # 默认黑色
            pos_tags.append(f'<span style="color: {color}" title="{flag}">{word}</span>')

        # 医疗实体规则和颜色映射
        medical_rules = {
            'disease': {'keywords': ['病', '症', '炎', '癌', '瘤'], 'color': '#ff6b6b'},      # 疾病-红色
            'symptom': {'keywords': ['痛', '胀', '肿', '痒', '咳', '喘', '麻', '晕'], 'color': '#51cf66'},  # 症状-绿色
            'medicine': {'keywords': ['药', '素', '剂', '丸', '片'], 'color': '#339af0'},    # 药品-蓝色
            'organ': {'keywords': ['胃', '肝', '肺', '肾', '心', '脑', '血'], 'color': '#ffd43b'},     # 器官-黄色
            'treatment': {'keywords': ['手术', '治疗', '化疗', '放疗', '用药'], 'color': '#845ef7'}, # 治疗-紫色
            'department': {'keywords': ['科', '医院', '诊所', '中心'], 'color': '#a8701a'},   # 科室-棕色
            'test': {'keywords': ['检查', '化验', 'CT', 'MRI', '超声'], 'color': '#868e96'}    # 检查-灰色
        }

        # 实体识别
        entities = []
        for word, flag in jieba.posseg.cut(content):
            entity_type = None
            for type_name, rule in medical_rules.items():
                if any(kw in word for kw in rule['keywords']):
                    entity_type = type_name
                    entities.append(f'<span style="color: {rule["color"]}" title="{type_name}">{word}</span>')
                    break
            if not entity_type:
                entities.append(word)

        # 生成文档摘要（这里使用关键词组合作为简单摘要）
        summary = '。'.join([kw for kw in keywords])

        # 文本分析结果
        text_analysis = {
            'pos_tagging': ' '.join(pos_tags),
            'named_entities': ' '.join(entities),
            'summary': summary
        }

        # 更新系统统计
        stats = SystemStats.objects.first() or SystemStats.objects.create()
        stats.doc_count += 1
        stats.save()

        return JsonResponse({
            'success': True,
            'results': {
                'text_analysis': text_analysis
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


# 创建一个临时文件
import tempfile
import zipfile
import os
from django.http import FileResponse

@csrf_exempt
def download_results(request):
    """下载分析结果API接口"""
    if request.method != 'GET':
        return JsonResponse({'error': '只支持GET请求'}, status=405)

    try:
        # 获取最近的分析结果
        latest_document = Document.objects.order_by('-created_at').first()
        if not latest_document:
            return JsonResponse({'error': '没有可下载的分析结果'}, status=404)


        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_file.close()

        # 创建ZIP文件
        with zipfile.ZipFile(temp_file.name, 'w') as zipf:
            # 添加文档内容
            zipf.writestr('document.txt', latest_document.content)
            
            # 添加分析结果
            if latest_document.keywords:
                zipf.writestr('keywords.txt', latest_document.keywords)
            
            if latest_document.pos_tags:
                zipf.writestr('pos_tags.txt', latest_document.pos_tags)
            
            # 添加元数据
            metadata = f"文件名: {latest_document.title}\n"
            metadata += f"文件类型: {latest_document.file_type}\n"
            metadata += f"创建时间: {latest_document.created_at}\n"
            zipf.writestr('metadata.txt', metadata)

        # 返回ZIP文件
        response = FileResponse(open(temp_file.name, 'rb'))
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = 'attachment; filename=analysis_results.zip'
        
        # 设置回调以删除临时文件
        def delete_temp_file(response):
            os.unlink(temp_file.name)
            return response
        
        response.close = delete_temp_file.__get__(response)
        
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

        