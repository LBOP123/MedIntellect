import json
import random
from collections import defaultdict

def split_rad_data(data_path, test_ratio=0.2, seed=42):
    # 加载数据
    with open(data_path) as f:
        data = json.load(f)
    
    # 按image_name分组保证同一图片的所有问答一起划分
    img_to_data = defaultdict(list)
    for item in data:
        img_to_data[item['image_name']].append(item)
    
    # 随机划分
    img_names = list(img_to_data.keys())
    random.seed(seed)
    test_size = int(len(img_names) * test_ratio)
    test_img_names = set(random.sample(img_names, test_size))
    
    # 分离数据
    test_data = []
    train_data = []
    
    for img_name in img_names:
        items = img_to_data[img_name]
        if img_name in test_img_names:
            test_data.extend(items)
        else:
            train_data.extend(items)
    
    return {
        'train': train_data,
        'test': test_data
    }

if __name__ == '__main__':
    result = split_rad_data(
        data_path='VQA_RAD Dataset Public.json',
        test_ratio=0.2  # 抽取20%作为测试集
    )
    
    # 保存结果
    with open('rad_train.json', 'w') as f:
        json.dump(result['train'], f, indent=2)
    with open('rad_test.json', 'w') as f:
        json.dump(result['test'], f, indent=2)
    
    # 检查训练集和测试集的图片无重叠
    train_images = {item['image_name'] for item in result['train']}
    test_images = {item['image_name'] for item in result['test']}
    assert len(train_images & test_images) == 0
    
    print(f"训练集样本数: {len(result['train'])}")
    print(f"测试集样本数: {len(result['test'])}")