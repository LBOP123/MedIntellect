from django.contrib import admin
from .models import MedicalQA

@admin.register(MedicalQA)
class MedicalQAAdmin(admin.ModelAdmin):
    list_display = ['id','title', 'question', 'answer', 'keywords', 'department', 'created_at']
    list_filter = ['department', 'created_at']
    search_fields = ['title', 'question', 'answer', 'keywords']
    ordering = ['-created_at']
    readonly_fields = ['keywords']
