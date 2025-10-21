from fastapi import APIRouter, HTTPException, Depends, Path
from typing import List, Dict, Optional
from datetime import datetime

from prisma import Prisma

from database import get_db
from service.ai_service import (
    evaluate_question_answer,
    generate_greeting,
    generate_question,
    score_answer,
    detect_intent,
    generate_intent_response
)
from auth.dependencies import get_current_user, get_user_or_interview_auth
from models.schemas import EvaluationRequest, EvaluationResponse, EvaluationResponseItem, InterviewChatRequest, StartInterviewRequest, InterviewResponseRequest, FinalScoreRequest

router = APIRouter(prefix="/interview")


# -------------------------------
# Start Interview Endpoint
# -------------------------------
@router.post("/start_chat", summary="Start the interview, greet candidate and get the first question")
def start_interview(req: StartInterviewRequest):
    if not req.candidate:

        raise HTTPException(status_code=400, detail="Candidate info is required.")

    # 1️⃣ Generate greeting
    greeting_msg,first_question = generate_greeting(req.candidate)

    return {
        "greeting": greeting_msg,
        "first_question": first_question,
        "level": 1
    }

# -------------------------------
# Handle Interview Response
# -------------------------------
@router.post("/chat_response", summary="Process user's response and return next question or result")
def interview_response(req: InterviewResponseRequest):
    intent = detect_intent(req.user_input)

    # --- If intent is not an answer ---
    if intent != "answer":
        if intent in ["negative", "next"]:
            req.history.append({
                "question": req.question,
                "answer": f"[Skipped: {intent}]",
                "score": 0,
                "level": req.last_level,
                "timestamp": datetime.utcnow().isoformat()
            })
            next_q = generate_question(req.jd_text, 2, req.last_level, req.history)
            return {
                "intent": intent,
                "response": "Skipping to next question.",
                "next_question": next_q,
                "history": req.history
            }

        response = generate_intent_response(intent, req.question, req.user_input)
        return {"intent": intent, "response": response, "next_question": None}

    # --- Evaluate the answer ---
    score_data = score_answer(req.question, req.user_input)
    score = score_data["score"]

    req.history.append({
        "question": req.question,
        "answer": req.user_input,
        "score": score,
        "level": req.last_level,
        "timestamp": datetime.utcnow().isoformat()
    })

    # Adjust difficulty
    level = min(req.last_level + 1, 5) if score >= 4 else max(req.last_level - 1, 1) if score <= 2 else req.last_level
    next_q = generate_question(req.jd_text, score, level, req.history)

    return {
        "intent": "answer",
        "score": score,
        "next_question": next_q,
        "level": level,
        "history": req.history
    }



# -------------------------------
# AI Save chat 
# ------------------------------
@router.post("/save-chat", summary="Save interview chat history entries to the database")
async def save_chat_entry(entry: InterviewChatRequest, db: Prisma = Depends(get_db)):
    saved_entries = []

    try:
        for item in entry.history:
            # Replace newlines with spaces
            question_clean = item.question.replace("\n", " ")
            answer_clean = item.answer.replace("\n", " ") if item.answer else ""

            chat = await db.interviewchathistory.create(
                data={
                    "interviewId": entry.interviewId,
                    "candidateId": entry.candidateId,
                    "applicationId": entry.applicationId,
                    "question": question_clean,
                    "answer": answer_clean,
                    "score": item.score,
                    "level": item.level,
                    "createdAt": item.timestamp
                }
            )
            saved_entries.append(chat)

        return {
            "message": f"Successfully saved {len(saved_entries)} chat history entries.",
            "data": saved_entries
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving chat history: {str(e)}")


# -------------------------------
# Final Score Calculation
# -------------------------------
@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_interview(
    interviewId: str = Path(..., description="ID of the interview to evaluate"),
    db: Prisma = Depends(get_db)
):
    """
    Evaluate all question-answer pairs from InterviewChatHistory for a given interviewId
    and save the evaluations in the Evaluation table.
    """
    try:
        # --- Fetch chat history for this interview ---
        chat_history = await db.interviewchathistory.find_many(
            where={"interviewId": interviewId}
        )

        if not chat_history:
            raise HTTPException(status_code=404, detail="No chat history found for this interview")

        saved_results = []

        for chat in chat_history:
            # Evaluate question-answer using AI service
            score_data = await evaluate_question_answer(chat.question, chat.answer or "")

            # Save evaluation in DB
            eval_record = await db.evaluation.create(
                data={
                    "question": chat.question,
                    "answer": chat.answer or "",
                    "interviewId": interviewId,
                    "factualAccuracy": score_data.get("factualAccuracy"),
                    "factualAccuracyExplanation": score_data.get("factualAccuracyExplanation"),
                    "completeness": score_data.get("completeness"),
                    "completenessExplanation": score_data.get("completenessExplanation"),
                    "relevance": score_data.get("relevance"),
                    "relevanceExplanation": score_data.get("relevanceExplanation"),
                    "coherence": score_data.get("coherence"),
                    "coherenceExplanation": score_data.get("coherenceExplanation"),
                    "score": score_data.get("score"),
                    "finalEvaluation": score_data.get("finalEvaluation"),
                    "evaluatedAt": datetime.utcnow()
                }
            )

            saved_results.append(EvaluationResponseItem(
                question=eval_record.question,
                answer=eval_record.answer,
                score=eval_record.score,
                id=eval_record.id,
                createdAt=eval_record.createdAt
            ))

        return EvaluationResponse(
            interviewId=interviewId,
            results=saved_results,
            message=f"Successfully evaluated {len(saved_results)} questions."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during evaluation: {str(e)}")