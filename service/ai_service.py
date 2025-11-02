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


def generate_question(jd_text: str, last_score: int, last_level: int, history):
    print("generating question")

    # Decide performance type and difficulty rule
    if last_score >= 4:
        performance = "strong"
        difficulty_change = "+1 (max 5)"
    elif last_score <= 2:
        performance = "weak"
        difficulty_change = "-1 (min 1)"
    else:
        performance = "average"
        difficulty_change = "same"

    prompt = ChatPromptTemplate.from_template("""
    You are a professional interviewer asking questions related to this job:
    {jd_text}

    The candidate previously scored {last_score}/5.
    The difficulty level of the last question was {last_level}.
    The performance was {performance}.

    Based on this:
    1. Start with a short **natural feedback sentence** (just one line, not generic or repeated — make it sound fresh each time).
       - If strong → sound impressed or confident.
       - If average → sound neutral or conversational.
       - If weak → sound encouraging and supportive.
    2. Then ask the **next question** naturally in the same conversational tone.
       - Keep it short and engaging (1–2 sentences max).
       - Use the job description as context.
       - Make sure the question difficulty adjusts based on the rule: {difficulty_change}

    Previous chat history:
    {history}
    """)

    chain = prompt | llm
    response = chain.invoke({
        "jd_text": jd_text,
        "last_score": last_score,
        "last_level": last_level,
        "performance": performance,
        "difficulty_change": difficulty_change,
        "history": history,
    })

    return response.content.strip()


# --- Intent Response ---
def generate_intent_response(intent: str, question: str, user_input: str = "") -> str:
    # --- Build dynamic prompt ---
    if intent == "exit":
        prompt_text = """
        The candidate triggered intent: {intent}
        Question: "{question}"
        Answer: "{user_input}"

        Generate a short, polite interviewer response indicating the interview has ended 
        and no further questions will be asked.
        Limit response to maximum 10 words.
        """
    else:
        prompt_text = """
        The candidate triggered intent: {intent}
        Question: "{question}"
        Answer: "{user_input}"

        Generate a short, polite interviewer response. 
        Limit response to maximum 10 words.
        """

    # --- Create and run chain ---
    prompt = ChatPromptTemplate.from_template(prompt_text)
    chain = prompt | llm
    response = chain.invoke({
        "intent": intent,
        "question": question,
        "user_input": user_input
    }).content.strip()

    # --- Safety: enforce word limit manually too ---
    words = response.split()
    if len(words) > 10:
        response = " ".join(words[:10]).rstrip(",.!") + "."

    if response.startswith('"') and response.endswith('"'):
        response = response[1:-1].strip()

    return response
   

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
    response = chain.invoke({"message": message}).content.strip().lower()

    # ✅ Remove surrounding quotes if LLM returns like `"answer"`
    if response.startswith('"') and response.endswith('"'):
        response = response[1:-1].strip()

    return response




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

