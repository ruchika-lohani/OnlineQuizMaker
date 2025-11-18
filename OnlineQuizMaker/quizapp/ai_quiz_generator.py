import os
import json
import google.generativeai as genai
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()

class AIQuizGenerator:
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        if self.api_key and self.api_key != 'your_google_ai_studio_key_here':
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.ai_enabled = True
        else:
            self.ai_enabled = False
            print("⚠️  Google AI API key not found. Using demo mode.")
    
    def generate_quiz(self, topic, difficulty='medium', num_questions=5, question_type='multiple_choice'):
        """
        Generate quiz questions using Google Gemini AI
        """
        print(f"🎯 BACKEND: Requested {num_questions} questions about '{topic}'")
        
        if not self.ai_enabled:
            quiz_data = self._get_demo_questions(topic, difficulty, num_questions)
            print(f"📊 BACKEND: Demo mode - Generated {len(quiz_data['questions'])} questions")
            return quiz_data
        
        try:
            prompt = self._build_prompt(topic, difficulty, num_questions, question_type)
            print(f"🔍 BACKEND: Sending request to AI for {num_questions} questions...")
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=4000,
                    temperature=0.7,
                )
            )
            
            content = response.text
            print(f"📝 BACKEND: Raw AI response received")
            
            quiz_data = self._parse_response(content, topic, difficulty, num_questions)
            print(f"✅ BACKEND: Final quiz has {len(quiz_data['questions'])} questions")
            return quiz_data
            
        except Exception as e:
            print(f"❌ BACKEND: AI Generation Error: {e}")
            quiz_data = self._get_demo_questions(topic, difficulty, num_questions)
            print(f"📊 BACKEND: Fallback to demo - {len(quiz_data['questions'])} questions")
            return quiz_data
    
    def _build_prompt(self, topic, difficulty, num_questions, question_type):
        return f"""
IMPORTANT: Generate EXACTLY {num_questions} multiple choice questions about "{topic}".

DIFFICULTY: {difficulty}
NUMBER OF QUESTIONS: {num_questions}

FORMAT REQUIREMENTS:
- Generate EXACTLY {num_questions} questions, no more, no less
- Each question must have 4 options
- Only one correct answer per question
- Include brief explanations
- Make questions {difficulty} difficulty

OUTPUT FORMAT - Return ONLY valid JSON:
{{
    "quiz_title": "Creative title about {topic}",
    "questions": [
        {{
            "question_text": "Question 1?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 0,
            "explanation": "Brief explanation"
        }}
        // Continue for exactly {num_questions} questions
    ]
}}

TOPIC: {topic}
NUMBER OF QUESTIONS REQUIRED: {num_questions}
DIFFICULTY: {difficulty}

CRITICAL: Generate exactly {num_questions} questions. Do not stop early.
"""
    
    def _parse_response(self, content, topic, difficulty, num_questions):
        """Parse AI response and validate structure"""
        try:
            # Extract JSON from response
            start = content.find('{')
            end = content.rfind('}') + 1
            
            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")
                
            json_str = content[start:end]
            data = json.loads(json_str)
            
            # Validate structure
            if 'questions' not in data:
                raise ValueError("No 'questions' field in response")
                
            if 'quiz_title' not in data:
                data['quiz_title'] = f"{topic.title()} Quiz - {difficulty.title()}"
            
            # Check question count
            actual_questions = len(data['questions'])
            print(f"📊 BACKEND: AI generated {actual_questions} questions (requested: {num_questions})")
            
            # If wrong number of questions, use demo questions
            if actual_questions != num_questions:
                print(f"⚠️  BACKEND: AI returned wrong count. Using demo questions.")
                return self._get_demo_questions(topic, difficulty, num_questions)
            
            return data
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"❌ BACKEND: Parsing error: {e}")
            return self._get_demo_questions(topic, difficulty, num_questions)
    
    def _get_demo_questions(self, topic, difficulty, num_questions):
        """Provide demo questions with exact count"""
        print(f"🔄 BACKEND: Generating {num_questions} demo questions for '{topic}'")
        
        # Create questions based on requested count
        questions = []
        
        # Different question templates for variety
        templates = [
            {
                "template": f"What is a key concept in {topic}?",
                "options": [
                    "Fundamental principles",
                    "Basic terminology", 
                    "Core methodologies",
                    "All of the above"
                ]
            },
            {
                "template": f"Why is {topic} important in modern applications?",
                "options": [
                    "It solves real-world problems",
                    "It drives innovation",
                    "It improves efficiency",
                    "All of the above"
                ]
            },
            {
                "template": f"What skills are needed to master {topic}?",
                "options": [
                    "Analytical thinking",
                    "Problem-solving abilities",
                    "Continuous learning mindset",
                    "All of the above"
                ]
            },
            {
                "template": f"How does {topic} impact technology development?",
                "options": [
                    "Through new tools and frameworks",
                    "By enabling automation",
                    "Through improved processes",
                    "All of the above"
                ]
            },
            {
                "template": f"What are common challenges in learning {topic}?",
                "options": [
                    "Understanding complex concepts",
                    "Applying theory to practice",
                    "Keeping up with changes",
                    "All of the above"
                ]
            },
            {
                "template": f"What makes {topic} different from related fields?",
                "options": [
                    "Its unique methodology",
                    "Specific application domains",
                    "Core principles and theories",
                    "All of the above"
                ]
            },
            {
                "template": f"How has {topic} evolved recently?",
                "options": [
                    "Through technological advancements",
                    "With new research findings",
                    "In practical applications",
                    "All of the above"
                ]
            },
            {
                "template": f"What role does {topic} play in education?",
                "options": [
                    "Teaching critical thinking",
                    "Developing problem-solving skills",
                    "Preparing for future careers",
                    "All of the above"
                ]
            },
            {
                "template": f"Why is {topic} considered a valuable skill?",
                "options": [
                    "High demand in job market",
                    "Versatile applications",
                    "Future-proof knowledge",
                    "All of the above"
                ]
            },
            {
                "template": f"What are the future trends in {topic}?",
                "options": [
                    "Increased automation",
                    "AI integration",
                    "New specializations",
                    "All of the above"
                ]
            },
            {
                "template": f"How does {topic} contribute to innovation?",
                "options": [
                    "By enabling new solutions",
                    "Through improved processes",
                    "With better tools",
                    "All of the above"
                ]
            },
            {
                "template": f"What are the ethical considerations in {topic}?",
                "options": [
                    "Privacy concerns",
                    "Fairness and bias",
                    "Responsible implementation",
                    "All of the above"
                ]
            },
            {
                "template": f"How is {topic} used in everyday life?",
                "options": [
                    "In mobile applications",
                    "Through web services",
                    "In automation tools",
                    "All of the above"
                ]
            },
            {
                "template": f"What resources are best for learning {topic}?",
                "options": [
                    "Online courses and tutorials",
                    "Practical projects",
                    "Community forums",
                    "All of the above"
                ]
            },
            {
                "template": f"Why is collaboration important in {topic}?",
                "options": [
                    "Different perspectives",
                    "Knowledge sharing",
                    "Faster problem-solving",
                    "All of the above"
                ]
            }
        ]
        
        # Generate exactly the requested number of questions
        for i in range(num_questions):
            template = templates[i % len(templates)]  # Cycle through templates
            questions.append({
                "question_text": template["template"],
                "options": template["options"],
                "correct_answer": 3,  # "All of the above" is correct
                "explanation": f"This question covers important aspects of {topic} that are fundamental to understanding the field."
            })
        
        return {
            "quiz_title": f"{topic.title()} Quiz - {difficulty.title()}",
            "questions": questions
        }

# Singleton instance
ai_generator = AIQuizGenerator()