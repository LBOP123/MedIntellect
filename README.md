# MedIntellect - 智能医疗问答与文档分析系统

## 项目简介
MedIntellect 是一个基于Django框架开发的智能医疗问答和文档分析系统。该系统集成了自然语言处理技术，提供医疗问答、文档分析、文本摘要等功能，旨在提高医疗信息的获取和分析效率。

## 功能特点
- 💬 **智能问答**：提供医疗相关问题的智能回答服务
- 📄 **文档分析**：支持多种格式文档的智能分析
  - 文本文档(TXT)
  - Word文档(DOC)
  - PDF文档
  - 图片文档
- 🔍 **文本分析**：
  - 关键词提取
  - 实体识别
  - 词性标注
  - 文本摘要
- 📊 **系统统计**：实时统计系统使用数据

## 技术栈
- **后端框架**：Django 5.2
- **数据库**：MySQL
- **自然语言处理**：
  - jieba 分词
  - TF-IDF 关键词提取
  - scikit-learn 文本向量化
- **前端技术**：
  - HTML/CSS/JavaScript
  - 数据可视化

## 项目结构
```
MedIntellect/
├── core/                   # 核心应用
│   ├── models.py          # 数据模型
│   ├── views.py           # 视图函数
│   ├── urls.py            # URL配置
│   └── data_processor.py  # 数据处理
├── medintellect/          # 项目配置
├── static/                # 静态文件
├── templates/             # 模板文件
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
```
mysql -u root -e "CREATE DATABASE IF NOT EXISTS medintellect CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```
- 修改 `medintellect/settings.py` 中的数据库配置

4. 数据库迁移
```bash
python manage.py migrate
```
执行数据导入命令，将Data文件夹内的CSV文件数据导入到数据库中。
```
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
4. 系统管理：访问 `http://localhost:8000/admin` 进行后台管理

## 注意事项
- 开发环境下请勿使用默认的SECRET_KEY
- 生产环境部署时请关闭DEBUG模式
- 定期备份数据库

## 许可证
MIT License

## 联系方式
如有问题或建议，请提交Issue或Pull Request。
