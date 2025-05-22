import pandas as pd
import jieba
import jieba.analyse
from .models import MedicalQA
from django.db import transaction
from pathlib import Path
from django.db.models import Q
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class DataProcessor:
    def __init__(self):
        self.data_dir = Path(__file__).resolve().parent.parent / 'Data'
        self.stopwords_path = Path(__file__).resolve().parent.parent / 'static' / 'refs' / 'stopwords.txt'
        self.departments = {
            'Andriatria_男科': '男科',
            'IM_内科': '内科',
            'OAGD_妇产科': '妇产科',
            'Oncology_肿瘤科': '肿瘤科',
            'Pediatric_儿科': '儿科',
            'Surgical_外科': '外科'
        }
        # 加载停用词
        self.stopwords = self.load_stopwords()
        # 初始化TF-IDF向量化器
        self.vectorizer = TfidfVectorizer()

    def load_stopwords(self):
        """加载停用词表"""
        try:
            with open(self.stopwords_path, 'r', encoding='utf-8') as f:
                return set([line.strip() for line in f])
        except Exception as e:
            print(f"加载停用词表时发生错误：{str(e)}")
            return set()

    def process_text(self, text):
        """文本预处理：分词、去停用词"""
        if not isinstance(text, str):
            return []
        # 使用jieba分词
        words = jieba.cut(text)
        # 去除停用词
        words = [word for word in words if word not in self.stopwords]
        return words

    def extract_keywords(self, text, topK=10):
        """提取关键词（去除停用词后）"""
        # 使用jieba提取关键词，同时考虑停用词
        keywords = jieba.analyse.extract_tags(
            text,
            topK=topK,
            withWeight=False,
            allowPOS=('n', 'vn', 'v')
        )
        # 过滤停用词
        keywords = [word for word in keywords if word not in self.stopwords]
        return keywords

    def build_index(self, questions):
        """构建文本索引"""
        # 将问题文本转换为TF-IDF向量
        try:
            tfidf_matrix = self.vectorizer.fit_transform(questions)
            return tfidf_matrix
        except Exception as e:
            print(f"构建索引时发生错误：{str(e)}")
            return None

    def search_similar(self, query, tfidf_matrix, top_k=5):
        """搜索相似问题"""
        try:
            # 将查询转换为向量
            query_vec = self.vectorizer.transform([query])
            # 计算相似度
            similarities = cosine_similarity(query_vec, tfidf_matrix)
            # 获取最相似的问题索引
            top_indices = np.argsort(similarities[0])[-top_k:]
            return top_indices[::-1], similarities[0][top_indices[::-1]]
        except Exception as e:
            print(f"搜索相似问题时发生错误：{str(e)}")
            return [], []

    def process_csv_file(self, file_path, department):
        """处理单个CSV文件"""
        try:
            # 读取CSV文件
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # 清理数据
            df = df.fillna('')
            for col in ['ask', 'answer', 'title']:
                if col in df.columns:
                    df[col] = df[col].astype(str).apply(self.clean_text)
            
            # 确保数据框包含必要的列
            required_columns = ['department', 'title', 'ask', 'answer']
            if not all(col in df.columns for col in required_columns):
                print(f"错误：{file_path} 缺少必要的列（department, title, ask, answer）")
                return 0

            # 构建问题索引
            questions = df['ask'].tolist()
            tfidf_matrix = self.build_index(questions)

            # 批量处理数据
            batch_size = 1000
            total_processed = 0
            qa_objects = []

            for idx, row in df.iterrows():
                try:
                    # 对问题进行分词和去停用词处理
                    processed_text = self.process_text(str(row['ask']))
                    # 提取关键词
                    keywords = self.extract_keywords(str(row['ask']))

                    qa_objects.append(MedicalQA(
                        title=str(row['title']) if 'title' in row else '',
                        question=str(row['ask']),
                        answer=str(row['answer']),
                        keywords=','.join(keywords),
                        department=department
                    ))

                    # 当达到批量大小时，执行批量插入
                    if len(qa_objects) >= batch_size:
                        with transaction.atomic():
                            MedicalQA.objects.bulk_create(qa_objects)
                            total_processed += len(qa_objects)
                            print(f'已处理 {total_processed} 条记录')
                            qa_objects = []

                except Exception as e:
                    print(f'处理记录时发生错误：{str(e)}')
                    continue

            # 保存剩余的记录
            if qa_objects:
                try:
                    with transaction.atomic():
                        MedicalQA.objects.bulk_create(qa_objects)
                        total_processed += len(qa_objects)
                        print(f'已处理 {total_processed} 条记录')
                except Exception as e:
                    print(f'保存剩余记录时发生错误：{str(e)}')

            return total_processed

        except Exception as e:
            print(f"处理文件 {file_path} 时发生错误：{str(e)}")
            return 0

    def process_all_data(self):
        """处理所有数据文件"""
        total_processed = 0

        for dept_dir, dept_name in self.departments.items():
            dept_path = self.data_dir / dept_dir
            if not dept_path.exists():
                print(f"警告：目录 {dept_path} 不存在")
                continue

            # 处理该科室下的所有CSV文件
            for csv_file in dept_path.glob('*.csv'):
                print(f"正在处理 {csv_file}...")
                count = self.process_csv_file(csv_file, dept_name)
                total_processed += count
                print(f"成功处理 {count} 条记录")

        print(f"总共处理 {total_processed} 条记录")
        return total_processed

    @staticmethod
    def clean_text(text):
        """清理文本数据"""
        if pd.isna(text) or not isinstance(text, str):
            return ""
        # 移除特殊字符和多余的空格
        text = text.strip()
        # 移除零宽字符
        text = text.replace('\u200b', '')
        # 移除重复的空格
        text = ' '.join(text.split())
        return text