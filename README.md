# MedIntellect - 智能医疗问答与文档分析系统

## 项目简介
MedIntellect 是一个基于Django框架开发的智能医疗问答和文档分析系统。该系统集成了自然语言处理和计算机视觉技术，提供医疗问答、文档分析、医学影像问答等功能，旨在提高医疗信息的获取和分析效率。

## 功能特点
- 💬 **智能问答**：
  - 基于关键词匹配的医疗问答
  - 基于相似度计算的智能推荐
  - 实体识别和标注
- 📄 **文档分析**：支持多种格式文档的智能分析
  - 文本文档(TXT)
  - Word文档(DOC/DOCX)
  - PDF文档
  - 图片文档(JPG/PNG)
- 🔍 **文本分析**：
  - 关键词提取
  - 医疗实体识别（疾病、症状、药物等）
  - 词性标注
  - 文本摘要
  - 文本聚类分析
- 🖼️ **医学影像问答**：
  - 支持放射影像的智能问答
  - 基于VQA模型的图像理解
- 📊 **系统统计**：
  - 问答数据统计
  - 文档分析统计
  - 准确率统计
  - VQA准确率统计

## 技术栈
- **后端框架**：Django 5.2
- **数据库**：MySQL
- **自然语言处理**：
  - jieba 分词
  - TF-IDF 关键词提取
  - scikit-learn 文本向量化
  - 医疗实体识别
- **计算机视觉**：
  - VQA-RAD数据集
  - 医学影像理解模型
- **前端技术**：
  - HTML/CSS/JavaScript
  - 数据可视化
  - Bootstrap响应式设计

## 项目结构
```
MedIntellect/
├── core/                   # 核心应用
│   ├── models.py          # 数据模型
│   ├── views.py           # 视图函数
│   ├── urls.py            # URL配置
│   ├── data_processor.py  # 数据处理
│   ├── tiny_vqa.py       # VQA模型
│   └── qa_evaluation.py   # 问答评估
├── medintellect/          # 项目配置
├── static/                # 静态文件
│   ├── css/              # 样式文件
│   ├── js/               # JavaScript文件
│   ├── images/           # 图片资源
│   └── upload/           # 上传文件
├── templates/             # 模板文件
├── VQA_RAD/              # 医学影像问答数据
└── manage.py             # Django管理脚本
```

## 安装部署
1. 克隆项目
```bash
git clone https://github.com/yourusername/MedIntellect.git
cd MedIntellect
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置数据库
- 创建MySQL数据库
```sql
mysql -u root -e "CREATE DATABASE IF NOT EXISTS medintellect CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```
- 修改 `medintellect/settings.py` 中的数据库配置

4. 数据库迁移
```bash
python manage.py migrate
```
执行数据导入命令，将Data文件夹内的数据导入到数据库中：
```bash
python manage.py import_data
```

5. 创建超级用户（可选）
```bash
python manage.py createsuperuser
```

6. 运行开发服务器
```bash
python manage.py runserver
```

## 使用说明
1. 访问首页：`http://localhost:8000`
2. 医疗问答：点击"智能问答"进入对话界面
3. 文档分析：上传文档进行智能分析
4. 医学影像问答：上传医学影像进行智能问答
5. 系统管理：访问 `http://localhost:8000/admin` 进行后台管理

## 注意事项
- 开发环境下请勿使用默认的SECRET_KEY
- 生产环境部署时请关闭DEBUG模式
- 定期备份数据库
- 确保上传目录具有适当的写入权限
- VQA模型文件较大，请确保有足够的存储空间

## 许可证
MIT License

## 联系方式
如有问题或建议，请提交Issue或Pull Request。
