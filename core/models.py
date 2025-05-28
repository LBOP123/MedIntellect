from django.db import models

class MedicalQA(models.Model):
    """医疗问答数据模型"""
    title = models.CharField('标题', max_length=200, default='')
    question = models.TextField('问题')
    answer = models.TextField('答案')
    keywords = models.TextField('关键词')
    department = models.CharField('科室', max_length=50)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '医疗问答'
        verbose_name_plural = verbose_name
        db_table = 'medical_qa'
        ordering = ['-created_at']

    def __str__(self):
        return self.question[:50]

class Document(models.Model):
    """文档分析记录模型"""
    DOCUMENT_TYPES = [
        ('txt', '文本文档'),
        ('doc', 'Word文档'),
        ('pdf', 'PDF文档'),
        ('img', '图片文档'),
    ]

    title = models.CharField('标题', max_length=200, default='')
    file_type = models.CharField('文件类型', max_length=10, choices=DOCUMENT_TYPES)
    content = models.TextField('文档内容')
    summary = models.TextField('文档摘要', blank=True)
    keywords = models.TextField('关键词', blank=True)
    entities = models.TextField('实体识别结果', blank=True)
    pos_tags = models.TextField('词性标注结果', blank=True)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '文档分析'
        verbose_name_plural = verbose_name
        db_table = 'documents'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class AnalysisResult(models.Model):
    """分析结果模型"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='analysis_results')
    result_type = models.CharField('结果类型', max_length=50)
    result_data = models.TextField('结果数据')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '分析结果'
        verbose_name_plural = verbose_name
        db_table = 'analysis_results'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.document.title} - {self.result_type}'

class SystemStats(models.Model):
    """系统统计信息"""
    qa_count = models.IntegerField(default=0)  # 问答次数
    doc_count = models.IntegerField(default=0)  # 文档处理数
    accuracy = models.FloatField(default=0.0)  # 文本问答准确率
    vqa_accuracy = models.FloatField(default=0.0)  # 视觉问答准确率
    overall_accuracy = models.FloatField(default=0.0)  # 综合准确率
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '系统统计'
        verbose_name_plural = verbose_name
        db_table = 'system_stats'

    def __str__(self):
        return f'系统统计 - {self.updated_at}'
