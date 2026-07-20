"""
Question Engine - Manages interview questions based on role and experience
"""

import random

# Question database organized by role and difficulty
QUESTION_DATABASE = {
    "Full Stack Developer": {
        "Fresher": [
            "Tell me about yourself and why you want to become a Full Stack Developer.",
            "What is the difference between HTML, CSS, and JavaScript?",
            "Explain what a REST API is and how it works.",
            "What is the difference between GET and POST requests?",
            "What is version control and why is Git important?",
            "Describe the difference between frontend and backend development.",
            "What is responsive web design?",
            "Explain what a database is and name some types you know.",
            "What is the DOM in web development?",
            "Why is testing important in software development?",
        ],
        "Intermediate": [
            "Describe your experience with full stack development projects.",
            "Explain microservices architecture and when you would use it.",
            "How do you handle authentication and authorization in web applications?",
            "What strategies do you use for optimizing application performance?",
            "Explain the concept of CI/CD and its benefits.",
            "How do you handle database migrations in production?",
            "Describe a challenging bug you fixed and your debugging process.",
            "What is your approach to writing maintainable code?",
            "How do you handle state management in complex applications?",
            "Explain containerization and how Docker helps in development.",
        ],
    },
    "Data Scientist": {
        "Fresher": [
            "Tell me about yourself and your interest in data science.",
            "What is the difference between supervised and unsupervised learning?",
            "Explain what a neural network is in simple terms.",
            "What is overfitting and how can you prevent it?",
            "Describe the steps in a typical data science project.",
            "What is the difference between classification and regression?",
            "Why is data cleaning important in machine learning?",
            "What Python libraries are commonly used in data science?",
            "Explain what cross-validation is and why it's used.",
            "What is the purpose of feature engineering?",
        ],
        "Intermediate": [
            "Describe a data science project you've worked on end-to-end.",
            "How do you handle imbalanced datasets?",
            "Explain the bias-variance tradeoff.",
            "What techniques do you use for feature selection?",
            "How do you evaluate the performance of a machine learning model?",
            "Explain gradient descent and its variants.",
            "How do you handle missing data in large datasets?",
            "Describe your experience with deep learning frameworks.",
            "How do you deploy machine learning models to production?",
            "Explain A/B testing and when you would use it.",
        ],
    },
    "Software Engineer": {
        "Fresher": [
            "Tell me about yourself and your programming background.",
            "What programming languages are you most comfortable with?",
            "Explain object-oriented programming concepts.",
            "What is the difference between a stack and a queue?",
            "How do you approach debugging a piece of code?",
            "What is time complexity and why does it matter?",
            "Explain what an API is.",
            "What is the difference between compiled and interpreted languages?",
            "Describe a coding project you're proud of.",
            "How do you stay updated with new technologies?",
        ],
        "Intermediate": [
            "Describe your most challenging software engineering project.",
            "How do you design systems for scalability?",
            "Explain SOLID principles and their importance.",
            "How do you approach code reviews?",
            "Describe your experience with design patterns.",
            "How do you handle technical debt?",
            "Explain the CAP theorem.",
            "How do you ensure code quality in your projects?",
            "Describe your experience with agile methodologies.",
            "How do you approach system design problems?",
        ],
    },
    "HR Manager": {
        "Fresher": [
            "Tell me about yourself and why you chose HR as a career.",
            "What do you think are the most important qualities of an HR professional?",
            "How would you handle a conflict between two employees?",
            "What is the purpose of performance reviews?",
            "How do you stay organized when managing multiple tasks?",
            "What do you know about employment laws and regulations?",
            "How would you improve employee engagement?",
            "Describe your communication style.",
            "What recruitment methods do you find most effective?",
            "How do you handle confidential information?",
        ],
        "Intermediate": [
            "Describe your experience in HR management.",
            "How do you develop and implement HR policies?",
            "What strategies have you used to reduce employee turnover?",
            "How do you handle terminations professionally?",
            "Describe your approach to talent acquisition.",
            "How do you measure HR effectiveness?",
            "What is your experience with HRIS systems?",
            "How do you handle workplace diversity and inclusion?",
            "Describe a difficult HR situation you resolved.",
            "How do you align HR strategy with business goals?",
        ],
    },
    "Product Manager": {
        "Fresher": [
            "Tell me about yourself and your interest in product management.",
            "What do you think makes a product successful?",
            "How would you prioritize features for a new product?",
            "What is the difference between a product manager and project manager?",
            "How do you gather user feedback?",
            "Describe a product you love and why.",
            "What metrics would you track for a mobile app?",
            "How do you communicate with technical and non-technical teams?",
            "What is a minimum viable product?",
            "How do you handle competing priorities?",
        ],
        "Intermediate": [
            "Describe a product you managed from conception to launch.",
            "How do you create and manage a product roadmap?",
            "What frameworks do you use for product strategy?",
            "How do you handle stakeholder disagreements?",
            "Describe your approach to competitive analysis.",
            "How do you measure product-market fit?",
            "What is your experience with agile product development?",
            "How do you balance user needs with business goals?",
            "Describe a product failure and what you learned.",
            "How do you drive product adoption?",
        ],
    },
}

