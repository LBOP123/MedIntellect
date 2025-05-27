import json
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
from collections import defaultdict
import os
from tqdm import tqdm

class RADDataset(Dataset):
    def __init__(self, data, img_dir, transform=None):
        self.data = data
        self.img_dir = img_dir
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),  # 统一图片大小
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
        ])

        self.word2idx = {'<pad>': 0, '<unk>': 1}
        self.ans2idx = {}
        self._build_vocab()

    def _build_vocab(self):
        # 构建问题词汇表
        word_counter = defaultdict(int)
        for item in self.data:
            for word in item['question'].lower().split():
                word_counter[word] += 1
        for word, cnt in word_counter.items():
            if cnt >= 2:  # 词频阈值
                self.word2idx[word] = len(self.word2idx)

        # 构建答案词汇表
        ans_counter = defaultdict(int)
        for item in self.data:
            # 确保answer字段存在且为字符串类型
            if 'answer' in item and isinstance(item['answer'], str):
                ans = item['answer'].lower()
                ans_counter[ans] += 1
        for ans, cnt in ans_counter.items():
            if cnt >= 1:  # 由于医学数据集答案较为专业，降低阈值
                self.ans2idx[ans] = len(self.ans2idx)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        
        # 加载并处理图像
        img_path = os.path.join(self.img_dir, item['image_name'])
        try:
            image = Image.open(img_path).convert('RGB')
            image = self.transform(image)
        except Exception as e:
            print(f"Error loading image {img_path}: {e}")
            # 如果图像加载失败，返回一个全零张量
            image = torch.zeros((3, 224, 224))

        # 处理问题文本
        words = item['question'].lower().split()[:15]  # 限制问题长度为15个词
        word_ids = [self.word2idx.get(w, 1) for w in words]  # 未知词用1表示
        word_ids += [0] * (15 - len(word_ids))  # 补齐到固定长度

        # 处理答案
        answer = str(item.get('answer', '')).lower()
        answer_id = self.ans2idx.get(answer, 0)

        return image, torch.tensor(word_ids), torch.tensor(answer_id)