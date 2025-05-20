import pandas as pd
import jieba
import jieba.analyse
from .models import MedicalQA
from django.db import transaction
from pathlib import Path

class DataProcessor:
    def __init__(self):
        self.data_dir = Path(__file__).resolve().parent.parent / 'Data'
        self.departments = {
            'Andriatria_男科': '男科',
            'IM_内科': '内科',
            'OAGD_妇产科': '妇产科',
            'Oncology_肿瘤科': '肿瘤科',
            'Pediatric_儿科': '儿科',
            'Surgical_外科': '外科'
        }

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

            # 批量处理数据
            batch_size = 1000
            total_processed = 0
            qa_objects = []

            for _, row in df.iterrows():
                try:
                    # 使用jieba提取关键词
                    keywords = jieba.analyse.extract_tags(
                        str(row['ask']) + ' ' + str(row['answer']),
                        topK=10,
                        withWeight=False
                    )

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
        # 移除特殊字符和多余的空格
        text = str(text).strip()
        text = ' '.join(text.split())
        return text