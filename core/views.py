from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import MedicalQA, Document, AnalysisResult, SystemStats
import json
import jieba
import jieba.analyse
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.manifold import TSNE
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import base64
from PIL import Image
import numpy as np
from matplotlib import colors
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

        # 使用jieba分词提取关键词
        keywords = jieba.analyse.extract_tags(question, topK=5)

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

        # 根据关键词搜索相关问答
        qa_results = MedicalQA.objects.filter(
            keywords__contains=keywords[0] if keywords else ''
        ).order_by('-created_at')[:5]

        if qa_results:
            response = qa_results[0].answer
        else:
            response = "抱歉，我暂时无法回答这个问题。"

        return JsonResponse({
            'response': response,
            'results': {
                'text_analysis': {
                    'pos_tagging': ' '.join(pos_result),
                    'named_entities': '、'.join(entities),
                    'entity_tagging': ' '.join(entity_result),
                    'summary': summary
                }
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
        import jieba.posseg as pseg
        pos_tags = []
        pos_colors = {
            'n': '#e57373',   # 名词：红色
            'v': '#4caf50',   # 动词：绿色
            'a': '#2196f3',   # 形容词：蓝色
            'd': '#ff9800',   # 副词：橙色
            'r': '#9c27b0',   # 代词：紫色
            'm': '#795548',   # 数词：棕色
            'q': '#607d8b',   # 量词：灰色
            'p': '#795548',   # 介词：棕色
            'c': '#9e9e9e',   # 连词：灰色
            'u': '#757575',   # 助词：深灰色
            'w': '#000000',   # 标点：黑色
        }
        for word, flag in pseg.cut(content):
            color = pos_colors.get(flag[0], '#000000')  # 默认黑色
            pos_tags.append(f'<span style="color: {color}" title="{flag}">{word}</span>')

        # 文本分析结果
        text_analysis = {
            'pos_tagging': ' '.join(pos_tags[:50]),
            'named_entities': ' '.join(keywords),
            'summary': content[:200] + '...' if len(content) > 200 else content
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

        # 创建一个临时文件
        import tempfile
        import zipfile
        import os
        from django.http import FileResponse

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

        
# @csrf_exempt
# def chat_api(request):
#     """聊天API接口"""
#     if request.method != 'POST':
#         return JsonResponse({'error': '只支持POST请求'}, status=405)

#     try:
#         data = json.loads(request.body)
#         question = data.get('message', '')

#         # 使用jieba分词提取关键词
#         keywords = jieba.analyse.extract_tags(question, topK=5)

#         # 医疗实体颜色映射
#         medical_colors = {
#             'disease': '#ff6b6b',    # 疾病-红色
#             'symptom': '#51cf66',    # 症状-绿色
#             'medicine': '#339af0',   # 药品-蓝色
#             'organ': '#ffd43b',      # 器官-黄色
#             'treatment': '#845ef7',  # 治疗-紫色
#             'department': '#a8701a', # 科室-棕色
#             'test': '#868e96',      # 检查-灰色
#             'default': '#212529'     # 默认-黑色
#         }

#         # 医疗实体规则
#         medical_rules = {
#             'disease': ['病', '症', '炎', '癌', '瘤'],
#             'symptom': ['痛', '胀', '肿', '痒', '咳', '喘', '麻', '晕'],
#             'medicine': ['药', '素', '剂', '丸', '片'],
#             'organ': ['胃', '肝', '肺', '肾', '心', '脑', '血'],
#             'treatment': ['手术', '治疗', '化疗', '放疗', '用药'],
#             'department': ['科', '医院', '诊所', '中心'],
#             'test': ['检查', '化验', 'CT', 'MRI', '超声']
#         }

#         # 实体识别和颜色标注
#         entities = []
#         pos_result = []
#         for word, flag in jieba.posseg.cut(question):
#             entity_type = 'default'
#             # 判断实体类型
#             for type_name, keywords in medical_rules.items():
#                 if any(kw in word for kw in keywords):
#                     entity_type = type_name
#                     entities.append(f'{word}({type_name})')
#                     break
            
#             color = medical_colors.get(entity_type, medical_colors['default'])
#             pos_result.append(f'<span style="color: {color}" title="{entity_type}">{word}</span>')

#         # 实体识别（使用jieba词性标注中的名词作为实体）
#         entities = [word for word, flag in jieba.posseg.cut(question) if flag.startswith('n')]

#         # 生成文档摘要（这里使用关键词组合作为简单摘要）
#         summary = '。'.join([kw for kw in keywords])

#         # 根据关键词搜索相关问答
#         qa_results = MedicalQA.objects.filter(
#             keywords__contains=keywords[0] if keywords else ''
#         ).order_by('-created_at')[:5]

#         if qa_results:
#             response = qa_results[0].answer
#         else:
#             response = "抱歉，我暂时无法回答这个问题。"

#         return JsonResponse({
#             'response': response,
#             'results': {
#                 'text_analysis': {
#                     'pos_tagging': ' '.join(pos_result),
#                     'named_entities': '、'.join(entities),
#                     'summary': summary
#                 }
#             }
#         })

#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)