# Available roles and experience levels
AVAILABLE_ROLES = list(QUESTION_DATABASE.keys())
EXPERIENCE_LEVELS = ["Fresher", "Intermediate"]

class QuestionEngine:
    """Manages interview questions and progression."""
    
    def __init__(self, role, experience, num_questions=5):
        """Initialize the question engine."""
        self.role = role
        self.experience = experience
        self.num_questions = num_questions
        self.questions = []
        self.current_index = 0
        self.answers = []
        
        self._load_questions()
    
    def _load_questions(self):
        """Load and shuffle questions for the selected role and experience."""
        if self.role in QUESTION_DATABASE:
            if self.experience in QUESTION_DATABASE[self.role]:
                all_questions = QUESTION_DATABASE[self.role][self.experience].copy()
                random.shuffle(all_questions)
                self.questions = all_questions[:self.num_questions]
            else:
                # Default to fresher if experience not found
                all_questions = QUESTION_DATABASE[self.role]["Fresher"].copy()
                random.shuffle(all_questions)
                self.questions = all_questions[:self.num_questions]
        else:
            # Default questions if role not found
            self.questions = [
                "Tell me about yourself.",
                "What are your strengths?",
                "What are your weaknesses?",
                "Where do you see yourself in 5 years?",
                "Why should we hire you?",
            ]
    
    def get_current_question(self):
        """Get the current question."""
        if 0 <= self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None
    
    def get_question_number(self):
        """Get the current question number (1-indexed)."""
        return self.current_index + 1
    
    def get_total_questions(self):
        """Get total number of questions."""
        return len(self.questions)
    
    def next_question(self):
        """Move to the next question."""
        self.current_index += 1
        return self.current_index < len(self.questions)
    
    def is_complete(self):
        """Check if all questions have been answered."""
        return self.current_index >= len(self.questions)
    
    def store_answer(self, answer_data):
        """Store answer data for the current question."""
        self.answers.append({
            'question': self.get_current_question(),
            'question_number': self.get_question_number(),
            **answer_data
        })
    
    def get_all_answers(self):
        """Get all stored answers."""
        return self.answers
    
    def reset(self):
        """Reset the question engine."""
        self.current_index = 0
        self.answers = []
        self._load_questions()


def get_role_selection():
    """Display role selection menu in console."""
    print("\n" + "=" * 60)
    print("       AI INTERVIEW SIMULATOR - ROLE SELECTION")
    print("=" * 60)
    print("\nAvailable Roles:")
    print("-" * 40)
    
    for i, role in enumerate(AVAILABLE_ROLES, 1):
        print(f"  {i}. {role}")
    
    print("-" * 40)
    
    while True:
        try:
            choice = input("\nEnter role number (1-{}): ".format(len(AVAILABLE_ROLES)))
            idx = int(choice) - 1
            if 0 <= idx < len(AVAILABLE_ROLES):
                return AVAILABLE_ROLES[idx]
            print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a valid number.")


def get_experience_selection():
    """Display experience level selection menu in console."""
    print("\nExperience Levels:")
    print("-" * 40)
    
    for i, level in enumerate(EXPERIENCE_LEVELS, 1):
        print(f"  {i}. {level}")
    
    print("-" * 40)
    
    while True:
        try:
            choice = input("\nEnter experience level (1-{}): ".format(len(EXPERIENCE_LEVELS)))
            idx = int(choice) - 1
            if 0 <= idx < len(EXPERIENCE_LEVELS):
                return EXPERIENCE_LEVELS[idx]
            print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a valid number.")


def get_num_questions():
    """Get number of questions for the interview."""
    print("\nHow many questions? (3-10, default: 5)")
    
    while True:
        try:
            choice = input("Enter number of questions: ").strip()
            if not choice:
                return 5
            num = int(choice)
            if 3 <= num <= 10:
                return num
            print("Please enter a number between 3 and 10.")
        except ValueError:
            print("Please enter a valid number.")
