import streamlit as st
import json
import os
import random
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv

load_dotenv()

# File path for questions JSON
QUESTIONS_FILE = "questions.json"

# Initialize session state variables if not already present
if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0

if 'score' not in st.session_state:
    st.session_state.score = 0

if 'answered_questions' not in st.session_state:
    st.session_state.answered_questions = 0

if 'answered' not in st.session_state:
    st.session_state.answered = False

if 'results' not in st.session_state:
    st.session_state.results = []

if 'selected_topic' not in st.session_state:
    st.session_state.selected_topic = None

if 'questions' not in st.session_state:
    st.session_state.questions = []

if 'used_questions' not in st.session_state:
    st.session_state.used_questions = set()  # Track used questions

# Load questions from JSON file
def load_questions_data():
    if os.path.exists(QUESTIONS_FILE):
        with open(QUESTIONS_FILE, 'r') as f:
            return json.load(f)
    else:
        st.error("questions.json file not found. Please create it with the required questions.")
        return {}

# Function to load and shuffle questions for a selected topic
def load_questions_for_topic(questions_data, topic):
    if topic == "All":
        all_questions = []
        for topic_questions in questions_data.values():
            all_questions.extend(topic_questions)
        random.shuffle(all_questions)  # Shuffle all questions
        return all_questions
    else:
        topic_questions = questions_data.get(topic.lower(), [])
        random.shuffle(topic_questions)  # Shuffle questions for the selected topic
        return topic_questions

# Function to save explanations back to JSON file
def save_explanations(questions_data):
    with open(QUESTIONS_FILE, 'w') as f:
        json.dump(questions_data, f, indent=2)

# Function to get explanation from GPT
def get_explanation(question, options, correct_options):
    try:
        api_key = os.getenv("OPENAI_API_KEY", "your-api-key")
        if not api_key or api_key == "your-api-key":
            return "Please set your OpenAI API key to get explanations."
        
        llm = ChatOpenAI(api_key=api_key, model="gpt-4o-mini")
        
        options_list = [f"{key}: {value}" for key, value in options.items()]
        correct_options_full = [f"{opt}: {options[opt]}" for opt in correct_options]
        incorrect_options_full = [f"{key}: {value}" for key, value in options.items() if key not in correct_options]
        
        template = """
        Question: {question}
        
        Options:
        {options}
        
        Correct answers: {correct_options}
        
        Incorrect answers: {incorrect_options}
        
        Please explain why the correct answers are right and why the incorrect answers are wrong.
        """
        
        prompt = PromptTemplate(
            input_variables=["question", "options", "correct_options", "incorrect_options"],
            template=template,
        )
        
        chain = LLMChain(llm=llm, prompt=prompt)
        
        response = chain.invoke({
            "question": question,
            "options": "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options_list)]),
            "correct_options": ", ".join(correct_options_full),
            "incorrect_options": ", ".join(incorrect_options_full)
        })
        
        return response['text']
    
    except Exception as e:
        return f"Error getting explanation: {str(e)}"

# Function to reset the app
def reset_quiz():
    st.session_state.current_question_index = 0
    st.session_state.score = 0
    st.session_state.answered_questions = 0
    st.session_state.answered = False
    st.session_state.results = []
    st.session_state.selected_topic = None
    st.session_state.questions = []
    st.session_state.used_questions = set()  # Reset used questions

# Function to handle next question
def next_question():
    current_q = st.session_state.questions[st.session_state.current_question_index]
    selected_options_keys = st.session_state.selected_options if 'selected_options' in st.session_state else []
    
    st.session_state.results.append({
        "question": current_q["question"],
        "user_answers": [current_q["options"][key] for key in selected_options_keys],
        "correct_answers": [current_q["options"][key] for key in current_q["correct_options"]]
    })
    
    # Mark the current question as used
    st.session_state.used_questions.add(current_q["question"])
    
    st.session_state.current_question_index += 1
    st.session_state.answered_questions += 1
    st.session_state.answered = False
    if 'selected_options' in st.session_state:
        del st.session_state.selected_options

# Function to check answer
def check_answer():
    current_q = st.session_state.questions[st.session_state.current_question_index]
    selected_options_keys = st.session_state.selected_options if 'selected_options' in st.session_state else []
    
    correct = set(selected_options_keys) == set(current_q["correct_options"])
    if correct:
        st.session_state.score += 1
    st.session_state.answered = True

