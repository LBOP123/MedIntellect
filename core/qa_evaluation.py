import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from .models import SystemStats

def evaluate_qa_performance(csv_file_path):
    """评估问答系统性能
    
    Args:
        csv_file_path: test3.csv文件路径
        
    Returns:
        dict: 包含准确率等评估指标的字典
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file_path)
        
        if 'ask' not in df.columns or 'answer' not in df.columns:
            raise ValueError('CSV文件必须包含ask和answer列')
            
        # 初始化TF-IDF向量化器
        vectorizer = TfidfVectorizer()
        
        # 预处理文本，确保非空且有效
        questions = df['ask'].astype(str).apply(lambda x: x if len(x.strip()) > 0 else 'empty')
        answers = df['answer'].astype(str).apply(lambda x: x if len(x.strip()) > 0 else 'empty')
        
        # 计算问题和答案的TF-IDF向量
        try:
            questions_tfidf = vectorizer.fit_transform(questions)
            answers_tfidf = vectorizer.transform(answers)
        except Exception as e:
            print(f'TF-IDF向量化失败: {str(e)}')
            # 返回默认值
            return {
                'accuracy': 0.0,
                'total_questions': int(len(df)),
                'matched_questions': 0,
                'avg_similarity': 0.0,
                'threshold': 50.0  # 默认阈值
            }
        
        # 计算问题和答案的相似度
        question_similarities = cosine_similarity(questions_tfidf, questions_tfidf)
        answer_similarities = cosine_similarity(answers_tfidf, answers_tfidf)
        
        # 计算综合相似度（考虑问题和答案的相似度）
        similarities = (question_similarities + answer_similarities) / 2
        
        # 计算每个问题的最高相似度
        max_similarities = np.max(similarities, axis=1)
        
        # 动态计算相似度阈值（使用平均相似度作为基准）
        similarity_threshold = np.mean(max_similarities) * 0.8  # 设置为平均值的80%
        
        # 计算准确率（使用动态阈值）
        accuracy = float(np.mean(max_similarities > similarity_threshold) * 100)
        
        # 更新系统统计信息
        stats = SystemStats.objects.first() or SystemStats.objects.create()
        stats.accuracy = round(accuracy, 2)
        stats.save()
        
        # 确保所有数值都转换为Python原生类型
        return {
            'accuracy': round(accuracy, 2),
            'total_questions': int(len(df)),
            'matched_questions': int(sum(max_similarities > similarity_threshold)),
            'avg_similarity': float(round(np.mean(max_similarities) * 100, 2)),
            'threshold': float(round(similarity_threshold * 100, 2))
        }
        
    except Exception as e:
        raise Exception(f'评估问答系统性能时出错: {str(e)}')