import openai
import os
import json
from django.conf import settings

class AIQuizGenerator:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None
    
    def generate_quiz(self, topic, difficulty='medium', num_questions=5):
        try:
            # If no API key, use fallback
            if not self.client:
                return self._generate_fallback_quiz(topic, difficulty, num_questions)
                
            prompt = f"""
            Generate a {difficulty} level quiz with exactly {num_questions} questions about {topic}.
            
            Requirements:
            1. Generate EXACTLY {num_questions} questions
            2. Each question must have 4 distinct options
            3. Provide exactly one correct answer (1-4)
            4. Include a brief explanation for each answer
            5. Format as JSON with:
               - quiz_title: string
               - questions: array of objects with:
                 - question_text: string
                 - options: array of 4 strings
                 - correct_answer: integer (1-4)
                 - explanation: string
            
            Example format:
            {{
                "quiz_title": "Quiz about {topic}",
                "questions": [
                    {{
                        "question_text": "What is...?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_answer": 1,
                        "explanation": "Because..."
                    }}
                ]
            }}
            
            Make sure there are exactly {num_questions} questions and each has 4 options.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a quiz generator. Always provide exactly the requested number of questions with 4 options each."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            quiz_data = json.loads(response.choices[0].message.content)
            
            # Validate the generated quiz
            if len(quiz_data['questions']) != num_questions:
                raise Exception(f"Generated {len(quiz_data['questions'])} questions instead of {num_questions}")
            
            for i, question in enumerate(quiz_data['questions']):
                if len(question['options']) != 4:
                    raise Exception(f"Question {i+1} has {len(question['options'])} options instead of 4")
                if question['correct_answer'] not in [1, 2, 3, 4]:
                    raise Exception(f"Question {i+1} has invalid correct answer: {question['correct_answer']}")
            
            return quiz_data
            
        except Exception as e:
            # Fallback to manual generation if AI fails
            return self._generate_fallback_quiz(topic, difficulty, num_questions)
    
    def _generate_fallback_quiz(self, topic, difficulty, num_questions):
        """Fallback quiz generation if AI fails"""
        quiz_title = f"{topic.title()} - {difficulty.title()}"
        questions = []
        
        for i in range(num_questions):
            questions.append({
                "question_text": f"Sample question {i+1} about {topic}?",
                "options": [
                    f"Correct answer about {topic}",
                    f"Incorrect option 1 about {topic}",
                    f"Incorrect option 2 about {topic}",
                    f"Incorrect option 3 about {topic}"
                ],
                "correct_answer": 1,
                "explanation": f"This is a sample explanation for question {i+1}."
            })
        
        return {
            "quiz_title": quiz_title,
            "questions": questions
        }

# Create an instance for easy importing
ai_generator = AIQuizGenerator()