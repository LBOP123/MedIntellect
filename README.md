# MedIntellect - 医疗智能问答系统
## 项目简介
MedIntellect是一个基于Django框架开发的医疗智能问答系统，集成了自然语言处理技术，能够进行医疗实体识别、文本分析和智能问答等功能。系统旨在帮助用户更好地理解医疗文本，提供准确的医疗信息查询服务。

## 主要功能
1. 智能问答
   
   - 支持自然语言问答
   - 医疗实体识别和颜色标注
   - 词性分析和标注
   - 相关问题推荐
2. 文档分析
   
   - 支持多种文件格式（TXT、DOC、DOCX、PDF）
   - 文本分词和关键词提取
   - 医疗实体识别和可视化
   - 词云图生成
3. 实体识别
   
   - 疾病实体（红色）
   - 症状实体（绿色）
   - 药品实体（蓝色）
   - 器官实体（黄色）
   - 治疗实体（紫色）
   - 科室实体（棕色）
   - 检查实体（灰色）
## 技术栈
- 后端：Django
- 前端：HTML、CSS、JavaScript
- 数据处理：jieba分词
- 文件处理：python-docx、PyPDF2
- 可视化：wordcloud
## 安装步骤
1. 克隆项目
```
git clone https://github.com/你的用户名/MedIntellect.git
cd MedIntellect
```
2. 创建虚拟环境
```
python -m venv venv
.\venv\Scripts\activate
```
3. 安装依赖
```
pip install -r requirements.txt
```
6. 初始化数据库
```
python manage.py makemigrations
python manage.py migrate
```
8. 创建超级用户（可选）
```
python manage.py createsuperuser
```
9. 运行开发服务器
```
python manage.py runserver
```
11. 访问系统
- 打开浏览器访问： http://127.0.0.1:8000
- 管理后台： http://127.0.0.1:8000/admin
## 使用说明
### 智能问答
1. 在首页输入框中输入医疗相关问题
2. 系统会自动识别医疗实体并用不同颜色标注
3. 显示分词结果和词性标注
4. 提供相关问题推荐
### 文档分析
1. 点击"文档分析"页面
2. 上传医疗相关文档（支持TXT、DOC、DOCX、PDF格式）
3. 系统自动进行分词和实体识别
4. 生成词云图和文本分析结果
## 注意事项
1. 确保安装了所有必要的Python包
2. Windows环境下可能需要安装Visual C++ Build Tools
3. 建议使用Python 3.8或更高版本
4. 文件上传大小限制为10MB
## 开发计划
- 添加更多医疗实体类型
- 优化实体识别准确率
- 支持更多文件格式
- 添加用户认证系统
- 优化词云图显示效果
## 贡献指南
1. Fork 项目
2. 创建功能分支 ( git checkout -b feature/AmazingFeature )
3. 提交更改 ( git commit -m 'Add some AmazingFeature' )
4. 推送到分支 ( git push origin feature/AmazingFeature )
5. 提交 Pull Request
## 许可证
MIT License

## 联系方式
- 项目维护者：[你的名字]
- 邮箱：[你的邮箱]
- GitHub：[你的GitHub主页]
## 致谢
感谢所有为这个项目做出贡献的开发者！
