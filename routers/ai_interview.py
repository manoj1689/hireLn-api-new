from fastapi import APIRouter, HTTPException, Depends, Path, status
from typing import List, Optional, Union
from datetime import datetime, timezone

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
from auth.dependencies import get_user_or_interview_auth
from models.schemas import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResponseItem,
    InterviewChatRequest,
    StartInterviewRequest,
    InterviewResponseRequest,
    FinalScoreRequest,
    UserResponse,
)

router = APIRouter(prefix="/interview")

# -------------------------------
# Start Interview Endpoint
# -------------------------------
@router.post("/start_chat", summary="Start the interview, greet candidate and get the first question")
def start_interview(
    req: StartInterviewRequest,
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth),
):
    if not req.candidate:
        raise HTTPException(status_code=400, detail="Candidate info is required.")

    # ✅ Access restriction
    where_clause = {"id": req.interview_id} if hasattr(req, "interview_id") else {}
    if isinstance(auth_data, UserResponse):
        where_clause["scheduledById"] = auth_data.id
    elif isinstance(auth_data, dict):
        allowed_id = auth_data.get("interviewId")
        if allowed_id and allowed_id != req.interview_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this interview",
            )

    greeting_msg, first_question = generate_greeting(req.candidate)
    return {"greeting": greeting_msg, "first_question": first_question, "level": 1}


# -------------------------------
# Handle Interview Response
# -------------------------------
@router.post("/chat_response", summary="Process user's response and return next question or result")
def interview_response(
    req: InterviewResponseRequest,
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth),
):
    # ✅ Access restriction
    where_clause = {"id": req.interviewId}
    if isinstance(auth_data, UserResponse):
        where_clause["scheduledById"] = auth_data.id
    elif isinstance(auth_data, dict):
        allowed_id = auth_data.get("interviewId")
        if allowed_id and allowed_id != req.interviewId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this interview",
            )

    # --- Detect user intent ---
    intent = detect_intent(req.user_input)

    # --- Handle Non-Answer Intents ---
    if intent != "answer":
        # 🟢 Case 1: Skip / Next
        if intent in ["negative", "next"]:
            req.history.append({
                "question": req.question,
                "answer": f"Skipped: {intent}",
                "score": req.last_score,
                "level": req.last_level,
                "timestamp": datetime.utcnow().isoformat()
            })

            next_q = generate_question(req.jd_text,  req.last_score, req.last_level, req.history)
            intent_response = generate_intent_response(intent, req.question, req.user_input)

            return {
                "intent": intent,
                "response": intent_response,
                "next_question": next_q,
                "history": req.history
            }

        # 🟡 Case 2: Repeat / Unclear / Offtopic
        elif intent in ["repeat", "unclear", "offtopic"]:
            req.history.append({
                "question": req.question,
                "answer": f"Clarification requested: {intent}",
                "score":  req.last_score,
                "level": req.last_level,
                "timestamp": datetime.utcnow().isoformat()
            })

            # same question or rephrased one depending on logic
            clarification_response = generate_intent_response(intent, req.question, req.user_input)
            next_q = generate_question(req.jd_text,  req.last_score, req.last_level, req.history)

            return {
                "intent": intent,
                "response": clarification_response,
                "next_question": next_q,
                "history": req.history
            }

        # 🔴 Case 3: Exit / Leave Interview
        elif intent in ["leave", "exit"]:
            req.history.append({
                "question": req.question,
                "answer": f"User exited: {intent}",
                "score": 0,
                "level": req.last_level,
                "timestamp": datetime.utcnow().isoformat()
            })

            exit_response = generate_intent_response(intent, req.question, req.user_input)
            return {
                "intent": intent,
                "response": exit_response,
                "next_question": None,
                "history": req.history
            }

        # 🟣 Fallback for unknown intents
        fallback_response = generate_intent_response(intent, req.question, req.user_input)
        return {
            "intent": intent,
            "response": fallback_response,
            "next_question": None,
            "history": req.history
        }

    # --- Case 4: User provided a valid answer ---
    score_data = score_answer(req.question, req.user_input)
    score = score_data.get("score", 0)

    req.history.append({
        "question": req.question,
        "answer": req.user_input,
        "score": score,
        "level": req.last_level,
        "timestamp": datetime.utcnow().isoformat()
    })

    # ✅ Adjust difficulty level based on score
    if score >= 4:
        level = min(req.last_level + 1, 5)
    elif score <= 2:
        level = max(req.last_level - 1, 1)
    else:
        level = req.last_level

    # ✅ Generate next question
    next_q = generate_question(req.jd_text, score, level, req.history)

    return {
        "intent": "answer",
        "score": score,
        "next_question": next_q,
        "level": level,
        "history": req.history
    }

# -------------------------------
# Save Interview Chat History
# -------------------------------
@router.post("/save-chat", summary="Save interview chat history entries to the database")
async def save_chat_entry(
    entry: InterviewChatRequest,
    db: Prisma = Depends(get_db),
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth),
):
    # ✅ Access restriction
    where_clause = {"id": entry.interviewId}
    if isinstance(auth_data, UserResponse):
        where_clause["scheduledById"] = auth_data.id
    elif isinstance(auth_data, dict):
        allowed_id = auth_data.get("interviewId")
        if allowed_id and allowed_id != entry.interviewId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to save chat for this interview",
            )

    saved_entries = []

    try:
        for item in entry.history:
            chat = await db.chathistory.create(
                data={
                    "interviewId": entry.interviewId,
                    "candidateId": entry.candidateId,
                    "applicationId": entry.applicationId,
                    "question": item.question.replace("\n", " "),
                    "answer": item.answer.replace("\n", " ") if item.answer else "",
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
# Final Evaluation
# -------------------------------
@router.post("/evaluate/{interviewId}", response_model=EvaluationResponse)
async def evaluate_interview(
    interviewId: str = Path(..., description="Interview ID to evaluate"),
    db: Prisma = Depends(get_db),
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth),
):
    # ✅ Access restriction
    where_clause = {"id": interviewId}
    if isinstance(auth_data, UserResponse):
        where_clause["scheduledById"] = auth_data.id
    elif isinstance(auth_data, dict):
        allowed_id = auth_data.get("interviewId")
        if allowed_id and allowed_id != interviewId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to evaluate this interview",
            )

    try:
        chat_history = await db.chathistory.find_many(
            where={"interviewId": interviewId}
        )

        if not chat_history:
            raise HTTPException(status_code=404, detail="No chat history found for this interview")

        saved_results = []
        for chat in chat_history:
            score_data = await evaluate_question_answer(chat.question, chat.answer or "")
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
