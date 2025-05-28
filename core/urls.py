from django.urls import path
from . import views

urlpatterns = [
    path('api/evaluate_qa', views.evaluate_qa, name='evaluate_qa'),
    path('api/evaluate_vqa', views.evaluate_vqa, name='evaluate_vqa'),
    path('', views.home, name='home'),
    path('chat/', views.chat, name='chat'),
    path('document-analysis/', views.document_analysis, name='document_analysis'),
    path('about/', views.about, name='about'),
    
    # API endpoints
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/visual_qa/', views.visual_qa_api, name='visual_qa_api'), 
    path('api/analyze-document/', views.analyze_document, name='analyze_document'),
    path('api/analyze-batch/', views.analyze_batch, name='analyze_batch'),
    path('api/upload/', views.upload_file, name='upload_file'),
    path('api/download-results/', views.download_results, name='download_results'),
]