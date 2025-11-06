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
]