from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from .models import Quiz, Question, QuizAttempt
from .forms import QuizForm, QuestionForm

def home(request):
    quizzes = Quiz.objects.all()
    return render(request, 'home.html', {'quizzes': quizzes})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect('home')

@login_required
def create_quiz(request):
    if request.method == 'POST':
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.created_by = request.user
            quiz.save()
            return redirect('add_questions', quiz_id=quiz.id)
    else:
        form = QuizForm()
    return render(request, 'create_quiz.html', {'form': form})

@login_required
def add_questions(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz
            question.save()
            return redirect('add_questions', quiz_id=quiz.id)
    else:
        form = QuestionForm()
    questions = Question.objects.filter(quiz=quiz)
    return render(request, 'add_questions.html', {
        'form': form, 
        'quiz': quiz, 
        'questions': questions
    })

def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = Question.objects.filter(quiz=quiz)
    
    if request.method == 'POST':
        score = 0
        for question in questions:
            selected_option = request.POST.get(f'question_{question.id}')
            if selected_option and int(selected_option) == question.correct_option:
                score += 1
        
        if request.user.is_authenticated:
            attempt = QuizAttempt(quiz=quiz, user=request.user, score=score)
            attempt.save()
        
        return render(request, 'quiz_result.html', {
            'quiz': quiz,
            'score': score,
            'total': questions.count()
        })
    
    return render(request, 'take_quiz.html', {
        'quiz': quiz,
        'questions': questions
    })

@login_required
def my_quizzes(request):
    quizzes = Quiz.objects.filter(created_by=request.user)
    return render(request, 'my_quizzes.html', {'quizzes': quizzes})