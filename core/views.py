from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import MedicalQA, Document, AnalysisResult, SystemStats
import json
import jieba
import jieba.analyse
import pandas as pd
import tempfile
import zipfile
import os
from django.http import FileResponse
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
from io import BytesIO
from django.conf import settings
from .tiny_vqa import VQAProcessor

def home(request):
    """首页视图"""
    stats = SystemStats.objects.first()
    if not stats:
        stats = SystemStats.objects.create()
    
    context = {
        'qa_count': stats.qa_count,
        'doc_count': stats.doc_count,
        'accuracy': round(stats.accuracy, 2),
        'vqa_accuracy': round(stats.vqa_accuracy, 2),
        'overall_accuracy': round(stats.overall_accuracy, 2)
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
def evaluate_vqa(request):
    """视觉问答系统评估API接口"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)

    try:
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'error': '未上传文件'}, status=400)

        if not file.name.endswith('.csv'):
            return JsonResponse({'error': '只支持CSV文件'}, status=400)

        # 保存文件到临时目录
        import tempfile
        import os
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, 'Medical_VQA_TestSet.csv')
        
        with open(temp_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # 评估视觉问答系统性能
        from .vqa_evaluation import evaluate_vqa_performance
        results = evaluate_vqa_performance(temp_path)

        # 删除临时文件
        os.remove(temp_path)

        return JsonResponse({
            'success': True,
            'results': results
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def evaluate_qa(request):
    """问答系统评估API接口"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)

    try:
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'error': '未上传文件'}, status=400)

        if not file.name.endswith('.csv'):
            return JsonResponse({'error': '只支持CSV文件'}, status=400)

        # 保存文件到临时目录
        import tempfile
        import os
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, 'test3.csv')
        
        with open(temp_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # 评估问答系统性能
        from .qa_evaluation import evaluate_qa_performance
        results = evaluate_qa_performance(temp_path)

        # 删除临时文件
        os.remove(temp_path)

        return JsonResponse({
            'success': True,
            'results': results
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

#视觉问答
vqa_processor = None

def get_vqa_processor():
    """获取或初始化 VQA 处理器"""
    global vqa_processor
    if vqa_processor is None:
        try:
            # 使用新的RAD模型路径
            model_path = os.path.join(settings.BASE_DIR, 'static/refs/rad_vqa_model.pth')
            if os.path.exists(model_path):
                vqa_processor = VQAProcessor(model_path)
                print("RAD VQA模型初始化成功")
            else:
                print(f"RAD模型文件未找到: {model_path}")
                return None
        except Exception as e:
            print(f"初始化RAD VQA处理器时出错: {e}")
            return None
    return vqa_processor

@csrf_exempt
def visual_qa_api(request):
    """处理视觉问答请求"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)
    
    try:
        # 检查图片和问题是否提供
        if 'image' not in request.FILES or 'question' not in request.POST:
            return JsonResponse({
                'success': False,
                'error': '请提供图片和问题'
            })
        
        image_file = request.FILES['image']
        question = request.POST['question'].strip()
        
        if not question:
            return JsonResponse({
                'success': False,
                'error': '问题不能为空'
            })
        
        # 验证图片文件
        if not image_file.content_type.startswith('image/'):
            return JsonResponse({
                'success': False,
                'error': '请上传有效的图片文件'
            })
        
        # 获取VQA处理器
        processor = get_vqa_processor()
        if processor is None:
            return JsonResponse({
                'success': False,
                'error': 'VQA模型未加载，请检查模型文件'
            })
        
        # 处理图片
        try:
            # 打开并预处理图片
            image = Image.open(BytesIO(image_file.read())).convert('RGB')
            
            # 应用图片变换
            image_tensor = processor.image_transform(image)
            
            # 从VQA模型获取答案
            answer = processor.predict(image_tensor, question)
            
            return JsonResponse({
                'success': True,
                'answer': answer,
                'question': question
            })
            
        except Exception as e:
            print(f"处理VQA请求时出错: {e}")
            return JsonResponse({
                'success': False,
                'error': f'处理图片或问题时发生错误: {str(e)}'
            })
    
    except Exception as e:
        print(f"VQA API错误: {e}")
        return JsonResponse({
            'success': False,
            'error': '服务器内部错误，请稍后重试'
        })

# 添加一个全局变量来存储分析结果
analysis_results = {
    'text_analysis': {},
    'clustering_results': {},
    'latest_document': None
}

@csrf_exempt
def upload_file(request):
    """文件上传API接口 - 修改版本"""
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
        
        # 用于存储纯文本版本（无HTML标签）
        pos_tags_plain = []
        for word, flag in jieba.posseg.cut(content):
            color = pos_colors.get(flag[0], '#212529')
            pos_tags.append(f'<span style="color: {color}" title="{flag}">{word}</span>')
            pos_tags_plain.append(f'{word}/{flag}')

        # 医疗实体规则和颜色映射
        medical_rules = {
            'disease': {'keywords': ['病', '症', '炎', '癌', '瘤'], 'color': '#ff6b6b'},
            'symptom': {'keywords': ['痛', '胀', '肿', '痒', '咳', '喘', '麻', '晕'], 'color': '#51cf66'},
            'medicine': {'keywords': ['药', '素', '剂', '丸', '片'], 'color': '#339af0'},
            'organ': {'keywords': ['胃', '肝', '肺', '肾', '心', '脑', '血'], 'color': '#ffd43b'},
            'treatment': {'keywords': ['手术', '治疗', '化疗', '放疗', '用药'], 'color': '#845ef7'},
            'department': {'keywords': ['科', '医院', '诊所', '中心'], 'color': '#a8701a'},
            'test': {'keywords': ['检查', '化验', 'CT', 'MRI', '超声'], 'color': '#868e96'}
        }

        # 实体识别
        entities = []
        entities_plain = []
        for word, flag in jieba.posseg.cut(content):
            entity_type = None
            for type_name, rule in medical_rules.items():
                if any(kw in word for kw in rule['keywords']):
                    entity_type = type_name
                    entities.append(f'<span style="color: {rule["color"]}" title="{type_name}">{word}</span>')
                    entities_plain.append(f'{word}[{type_name}]')
                    break
            if not entity_type:
                entities.append(word)
                entities_plain.append(word)

        # 生成文档摘要
        summary = '。'.join([kw for kw in keywords])

        # 文本分析结果
        text_analysis = {
            'pos_tagging': ' '.join(pos_tags),
            'named_entities': ' '.join(entities),
            'summary': summary
        }

        # 保存分析结果到全局变量
        global analysis_results
        analysis_results['text_analysis'] = {
            'document_title': file.name,
            'keywords': keywords,
            'pos_tagging_html': ' '.join(pos_tags),
            'pos_tagging_plain': ' '.join(pos_tags_plain),
            'named_entities_html': ' '.join(entities),
            'named_entities_plain': ' '.join(entities_plain),
            'summary': summary,
            'original_content': content,
            'created_at': document.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        analysis_results['latest_document'] = document

        # 更新数据库记录
        document.keywords = ','.join(keywords)
        document.pos_tags = ' '.join(pos_tags_plain[:100])
        document.save()

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
def analyze_batch(request):
    """批量文本分析API接口 - 修复编码问题版本"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)

    try:
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'error': '未上传文件'}, status=400)

        # 尝试多种编码格式读取CSV文件
        def read_csv_with_encoding(file_obj):
            # 常见的编码格式列表
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'latin1', 'cp1252']
            
            for encoding in encodings:
                try:
                    # 重置文件指针
                    file_obj.seek(0)
                    # 读取文件内容并解码
                    content = file_obj.read().decode(encoding)
                    # 使用StringIO创建文件对象供pandas读取
                    from io import StringIO
                    return pd.read_csv(StringIO(content)), encoding
                except (UnicodeDecodeError, UnicodeError):
                    continue
                except Exception as e:
                    # 如果不是编码错误，记录但继续尝试下一个编码
                    print(f"使用编码 {encoding} 读取失败: {str(e)}")
                    continue
            
            # 如果所有编码都失败，抛出异常
            raise ValueError("无法识别文件编码格式，请确保文件是有效的CSV文件")

        # 读取数据集
        try:
            df, used_encoding = read_csv_with_encoding(file)
            print(f"成功使用编码 {used_encoding} 读取文件")
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        
        # 检查是否包含content列
        if 'content' not in df.columns:
            available_columns = ', '.join(df.columns.tolist())
            return JsonResponse({
                'error': f'CSV文件必须包含content列。当前可用列: {available_columns}'
            }, status=400)
            
        # 获取有效文本数据
        texts = df['content'].dropna().astype(str).tolist()
        if not texts:
            return JsonResponse({'error': 'content列为空或没有有效数据'}, status=400)
        
        # 过滤掉空字符串和过短的文本
        texts = [text.strip() for text in texts if text.strip() and len(text.strip()) > 5]
        if not texts:
            return JsonResponse({'error': 'content列中没有有效的文本数据（文本长度需大于5个字符）'}, status=400)

        print(f"有效文本数量: {len(texts)}")

        # 文本预处理和向量化
        try:
            # 使用jieba分词处理中文文本
            processed_texts = []
            for text in texts:
                # 分词
                words = jieba.cut(text)
                processed_text = ' '.join(words)
                processed_texts.append(processed_text)

            # TF-IDF向量化
            vectorizer = TfidfVectorizer(
                max_features=min(1000, len(texts) * 10),  # 动态调整特征数量
                stop_words=None,
                min_df=1,  # 最小文档频率
                max_df=0.95  # 最大文档频率
            )
            X = vectorizer.fit_transform(processed_texts)
            
            if X.shape[1] == 0:
                return JsonResponse({'error': '文本向量化失败，可能是文本内容过于简单或重复'}, status=400)
            
            print(f"向量化完成，特征维度: {X.shape}")

        except Exception as e:
            return JsonResponse({'error': f'文本向量化失败: {str(e)}'}, status=500)

        # t-SNE降维
        try:
            from sklearn.manifold import TSNE
            # 根据数据量调整参数
            n_samples = len(texts)
            perplexity = min(30, max(5, n_samples // 3))  # 动态调整perplexity
            
            tsne = TSNE(
                n_components=2, 
                random_state=42, 
                perplexity=perplexity,
                n_iter=1000,
                learning_rate='auto'
            )
            X_tsne = tsne.fit_transform(X.toarray())
            print(f"t-SNE降维完成")
        except Exception as e:
            return JsonResponse({'error': f't-SNE降维失败: {str(e)}'}, status=500)

        # 聚类分析
        try:
            from sklearn.cluster import KMeans
            n_clusters = min(5, max(2, len(texts) // 10))  # 动态调整聚类数量
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X.toarray())
            print(f"聚类完成，聚类数量: {n_clusters}")
        except Exception as e:
            return JsonResponse({'error': f'聚类分析失败: {str(e)}'}, status=500)

        # 生成t-SNE可视化
        try:
            import matplotlib.pyplot as plt
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            plt.figure(figsize=(12, 8))
            scatter = plt.scatter(
                X_tsne[:, 0], X_tsne[:, 1], 
                alpha=0.7, 
                c=clusters, 
                cmap='tab10',
                s=50
            )
            plt.title('t-SNE Text Clustering Visualization', fontsize=16)
            plt.xlabel('t-SNE Component 1')
            plt.ylabel('t-SNE Component 2')
            plt.colorbar(scatter, label='Cluster')
            plt.grid(True, alpha=0.3)

            # 保存t-SNE图像
            from io import BytesIO
            tsne_buffer = BytesIO()
            plt.savefig(tsne_buffer, format='png', dpi=300, bbox_inches='tight')
            tsne_buffer.seek(0)
            tsne_base64 = base64.b64encode(tsne_buffer.read()).decode('utf-8')
            plt.close()
            print("t-SNE可视化生成完成")
        except Exception as e:
            print(f"t-SNE可视化生成失败: {str(e)}")
            tsne_base64 = None

        # 生成词云图
        try:
            from wordcloud import WordCloud
            
            text_combined = ' '.join(processed_texts)
            
            # 加载背景图像
            background_image = process_image_mask('static/refs/R-C.jpg')
            # 定义字体路径变量
            font_path = 'static/refs/simsun.ttc'
            # 定义颜色列表
            colors = ['#000000', '#FF0080', '#00FF80', '#8000FF', '#FF8000']  # 霓虹配色
    
            # 自定义颜色函数
            def color_func(*args, **kwargs):
                return colors[np.random.randint(0, len(colors))]

            wordcloud = WordCloud(
                width=800,  # 与mask尺寸保持一致
                height=600,  # 与mask尺寸保持一致
                background_color='white',
                max_words=150,  # 减少词数，避免拥挤
                prefer_horizontal=0.9,  # 调整水平偏好
                color_func=color_func,  # 使用自定义颜色函数
                font_path=font_path,
                collocations=False,
                mask=background_image,  # 使用处理后的mask
                max_font_size=60,  # 限制最大字体大小
                min_font_size=10,  # 设置最小字体大小
                relative_scaling=0.5,  # 调整字体大小的相对缩放
                scale=2,  # 提高清晰度
                margin=10  # 设置边距
            ).generate(text_combined)
        
            # 保存词云图像
            wordcloud_buffer = BytesIO()
            wordcloud.to_image().save(wordcloud_buffer, format='PNG')
            wordcloud_buffer.seek(0)
            wordcloud_base64 = base64.b64encode(wordcloud_buffer.read()).decode('utf-8')
            print("词云图生成完成")
        except Exception as e:
            print(f"词云图生成失败: {str(e)}")
            wordcloud_base64 = None

        # 保存聚类结果到全局变量
        global analysis_results
        analysis_results['clustering_results'] = {
            'dataset_name': file.name,
            'total_texts': len(texts),
            'n_clusters': n_clusters,
            'tsne_coordinates': X_tsne.tolist(),
            'cluster_labels': clusters.tolist(),
            'texts': texts,
            'tsne_image': tsne_base64,
            'wordcloud_image': wordcloud_base64,
            'encoding_used': used_encoding,
            'created_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 准备返回结果
        results = {}
        if tsne_base64:
            results['tsne'] = f'<img src="data:image/png;base64,{tsne_base64}" alt="t-SNE Visualization" style="max-width: 100%;">'
        else:
            results['tsne'] = '<div class="error">t-SNE可视化生成失败</div>'
            
        if wordcloud_base64:
            results['wordcloud'] = f'<img src="data:image/png;base64,{wordcloud_base64}" alt="Word Cloud" style="max-width: 100%;">'
        else:
            results['wordcloud'] = '<div class="error">词云图生成失败</div>'

        return JsonResponse({
            'success': True,
            'results': results,
            'info': {
                'total_texts': len(texts),
                'n_clusters': n_clusters,
                'encoding_used': used_encoding
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'批量分析失败: {str(e)}'}, status=500)


@csrf_exempt
def download_results(request):
    """下载分析结果API接口 - 修复版本"""
    if request.method != 'GET':
        return JsonResponse({'error': '只支持GET请求'}, status=405)

    try:
        global analysis_results
        
        # 检查是否有分析结果
        if not analysis_results['text_analysis'] and not analysis_results['clustering_results']:
            return JsonResponse({'error': '没有可下载的分析结果，请先进行文本分析或聚类分析'}, status=404)

        # 创建临时文件 - 修复delete参数问题
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_file.close()

        # 创建ZIP文件
        with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            
            # 添加文本分析结果
            if analysis_results['text_analysis']:
                text_data = analysis_results['text_analysis']
                
                # 原始文档
                if 'original_content' in text_data:
                    zipf.writestr('text_analysis/original_document.txt', text_data['original_content'])
                
                # 关键词
                if 'keywords' in text_data:
                    keywords_content = '\n'.join(text_data['keywords'])
                    zipf.writestr('text_analysis/keywords.txt', keywords_content)
                
                # 词性标注结果（纯文本版本）
                if 'pos_tagging_plain' in text_data:
                    zipf.writestr('text_analysis/pos_tagging.txt', text_data['pos_tagging_plain'])
                
                # 实体识别结果（纯文本版本）
                if 'named_entities_plain' in text_data:
                    zipf.writestr('text_analysis/named_entities.txt', text_data['named_entities_plain'])
                
                # 文档摘要
                if 'summary' in text_data:
                    zipf.writestr('text_analysis/summary.txt', text_data['summary'])
                
                # 分析报告
                report_content = f"""文本分析报告
================

文档名称: {text_data.get('document_title', 'Unknown')}
分析时间: {text_data.get('created_at', 'Unknown')}

关键词数量: {len(text_data.get('keywords', []))}
主要关键词: {', '.join(text_data.get('keywords', [])[:5])}

文档摘要:
{text_data.get('summary', '无摘要')}

详细分析结果请查看其他文件。
"""
                zipf.writestr('text_analysis/analysis_report.txt', report_content)

            # 添加聚类分析结果
            if analysis_results['clustering_results']:
                cluster_data = analysis_results['clustering_results']
                
                # 聚类结果统计
                cluster_summary = f"""聚类分析报告
================

数据集名称: {cluster_data.get('dataset_name', 'Unknown')}
分析时间: {cluster_data.get('created_at', 'Unknown')}
文本总数: {cluster_data.get('total_texts', 0)}
聚类数量: {cluster_data.get('n_clusters', 0)}

聚类分布:
"""
                # 统计每个聚类的文本数量
                cluster_labels = cluster_data.get('cluster_labels', [])
                if cluster_labels:
                    from collections import Counter
                    cluster_counts = Counter(cluster_labels)
                    for cluster_id, count in sorted(cluster_counts.items()):
                        cluster_summary += f"聚类 {cluster_id}: {count} 个文本\n"
                
                zipf.writestr('clustering_analysis/clustering_report.txt', cluster_summary)
                
                # 详细聚类结果
                if 'texts' in cluster_data and 'cluster_labels' in cluster_data:
                    detailed_results = "详细聚类结果\n" + "="*50 + "\n\n"
                    for i, (text, label) in enumerate(zip(cluster_data['texts'], cluster_data['cluster_labels'])):
                        detailed_results += f"文本 {i+1} (聚类 {label}):\n{text[:200]}...\n\n"
                    
                    zipf.writestr('clustering_analysis/detailed_results.txt', detailed_results)
                
                # t-SNE坐标数据
                if 'tsne_coordinates' in cluster_data:
                    import json
                    tsne_data = {
                        'coordinates': cluster_data['tsne_coordinates'],
                        'cluster_labels': cluster_data.get('cluster_labels', [])
                    }
                    zipf.writestr('clustering_analysis/tsne_coordinates.json', json.dumps(tsne_data, indent=2))
                
                # 保存图像文件
                if 'tsne_image' in cluster_data:
                    tsne_image_data = base64.b64decode(cluster_data['tsne_image'])
                    zipf.writestr('clustering_analysis/tsne_visualization.png', tsne_image_data)
                
                if 'wordcloud_image' in cluster_data:
                    wordcloud_image_data = base64.b64decode(cluster_data['wordcloud_image'])
                    zipf.writestr('clustering_analysis/wordcloud.png', wordcloud_image_data)

            # 添加README文件
            readme_content = """分析结果包说明
==================

本压缩包包含以下分析结果：

1. text_analysis/ - 文本分析结果
   - original_document.txt: 原始文档内容
   - keywords.txt: 提取的关键词
   - pos_tagging.txt: 词性标注结果
   - named_entities.txt: 命名实体识别结果
   - summary.txt: 文档摘要
   - analysis_report.txt: 分析报告

2. clustering_analysis/ - 聚类分析结果
   - clustering_report.txt: 聚类分析报告
   - detailed_results.txt: 详细聚类结果
   - tsne_coordinates.json: t-SNE降维坐标数据
   - tsne_visualization.png: t-SNE可视化图像
   - wordcloud.png: 词云图

生成时间: """ + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S') + """

使用说明：
- 所有文本文件使用UTF-8编码
- JSON文件可以用于进一步的数据分析
- PNG图像文件可以直接查看或用于报告
"""
            zipf.writestr('README.txt', readme_content)

        # 读取文件内容并返回响应
        with open(temp_file.name, 'rb') as f:
            file_data = f.read()
        
        # 创建HTTP响应
        response = HttpResponse(
            file_data,
            content_type='application/zip'
        )
        response['Content-Disposition'] = 'attachment; filename="analysis_results.zip"'
        response['Content-Length'] = len(file_data)
        
        # 清理临时文件
        try:
            os.unlink(temp_file.name)
        except:
            pass
        
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'生成下载文件时发生错误: {str(e)}'}, status=500)

def process_image_mask(image_path):
        """处理图片作为mask"""
        # 加载背景图像
        background_image = Image.open(image_path)
        
        # 转换为灰度图
        background_gray = background_image.convert('L')
        
        # 调整大小
        background_gray = background_gray.resize((800, 600))
        
        # 转换为numpy数组
        mask_array = np.array(background_gray)
        
        # 二值化处理：将图像转换为黑白两色
        # 白色区域(值大的区域)用于放置文字，黑色区域(值小的区域)不放置文字
        threshold = 128  # 阈值，可以调整
        mask_array = np.where(mask_array > threshold, 255, 0).astype(np.uint8)
        
        return mask_array