# Main app layout
st.title("MCQ Quiz Application")

# Load questions data
questions_data = load_questions_data()

if not questions_data:
    st.stop()

# Topic selection
if not st.session_state.selected_topic:
    available_topics = list(questions_data.keys())
    available_topics.append("All")
    
    st.header("Select a Topic")
    topic = st.selectbox("Choose a topic for your quiz:", available_topics)
    
    if st.button("Start Quiz"):
        st.session_state.selected_topic = topic
        st.session_state.questions = load_questions_for_topic(questions_data, topic)
        st.rerun()
else:
    total_questions = len(st.session_state.questions)
    st.write(f"Topic: {st.session_state.selected_topic} | Score: {st.session_state.score}/{st.session_state.answered_questions} | Questions Answered: {st.session_state.answered_questions}/{total_questions}")

    # Check if quiz is complete
    if st.session_state.current_question_index >= total_questions:
        st.header("Quiz Complete!")
        st.write(f"Your Final Score: {st.session_state.score}/{total_questions}")
        
        st.subheader("Summary of your answers:")
        for i, result in enumerate(st.session_state.results):
            with st.expander(f"Question {i+1}"):
                st.write(f"**Question:** {result['question']}")
                st.write(f"**Your answers:** {', '.join(result['user_answers']) if result['user_answers'] else 'None selected'}")
                st.write(f"**Correct answers:** {', '.join(result['correct_answers'])}")
        
        if st.button("Save Results"):
            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            results_data = {
                "timestamp": now,
                "topic": st.session_state.selected_topic,
                "score": st.session_state.score,
                "total_questions": total_questions,
                "results": st.session_state.results
            }
            st.json(results_data)
        
        if st.button("Restart Quiz"):
            reset_quiz()
            st.rerun()
    else:
        current_q = st.session_state.questions[st.session_state.current_question_index]
        st.header(f"Question {st.session_state.current_question_index + 1}/{total_questions}")
        st.subheader(current_q["question"])
        
        if not st.session_state.answered:
            if 'selected_options' not in st.session_state:
                st.session_state.selected_options = []
                
            cols = st.columns(2)
            option_idx = 0
            
            for key, option in current_q["options"].items():
                with cols[option_idx % 2]:
                    if st.checkbox(f"{key}: {option}", key=f"option_{key}_{st.session_state.current_question_index}"):
                        if key not in st.session_state.selected_options:
                            st.session_state.selected_options.append(key)
                    else:
                        if key in st.session_state.selected_options:
                            st.session_state.selected_options.remove(key)
                option_idx += 1
            
            if st.button("Submit Answer"):
                check_answer()
                st.rerun()
        else:
            selected_options_keys = st.session_state.selected_options if 'selected_options' in st.session_state else []
            correct = set(selected_options_keys) == set(current_q["correct_options"])
            
            if correct:
                st.success("Correct! Well done!")
            else:
                st.error("Incorrect!")
            
            st.write("**Correct answers:**")
            for key, option in current_q["options"].items():
                if key in current_q["correct_options"]:
                    st.write(f"✅ {key}: {option}")
                else:
                    st.write(f"❌ {key}: {option}")
            
            if st.button("Show Explanation"):
                if not current_q.get("explanation"):
                    explanation = get_explanation(
                        current_q["question"],
                        current_q["options"],
                        current_q["correct_options"]
                    )
                    for topic, questions in questions_data.items():
                        for q in questions:
                            if q["question"] == current_q["question"]:
                                q["explanation"] = explanation
                    save_explanations(questions_data)
                    current_q["explanation"] = explanation
                
                st.write("**Explanation:**")
                st.write(current_q["explanation"])
            
            if st.button("Next Question"):
                next_question()
                st.rerun()

# Sidebar with instructions
with st.sidebar:
    st.title("Instructions")
    st.write("""
    1. Select a topic for your quiz
    2. Select all correct options for each question
    3. After submitting, you'll see if your answer was correct
    4. You can view an explanation before moving to the next question
    5. Your final score will be shown at the end
    6. Refreshing the page keeps you on the same question
    """)
    
    st.title("Settings")
    if st.button("Reset Quiz", key="reset_sidebar"):
        reset_quiz()
        st.rerun()