from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Sum
from django.http import JsonResponse
import json
from .models import Quiz, Question, QuizAttempt
from .forms import QuizForm, QuestionForm
from .ai_quiz_generator import ai_generator
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.units import inch
from reportlab.lib import colors
from django.http import HttpResponse
import os


def home(request):
    quizzes = Quiz.objects.all()
    # Enhanced statistics
    total_quizzes = Quiz.objects.count()
    total_questions = Question.objects.count()
    total_attempts = QuizAttempt.objects.count()
    total_users = User.objects.count()
    active_quizzes = Quiz.objects.filter(question__isnull=False).distinct().count()
    
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

@login_required
def delete_quiz(request, quiz_id):
    """Delete a quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    quiz.delete()
    return redirect('my_quizzes')

@login_required
def profile(request):
    # Calculate user statistics
    total_quizzes_taken = QuizAttempt.objects.filter(user=request.user).count()
    total_quizzes_created = Quiz.objects.filter(created_by=request.user).count()
    
    # Calculate average score
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
        # Quiz-specific leaderboard
        quiz = get_object_or_404(Quiz, id=quiz_id)
        attempts = QuizAttempt.objects.filter(quiz=quiz).order_by('-score', 'attempted_at')[:10]
        return render(request, 'quiz_leaderboard.html', {'quiz': quiz, 'attempts': attempts})
    else:
        # Global leaderboard - users with best average scores
        from django.db.models import Avg, Count, Sum
        
        leaders = User.objects.annotate(
            quiz_count=Count('quizattempt'),
            avg_score=Avg('quizattempt__score'),
            total_score=Sum('quizattempt__score')
        ).filter(quiz_count__gt=0).order_by('-avg_score', '-quiz_count')[:20]
        
        return render(request, 'global_leaderboard.html', {'leaders': leaders})

# AI QUIZ GENERATOR FUNCTIONS
def ai_quiz_generator_page(request):
    """Render AI quiz generator page"""
    return render(request, 'ai_quiz_generator.html')

def generate_ai_quiz(request):
    """API endpoint to generate quiz using AI"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            topic = data.get('topic', '').strip()
            difficulty = data.get('difficulty', 'medium')
            num_questions = int(data.get('num_questions', 5))
            
            print(f"🎯 VIEWS: Request received - {num_questions} questions about '{topic}'")
            
            if not topic:
                return JsonResponse({'error': 'Topic is required'}, status=400)
            
            # Generate quiz using AI
            ai_quiz = ai_generator.generate_quiz(topic, difficulty, num_questions)
            
            # Double-check we have the right number of questions
            actual_questions = len(ai_quiz.get('questions', []))
            print(f"✅ VIEWS: Sending {actual_questions} questions to frontend")
            
            return JsonResponse({
                'success': True,
                'quiz': ai_quiz,
                'generated_questions': actual_questions,
                'requested_questions': num_questions
            })
            
        except Exception as e:
            print(f"❌ VIEWS: Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Only POST requests allowed'}, status=405)
def export_quiz_certificate(request, quiz_id):
    """Generate PDF certificate for quiz completion"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Get user's best attempt
    attempt = QuizAttempt.objects.filter(
        quiz=quiz, 
        user=request.user
    ).order_by('-score', '-attempted_at').first()
    
    if not attempt:
        return redirect('quiz_result', quiz_id=quiz_id)
    
    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    filename = f"certificate_{quiz.title}_{request.user.username}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Create PDF document
    doc = SimpleDocTemplate(response, pagesize=A4, topMargin=0.5*inch)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.darkblue,
        spaceAfter=30,
        alignment=1  # Center aligned
    )
    
    content_style = ParagraphStyle(
        'CustomContent',
        parent=styles['BodyText'],
        fontSize=14,
        spaceAfter=12,
        alignment=1  # Center aligned
    )
    
    # Build PDF content
    story = []
    
    # Title
    story.append(Paragraph("🎓 Certificate of Achievement", title_style))
    story.append(Spacer(1, 20))
    
    # Decorative line
    story.append(Paragraph("<hr width='80%' color='darkblue'/>", styles['BodyText']))
    story.append(Spacer(1, 30))
    
    # User name
    story.append(Paragraph(f"This certificate is proudly presented to", content_style))
    story.append(Paragraph(f"<b><font size='18' color='darkblue'>{request.user.username}</font></b>", content_style))
    story.append(Spacer(1, 20))
    
    # Achievement details
    story.append(Paragraph(f"for successfully completing the quiz", content_style))
    story.append(Paragraph(f"<b><font size='16' color='darkgreen'>'{quiz.title}'</font></b>", content_style))
    story.append(Spacer(1, 20))
    
    # Score and performance
    total_questions = quiz.question_set.count()
    percentage = (attempt.score / total_questions) * 100
    
    story.append(Paragraph(f"with an outstanding score of", content_style))
    story.append(Paragraph(f"<b><font size='16' color='red'>{attempt.score}/{total_questions}</font></b>", content_style))
    story.append(Paragraph(f"({percentage:.1f}% Accuracy)", content_style))
    story.append(Spacer(1, 20))
    
    # Performance rating
    if percentage >= 90:
        performance = "Excellent - Master Level! 🌟"
    elif percentage >= 75:
        performance = "Very Good - Advanced Level! 👍"
    elif percentage >= 60:
        performance = "Good - Proficient Level! ✅"
    else:
        performance = "Completed - Good Effort! 💪"
    
    story.append(Paragraph(f"Performance: <b>{performance}</b>", content_style))
    story.append(Spacer(1, 30))
    
    # Quiz details
    story.append(Paragraph(f"<b>Quiz Details:</b>", content_style))
    story.append(Paragraph(f"Category: {quiz.difficulty.title() if quiz.difficulty else 'General'}", content_style))
    story.append(Paragraph(f"Date Completed: {attempt.attempted_at.strftime('%B %d, %Y')}", content_style))
    story.append(Paragraph(f"Time: {attempt.attempted_at.strftime('%I:%M %p')}", content_style))
    story.append(Spacer(1, 30))
    
    # Footer
    story.append(Paragraph("<hr width='80%' color='darkblue'/>", styles['BodyText']))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Generated by QuizMaster - Your Learning Companion", 
                          ParagraphStyle('Footer', parent=styles['BodyText'], fontSize=10, textColor=colors.gray)))
    
    # Build PDF
    doc.build(story)
    return response
def save_ai_quiz(request):
    """Save AI-generated quiz to database"""
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            data = json.loads(request.body)
            quiz_data = data.get('quiz')
            topic = data.get('topic', 'general knowledge')
            difficulty = data.get('difficulty', 'medium')
            
            # Create quiz
            quiz = Quiz(
                title=quiz_data['quiz_title'],
                description=f"AI-generated quiz about {topic}",
                difficulty=difficulty,
                created_by=request.user
            )
            quiz.save()
            
            # Create questions
            for q_data in quiz_data['questions']:
                question = Question(
                    quiz=quiz,
                    question_text=q_data['question_text'],
                    option1=q_data['options'][0],
                    option2=q_data['options'][1],
                    option3=q_data['options'][2],
                    option4=q_data['options'][3],
                    correct_option=q_data['correct_answer'] + 1,  # Convert to 1-based
                    explanation=q_data.get('explanation', '')
                )
                question.save()
            
            return JsonResponse({
                'success': True,
                'quiz_id': quiz.id,
                'message': 'Quiz saved successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Authentication required'}, status=401)