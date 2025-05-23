# Generated by Django 5.2.1 on 2025-05-19 00:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='标题')),
                ('file_type', models.CharField(choices=[('txt', '文本文档'), ('doc', 'Word文档'), ('pdf', 'PDF文档'), ('img', '图片文档')], max_length=10, verbose_name='文件类型')),
                ('content', models.TextField(verbose_name='文档内容')),
                ('summary', models.TextField(blank=True, verbose_name='文档摘要')),
                ('keywords', models.TextField(blank=True, verbose_name='关键词')),
                ('entities', models.TextField(blank=True, verbose_name='实体识别结果')),
                ('pos_tags', models.TextField(blank=True, verbose_name='词性标注结果')),
                ('layout_analysis', models.TextField(blank=True, verbose_name='布局分析结果')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': '文档分析',
                'verbose_name_plural': '文档分析',
                'db_table': 'documents',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MedicalQA',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField(verbose_name='问题')),
                ('answer', models.TextField(verbose_name='答案')),
                ('keywords', models.TextField(verbose_name='关键词')),
                ('department', models.CharField(max_length=50, verbose_name='科室')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '医疗问答',
                'verbose_name_plural': '医疗问答',
                'db_table': 'medical_qa',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SystemStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qa_count', models.IntegerField(default=0, verbose_name='问答数量')),
                ('doc_count', models.IntegerField(default=0, verbose_name='文档处理数量')),
                ('accuracy', models.FloatField(default=0.0, verbose_name='系统准确率')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '系统统计',
                'verbose_name_plural': '系统统计',
                'db_table': 'system_stats',
            },
        ),
        migrations.CreateModel(
            name='AnalysisResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('result_type', models.CharField(max_length=50, verbose_name='结果类型')),
                ('result_data', models.TextField(verbose_name='结果数据')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analysis_results', to='core.document')),
            ],
            options={
                'verbose_name': '分析结果',
                'verbose_name_plural': '分析结果',
                'db_table': 'analysis_results',
                'ordering': ['-created_at'],
            },
        ),
    ]
