from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('create-quiz/', views.create_quiz, name='create_quiz'),
    path('add-questions/<int:quiz_id>/', views.add_questions, name='add_questions'),
    path('quiz/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('my-quizzes/', views.my_quizzes, name='my_quizzes'),
    path('profile/', views.profile, name='profile'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    
    # AI Quiz Generator URLs
    path('ai-quiz-generator/', views.ai_quiz_generator_page, name='ai_quiz_generator'),
    path('generate-ai-quiz/', views.generate_ai_quiz, name='generate_ai_quiz'),
    path('save-ai-quiz/', views.save_ai_quiz, name='save_ai_quiz'),
    path('delete-quiz/<int:quiz_id>/', views.delete_quiz, name='delete_quiz'),
    path('certificate/<int:quiz_id>/', views.export_quiz_certificate, name='export_certificate'),
    # Remove or comment out these lines if they exist:
    # path('delete-quiz/<int:quiz_id>/', views.delete_quiz, name='delete_quiz'),
    # path('delete-question/<int:question_id>/', views.delete_question, name='delete_question'),
]