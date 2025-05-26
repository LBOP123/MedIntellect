# core/tiny_vqa.py
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models import mobilenet_v2
import re
import os
from PIL import Image

class MedicalVQAModel(nn.Module):
    """与RAD训练代码保持一致的模型定义"""
    def __init__(self, vocab_size, ans_size):
        super().__init__()
        # 使用与训练时相同的CNN结构
        self.cnn = mobilenet_v2(weights="DEFAULT")
        # 注意：这里不冻结参数，因为推理时需要所有参数
        self.img_proj = nn.Linear(1000, 128)  # 与训练代码一致

        # 与训练代码完全一致的文本处理部分
        self.embed = nn.Embedding(vocab_size, 64)  # 64维嵌入
        self.lstm = nn.LSTM(64, 128, batch_first=True)  # 128维LSTM

        # 与训练代码完全一致的分类器
        self.classifier = nn.Sequential(
            nn.Linear(256, 128),  # 128+128=256
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(128, ans_size)
        )

    def forward(self, img, ques):
        # 与训练代码完全一致的前向传播
        img_feat = self.img_proj(self.cnn(img))
        txt_feat, _ = self.lstm(self.embed(ques))
        combined = torch.cat([img_feat, txt_feat[:, -1, :]], dim=1)
        return self.classifier(combined)

class VQAProcessor:
    def __init__(self, model_path='static/refs/rad_vqa_model.pth', device=None):
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.word2idx = None
        self.idx2word = None
        self.ans2idx = None
        self.idx2ans = None
        
        # 图像预处理 - 与RAD训练时保持一致
        self.image_transform = transforms.Compose([
            transforms.Resize((224, 224)),  # RAD使用224x224
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        # 加载模型
        self.load_model(model_path)
    
    def load_model(self, model_path):
        """加载训练好的RAD VQA模型"""
        try:
            if not os.path.exists(model_path):
                print(f"模型文件不存在: {model_path}")
                return False
                
            checkpoint = torch.load(model_path, map_location=self.device)
            
            # 检查checkpoint结构 - RAD模型的结构
            if 'word2idx' not in checkpoint or 'ans2idx' not in checkpoint:
                print("模型文件格式不正确，缺少词汇表信息")
                return False
            
            self.word2idx = checkpoint['word2idx']
            self.ans2idx = checkpoint['ans2idx']
            
            # 构建反向映射
            self.idx2word = {v: k for k, v in self.word2idx.items()}
            self.idx2ans = {v: k for k, v in self.ans2idx.items()}
            
            # 初始化模型
            self.model = MedicalVQAModel(
                vocab_size=len(self.word2idx),
                ans_size=len(self.ans2idx)
            )
            
            # 加载模型权重 - RAD模型使用 'model_state'
            if 'model_state' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state'])
            elif 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                print("模型文件中缺少模型权重")
                return False
                
            self.model.to(self.device)
            self.model.eval()
            
            print(f"RAD VQA模型加载成功，词汇量: {len(self.word2idx)}, 答案数: {len(self.ans2idx)}")
            return True
            
        except Exception as e:
            print(f"加载模型时出错: {e}")
            return False
    
    def is_model_loaded(self):
        """检查模型是否已加载"""
        return self.model is not None
    
    def preprocess_question(self, question):
        """预处理问题文本 - 与RAD训练时保持一致"""
        # 简单的文本清理
        question = question.lower().strip()
        question = re.sub(r'[^\w\s]', '', question)
        
        # 分词（这里简化为按空格分割）
        words = question.split()[:15]  # RAD使用15个词的限制
        
        # 转换为索引
        word_ids = []
        for word in words:
            if word in self.word2idx:
                word_ids.append(self.word2idx[word])
            else:
                word_ids.append(self.word2idx.get('<unk>', 1))  # 使用<unk>标记
        
        # 固定长度为15（与RAD训练时一致）
        if len(word_ids) < 15:
            word_ids.extend([0] * (15 - len(word_ids)))  # 用<pad>填充
        else:
            word_ids = word_ids[:15]
        
        return torch.tensor(word_ids).unsqueeze(0).to(self.device)
    
    def predict(self, image_tensor, question):
        """进行视觉问答预测"""
        if not self.is_model_loaded():
            raise Exception("模型未加载，无法进行预测")
            
        try:
            with torch.no_grad():
                # 确保图像张量格式正确
                if isinstance(image_tensor, Image.Image):
                    image_tensor = self.image_transform(image_tensor)
                
                if len(image_tensor.shape) == 3:
                    image_tensor = image_tensor.unsqueeze(0)
                
                image_tensor = image_tensor.to(self.device)
                
                # 预处理问题
                question_tensor = self.preprocess_question(question)
                
                # 模型预测
                outputs = self.model(image_tensor, question_tensor)
                
                # 获取最可能的答案
                _, predicted_idx = torch.max(outputs, 1)
                predicted_idx = predicted_idx.item()
                
                # 转换为答案文本
                if predicted_idx in self.idx2ans:
                    answer = self.idx2ans[predicted_idx]
                    # 对答案进行后处理，使其更自然
                    answer = self.post_process_answer(answer)
                    return answer
                else:
                    raise Exception("预测结果索引超出范围")
                
        except Exception as e:
            print(f"VQA预测错误: {e}")
            raise e
    
    def post_process_answer(self, answer):
        """对模型输出的答案进行后处理"""
        # 如果答案是单个词，尝试扩展为更自然的句子
        if len(answer.split()) == 1:
            if answer in ['yes', 'no']:
                return '是' if answer == 'yes' else '否'
            elif answer.isdigit():
                return f"数量是 {answer}"
            elif answer in ['normal', 'abnormal']:
                return '正常' if answer == 'normal' else '异常'
        
        # 首字母大写
        if answer and not answer[0].isupper():
            answer = answer.capitalize()
            
        return answer