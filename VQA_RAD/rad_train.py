import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision.models import mobilenet_v2
from tqdm import tqdm
import os

from rad_dataset import RADDataset

# 模型定义
class RADVQAModel(nn.Module):
    def __init__(self, vocab_size, ans_size):
        super().__init__()
        self.cnn = mobilenet_v2(weights="DEFAULT")
        # 冻结CNN参数以加快训练
        for param in self.cnn.parameters():
            param.requires_grad = False
        self.img_proj = nn.Linear(1000, 128)

        self.embed = nn.Embedding(vocab_size, 64)
        self.lstm = nn.LSTM(64, 128, batch_first=True)

        self.classifier = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.5),  # 添加dropout防止过拟合
            nn.Linear(128, ans_size)
        )

    def forward(self, img, ques):
        img_feat = self.img_proj(self.cnn(img))
        txt_feat, _ = self.lstm(self.embed(ques))
        combined = torch.cat([img_feat, txt_feat[:, -1, :]], dim=1)
        return self.classifier(combined)

def train_model(train_data_path, img_dir, num_epochs=10, batch_size=8, learning_rate=1e-4):
    device = torch.device("cpu")  # 使用CPU训练
    
    # 加载数据
    with open(train_data_path) as f:
        train_data = json.load(f)
    
    # 创建数据集和数据加载器
    train_dataset = RADDataset(train_data, img_dir)
    train_loader = DataLoader(
        train_dataset, 
        batch_size=batch_size, 
        shuffle=True,
        num_workers=0  # CPU模式下不使用多进程
    )
    
    # 初始化模型
    model = RADVQAModel(
        vocab_size=len(train_dataset.word2idx),
        ans_size=len(train_dataset.ans2idx)
    ).to(device)
    
    # 优化器和损失函数
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-5)
    criterion = nn.CrossEntropyLoss()
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=2
    )
    
    # 训练循环
    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{num_epochs}", ncols=100)
        
        for images, questions, answers in progress_bar:
            images = images.to(device)
            questions = questions.to(device)
            answers = answers.to(device)
            
            optimizer.zero_grad()
            outputs = model(images, questions)
            loss = criterion(outputs, answers)
            loss.backward()
            
            # 梯度裁剪防止梯度爆炸
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            optimizer.step()
            total_loss += loss.item()
            
            # 更新进度条
            progress_bar.set_postfix(loss=loss.item())
        
        avg_loss = total_loss / len(train_loader)
        print(f"Epoch {epoch + 1} | Avg Loss: {avg_loss:.4f}")
        
        # 更新学习率
        scheduler.step(avg_loss)
    
    # 保存模型和词汇表
    torch.save({
        'model_state': model.state_dict(),
        'word2idx': train_dataset.word2idx,
        'ans2idx': train_dataset.ans2idx
    }, 'rad_vqa_model.pth')
    print("模型已保存为 rad_vqa_model.pth")

def test_model(test_data_path, img_dir, model_path):
    device = torch.device("cpu")
    
    # 加载测试数据
    with open(test_data_path) as f:
        test_data = json.load(f)
    
    # 加载模型
    checkpoint = torch.load(model_path)
    test_dataset = RADDataset(test_data, img_dir)
    test_loader = DataLoader(test_dataset, batch_size=8, shuffle=False)
    
    model = RADVQAModel(
        vocab_size=len(checkpoint['word2idx']),
        ans_size=len(checkpoint['ans2idx'])
    ).to(device)
    model.load_state_dict(checkpoint['model_state'])
    model.eval()
    
    correct = 0
    total = 0
    
    with torch.no_grad():
        for images, questions, answers in tqdm(test_loader, desc="Testing"):
            images = images.to(device)
            questions = questions.to(device)
            answers = answers.to(device)
            
            outputs = model(images, questions)
            _, predicted = torch.max(outputs.data, 1)
            total += answers.size(0)
            correct += (predicted == answers).sum().item()
    
    accuracy = 100 * correct / total
    print(f"测试集准确率: {accuracy:.2f}%")
    return accuracy

if __name__ == '__main__':
    # 训练模型
    train_model(
        train_data_path='rad_train.json',
        img_dir='VQA_RAD Image Folder',
        num_epochs=10,
        batch_size=4,
        learning_rate=1e-4
    )
    
    # 测试模型
    test_model(
        test_data_path='rad_test.json',
        img_dir='VQA_RAD Image Folder',
        model_path='rad_vqa_model.pth'
    )