from django.core.management.base import BaseCommand
from core.data_processor import DataProcessor

class Command(BaseCommand):
    help = '从CSV文件导入医疗问答数据到数据库'

    def handle(self, *args, **options):
        processor = DataProcessor()
        
        self.stdout.write(self.style.SUCCESS('开始导入数据...'))
        
        try:
            total_processed = processor.process_all_data()
            self.stdout.write(
                self.style.SUCCESS(f'成功导入 {total_processed} 条记录')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'导入数据时发生错误：{str(e)}')
            )