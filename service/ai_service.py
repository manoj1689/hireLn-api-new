import json, re
import re
from langchain_openai import ChatOpenAI  # updated import
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# --- Load env ---
load_dotenv()

# --- Setup LLM ---
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
# -----------------------------
# Greeting / Introduction
# -----------------------------
def generate_first_question(candidate: dict) -> str:
    """
    Generate the first interview question based on candidate role and experience.
    """
    prompt = ChatPromptTemplate.from_template("""
    You are a professional interviewer.
    
    Candidate Info:
    Name: {name}
    Role Applied: {role}
    Experience: {experience}

    Generate one appropriate first interview question for this candidate.
    """)
    
    chain = prompt | llm
    response = chain.invoke({
        "name": candidate.get("name", ""),
        "role": candidate.get("role", ""),
        "experience": candidate.get("experience", "")
    })
    
    return response.content.strip()


def generate_greeting(candidate: dict) -> str:
    """
    Generate a short, warm greeting and include the first interview question.
    """
    first_question = generate_first_question(candidate)
    
    prompt = ChatPromptTemplate.from_template("""
    You are a friendly professional interviewer.

    Candidate Info:
    Name: {name}
    Role Applied: {role}
    Experience: {experience}

    Generate a short, warm, and professional greeting message.
    End with: "Let's start the interview. Here is your first question:"
    """)
    
    chain = prompt | llm
    response = chain.invoke({
        "name": candidate.get("name", ""),
        "role": candidate.get("role", ""),
        "experience": candidate.get("experience", ""),
        "first_question": first_question
    })
    
    return response.content.strip(), first_question

# --- Question Generator ---
def generate_question(jd_text: str, last_score: int, last_level: int, history):
    prompt = ChatPromptTemplate.from_template("""
    You are a professional interviewer ask question from {jd_text}.
    The candidate previously got {last_score}/5. The question difficulty level was {last_level}.

    Based on the candidate’s recent performance:
    - If the last answer was strong, naturally say something encouraging like 
      “You performed well earlier, let’s try something a bit more advanced.”
    - If the answer was average, say something neutral like 
      “Good effort, let’s continue.”
    - If the answer was weak, say something motivating like 
      “No worries, let’s go over a simpler question.”

    Then generate a **conversational next question** in the same tone.

    Difficulty adjustment:
    - score ≥ 4 → +1 (max 5)
    - score ≤ 2 → -1 (min 1)
    - score = 3 → same.

    History:
    {history}
    """)

    chain = prompt | llm
    response = chain.invoke({
        "jd_text": jd_text,
        "last_score": last_score,
        "last_level": last_level,
        "history": history
    })

    return response.content.strip()

# --- Scoring Tool ---
def score_answer(question: str, answer: str):
    prompt = ChatPromptTemplate.from_template("""
    You are an evaluator. Rate the candidate's answer 1–5.

    Question: {question}
    Answer: {answer}

    Respond ONLY as valid JSON:
    {{
      "score": <1-5>
      
    }}
    """)
    chain = prompt | llm
    response = chain.invoke({"question": question, "answer": answer})
    raw = response.content.strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid JSON: {raw}")
    data = json.loads(match.group())
    return {"score": int(data["score"])}


# --- Intent Detection ---
def detect_intent(message: str) -> str:
    prompt = ChatPromptTemplate.from_template("""
    Identify intent from this message:
    "{message}"

    Intents:
    - "answer"
    - "repeat"
    - "offtopic"
    - "unclear"
    - "negative"
    - "next"
    - "exit"                                                                                       

    Return only the intent.
    """)
    chain = prompt | llm
    return chain.invoke({"message": message}).content.strip().lower()


# --- Intent Response ---
# --- Intent Response ---
def generate_intent_response(intent: str, question: str, user_input: str = "") -> str:
    # Special handling for exit
    if intent == "exit":
        prompt = ChatPromptTemplate.from_template("""
        The candidate triggered intent: {intent}
        Question: "{question}"
        Answer: "{user_input}"

        Generate a short, polite interviewer response indicating that the interview has ended 
        and no further questions will be asked.
        """)
    else:
        # Default behavior for other intents
        prompt = ChatPromptTemplate.from_template("""
        The candidate triggered intent: {intent}
        Question: "{question}"
        Answer: "{user_input}"

        Generate a short, polite interviewer response.
        """)

    chain = prompt | llm
    return chain.invoke({
        "intent": intent, 
        "question": question, 
        "user_input": user_input
    }).content.strip()



async def evaluate_question_answer(question: str, answer: str) -> dict:
    """
    Evaluate a single question-answer pair and return a dict ready to save in DB,
    including explanations for each dimension.
    """
    prompt = ChatPromptTemplate.from_template("""
    You are an expert interviewer and evaluator.

    Question: "{question}"
    Candidate Answer: "{answer}"

    Evaluate the answer on the following dimensions:
    1. factualAccuracy: low / medium / high
    2. completeness: low / medium / high
    3. relevance: low / medium / high
    4. coherence: low / medium / high
    5. overall score: 1–5

    For each dimension, provide a short explanation.

    Provide a short final evaluation summary.

    Respond ONLY in valid JSON with these keys:
    {{
        "factualAccuracy": "<low|medium|high>",
        "factualAccuracyExplanation": "<short explanation>",
        "completeness": "<low|medium|high>",
        "completenessExplanation": "<short explanation>",
        "relevance": "<low|medium|high>",
        "relevanceExplanation": "<short explanation>",
        "coherence": "<low|medium|high>",
        "coherenceExplanation": "<short explanation>",
        "score": <1-5>,
        "finalEvaluation": "<short summary>"
    }}
    """)

    chain = prompt | llm
    response = chain.invoke({"question": question, "answer": answer}).content.strip()

    # Extract JSON safely
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid JSON returned by LLM: {response}")

    data = json.loads(match.group())

    # Ensure numeric score
    data["score"] = float(data.get("score", 0))

    # Ensure all expected keys exist
    keys = [
        "factualAccuracy", "factualAccuracyExplanation",
        "completeness", "completenessExplanation",
        "relevance", "relevanceExplanation",
        "coherence", "coherenceExplanation",
        "finalEvaluation"
    ]
    for key in keys:
        data.setdefault(key, None)

    return data

