import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Avg, Count
from .models import Quiz, Question, QuizAttempt
from .forms import QuizForm, QuestionForm
from .ai_quiz_generator import AIQuizGenerator

# Initialize AI generator
ai_generator = AIQuizGenerator()

def home(request):
    # Get quizzes with actual question counts
    quizzes = Quiz.objects.annotate(question_count=Count('question')).filter(question_count__gt=0)
    
    total_quizzes = Quiz.objects.count()
    total_questions = Question.objects.count()
    total_attempts = QuizAttempt.objects.count()
    total_users = User.objects.count()
    active_quizzes = quizzes.count()
    
    return render(request, 'home.html', {
        'quizzes': quizzes,
        'total_quizzes': total_quizzes,
        'total_questions': total_questions,
        'total_attempts': total_attempts,
        'total_users': total_users,
        'active_quizzes': active_quizzes,
    })

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
    
    # Get actual questions count
    questions = Question.objects.filter(quiz=quiz)
    return render(request, 'add_questions.html', {
        'form': form, 
        'quiz': quiz, 
        'questions': questions
    })

@login_required
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    if request.method == 'POST':
        quiz.delete()
        return redirect('my_quizzes')
    return redirect('my_quizzes')

def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = Question.objects.filter(quiz=quiz)
    
    # Don't allow taking empty quizzes
    if questions.count() == 0:
        return render(request, 'error.html', {
            'message': 'This quiz has no questions yet!'
        })
    
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
    quizzes = Quiz.objects.filter(created_by=request.user).annotate(question_count=Count('question'))
    return render(request, 'my_quizzes.html', {'quizzes': quizzes})

@login_required
def profile(request):
    total_quizzes_taken = QuizAttempt.objects.filter(user=request.user).count()
    total_quizzes_created = Quiz.objects.filter(created_by=request.user).count()
    
    attempts = QuizAttempt.objects.filter(user=request.user)
    if attempts.exists():
        average_score = attempts.aggregate(Avg('score'))['score__avg']
    else:
        average_score = 0
    
    recent_attempts = QuizAttempt.objects.filter(user=request.user).order_by('-attempted_at')[:5]
    
    return render(request, 'profile.html', {
        'total_quizzes_taken': total_quizzes_taken,
        'total_quizzes_created': total_quizzes_created,
        'average_score': average_score,
        'recent_attempts': recent_attempts,
    })

def leaderboard(request, quiz_id=None):
    if quiz_id:
        quiz = get_object_or_404(Quiz, id=quiz_id)
        attempts = QuizAttempt.objects.filter(quiz=quiz).order_by('-score')[:10]
        return render(request, 'quiz_leaderboard.html', {'quiz': quiz, 'attempts': attempts})
    else:
        leaders = User.objects.annotate(
            avg_score=Avg('quizattempt__score'),
            quiz_count=Count('quizattempt')
        ).filter(quiz_count__gt=0).order_by('-avg_score')[:20]
        return render(request, 'global_leaderboard.html', {'leaders': leaders})
    
def ai_quiz_generator_page(request):
    return render(request, 'ai_quiz_generator.html')

def generate_ai_quiz(request):
    """API endpoint to generate quiz using AI"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            topic = data.get('topic', '').strip()
            difficulty = data.get('difficulty', 'medium')
            num_questions = int(data.get('num_questions', 5))
            
            if not topic:
                return JsonResponse({'error': 'Topic is required'}, status=400)
            
            if num_questions < 1 or num_questions > 20:
                return JsonResponse({'error': 'Number of questions must be between 1 and 20'}, status=400)
            
            # Generate quiz using AI
            ai_quiz = ai_generator.generate_quiz(topic, difficulty, num_questions)
            
            return JsonResponse({
                'success': True,
                'quiz': ai_quiz
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

def save_ai_quiz(request):
    """Save AI-generated quiz to database"""
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            data = json.loads(request.body)
            quiz_data = data.get('quiz')
            topic = data.get('topic', 'general knowledge')
            difficulty = data.get('difficulty', 'medium')
            
            if not quiz_data or 'questions' not in quiz_data:
                return JsonResponse({'error': 'Invalid quiz data'}, status=400)
            
            questions = quiz_data['questions']
            if len(questions) == 0:
                return JsonResponse({'error': 'No questions generated'}, status=400)
            
            # Validate each question has exactly 4 options
            for i, q_data in enumerate(questions):
                options = q_data.get('options', [])
                if len(options) != 4:
                    return JsonResponse({
                        'error': f'Question {i+1} must have exactly 4 options, but got {len(options)}'
                    }, status=400)
                
                # Validate correct answer is within range
                correct_answer = q_data.get('correct_answer')
                if correct_answer not in [1, 2, 3, 4]:
                    return JsonResponse({
                        'error': f'Question {i+1} has invalid correct answer: {correct_answer}'
                    }, status=400)
            
            # Create quiz
            quiz = Quiz(
                title=quiz_data['quiz_title'],
                description=f"AI-generated quiz about {topic}",
                difficulty=difficulty,
                number_of_questions=len(questions),
                created_by=request.user
            )
            quiz.save()
            
            # Create questions
            for q_data in questions:
                question = Question(
                    quiz=quiz,
                    question_text=q_data['question_text'],
                    option1=q_data['options'][0],
                    option2=q_data['options'][1],
                    option3=q_data['options'][2],
                    option4=q_data['options'][3],
                    correct_option=q_data['correct_answer'],  # Already 1-based
                    explanation=q_data.get('explanation', '')
                )
                question.save()
            
            return JsonResponse({
                'success': True,
                'quiz_id': quiz.id,
                'message': f'Quiz saved successfully with {len(questions)} questions!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Authentication required'}, status=401)

@login_required


@login_required
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    if request.method == 'POST':
        quiz_title = quiz.title
        quiz.delete()
        messages.success(request, f'Quiz "{quiz_title}" has been deleted successfully!')
        return redirect('my_quizzes')
    return redirect('my_quizzes')

def delete_question(request, question_id):
    """Delete a specific question"""
    question = get_object_or_404(Question, id=question_id, quiz__created_by=request.user)
    quiz_id = question.quiz.id
    question.delete()
    return redirect('add_questions', quiz_id=quiz_id)

def quiz_detail(request, quiz_id):
    """View quiz details"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = Question.objects.filter(quiz=quiz)
    
    return render(request, 'quiz_detail.html', {
        'quiz': quiz,
        'questions': questions
    })