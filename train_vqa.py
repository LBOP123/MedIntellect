import os
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision.models import mobilenet_v2
from PIL import Image
from tqdm import tqdm
import numpy as np

# 数据集定义
class MedicalVQADataset(Dataset):
    def __init__(self, csv_file, img_dir, transform=None, sample_ratio=1.0):
        # 加载数据并采样
        full_data = pd.read_csv(csv_file)
        if sample_ratio < 1.0:
            sample_size = int(len(full_data) * sample_ratio)
            self.data = full_data.sample(n=sample_size, random_state=42).reset_index(drop=True)
            print(f"Sampled {len(self.data)} from {len(full_data)} samples ({sample_ratio*100:.1f}%)")
        else:
            self.data = full_data
            
        self.img_dir = img_dir
        # 优化的图像预处理 - 减小图像尺寸提升速度
        self.transform = transform or transforms.Compose([
            transforms.Resize((128, 128)),  # 从224降到128
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
        ])
        
        # 构建词汇表和答案映射
        self.word2idx = {'<pad>': 0, '<unk>': 1}
        self.ans2idx = {}
        self._build_vocab()

    def _build_vocab(self):
        # 构建问题词汇表
        for question in self.data['Question']:
            for word in question.lower().split():
                if word not in self.word2idx:
                    self.word2idx[word] = len(self.word2idx)

        # 构建答案映射
        for answer in self.data['Answer']:
            if answer not in self.ans2idx:
                self.ans2idx[answer] = len(self.ans2idx)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        img_path = os.path.join(os.path.abspath(self.img_dir), self.data.iloc[idx]['Figure_path'])
        try:
            image = Image.open(img_path).convert('RGB')
        except Exception as e:
            print(f'Error loading image {img_path}: {e}')
            # 如果图片加载失败，返回一个黑色图片
            image = Image.new('RGB', (128, 128), 'black')  # 更新尺寸
        image = self.transform(image)

        question = self.data.iloc[idx]['Question'].lower().split()
        # 减少问题长度限制，提升处理速度
        question_ids = [self.word2idx.get(w, self.word2idx['<unk>']) for w in question]
        question_ids = question_ids[:30] + [0] * (30 - len(question_ids))  # 从50降到30

        answer = self.data.iloc[idx]['Answer']
        answer_id = self.ans2idx[answer]

        return image, torch.tensor(question_ids), torch.tensor(answer_id)

# 优化的模型定义
class MedicalVQAModel(nn.Module):
    def __init__(self, vocab_size, ans_size):
        super().__init__()
        # 使用更轻量的CNN
        self.cnn = mobilenet_v2(weights="DEFAULT")
        # 修改输入层以适应128x128图像
        self.cnn.classifier = nn.Identity()  # 移除分类层
        self.img_proj = nn.Linear(1280, 256)  # 减少特征维度

        # 减少嵌入和LSTM维度
        self.embed = nn.Embedding(vocab_size, 128)  # 从300降到128
        self.lstm = nn.LSTM(128, 256, batch_first=True)  # 从512降到256
        self.dropout = nn.Dropout(0.3)  # 减少dropout比例

        # 更简洁的分类器
        self.classifier = nn.Sequential(
            nn.Linear(512, 256),  # 256+256=512
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, ans_size)
        )

    def forward(self, img, ques):
        img_feat = self.img_proj(self.cnn.features(img).mean([2, 3]))  # 全局平均池化
        txt_feat, _ = self.lstm(self.embed(ques))
        txt_feat = txt_feat[:, -1, :]
        
        combined = torch.cat([img_feat, txt_feat], dim=1)
        combined = self.dropout(combined)
        return self.classifier(combined)

# 早停机制
class EarlyStopping:
    def __init__(self, patience=3, min_delta=0.01):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_score = None
        self.early_stop = False

    def __call__(self, score):
        if self.best_score is None:
            self.best_score = score
        elif score < self.best_score + self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_score = score
            self.counter = 0

# 优化的训练函数
def train(train_csv, test_csv, img_dir, num_epochs=10, batch_size=8, sample_ratio=0.2):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 加载数据集 - 使用20%采样
    train_dataset = MedicalVQADataset(train_csv, img_dir, sample_ratio=sample_ratio)
    # 增加DataLoader的num_workers以加速数据加载
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, 
                            num_workers=4, pin_memory=True if device.type == 'cuda' else False)

    test_dataset = MedicalVQADataset(test_csv, img_dir, sample_ratio=sample_ratio)
    test_loader = DataLoader(test_dataset, batch_size=batch_size,
                           num_workers=4, pin_memory=True if device.type == 'cuda' else False)

    # 初始化模型
    model = MedicalVQAModel(
        vocab_size=len(train_dataset.word2idx),
        ans_size=len(train_dataset.ans2idx)
    ).to(device)

    # 使用更大的学习率加速训练
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs)
    
    # 早停机制
    early_stopping = EarlyStopping(patience=3)

    # 训练循环
    best_acc = 0
    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        progress_bar = tqdm(train_loader, desc=f'Epoch {epoch+1}/{num_epochs}')

        for images, questions, answers in progress_bar:
            images = images.to(device, non_blocking=True)
            questions = questions.to(device, non_blocking=True)
            answers = answers.to(device, non_blocking=True)

            optimizer.zero_grad()
            outputs = model(images, questions)
            loss = criterion(outputs, answers)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            progress_bar.set_postfix({'loss': f'{loss.item():.4f}'})

        avg_loss = total_loss / len(train_loader)
        scheduler.step()

        # 验证
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for images, questions, answers in tqdm(test_loader, desc='Testing'):
                images = images.to(device, non_blocking=True)
                questions = questions.to(device, non_blocking=True)
                answers = answers.to(device, non_blocking=True)

                outputs = model(images, questions)
                _, predicted = torch.max(outputs.data, 1)
                total += answers.size(0)
                correct += (predicted == answers).sum().item()

        accuracy = 100 * correct / total
        print(f'Epoch {epoch+1} - Loss: {avg_loss:.4f}, Accuracy: {accuracy:.2f}%, LR: {scheduler.get_last_lr()[0]:.6f}')

        # 保存最佳模型
        if accuracy > best_acc:
            best_acc = accuracy
            torch.save({
                'model_state_dict': model.state_dict(),
                'word2idx': train_dataset.word2idx,
                'ans2idx': train_dataset.ans2idx,
                'accuracy': best_acc
            }, 'tiny_vqa_model.pth')
            print(f'New best model saved with accuracy: {best_acc:.2f}%')

        # 早停检查
        early_stopping(accuracy)
        if early_stopping.early_stop:
            print(f'Early stopping at epoch {epoch+1}')
            break

    print(f'Training completed. Best accuracy: {best_acc:.2f}%')

if __name__ == '__main__':
    train(
        train_csv='train_2.csv',
        test_csv='test_2.csv',
        img_dir='images_2/figures',
        num_epochs=5,
        batch_size=4,        # 增加批次大小
        sample_ratio=0.2     # 使用20%的数据
    )