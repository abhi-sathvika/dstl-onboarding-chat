from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from dotenv import load_dotenv

from .database import create_db_and_tables, get_session, seed_db
from .models import Conversation, Message, MessageResponse, ConversationResponse

from .llm import generate_llm_response  # <-- new import

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    seed_db()
    yield


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files in production only
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
if ENVIRONMENT == "production":
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/app", StaticFiles(directory=static_dir, html=True), name="static")


@app.post("/conversations/", response_model=Conversation)
def create_conversation(
    conversation: Conversation, session: Session = Depends(get_session)
):
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


@app.get("/conversations/", response_model=List[ConversationResponse])
def read_conversations(
    offset: int = 0, limit: int = 100, session: Session = Depends(get_session)
):
    conversations = session.exec(select(Conversation).offset(offset).limit(limit)).all()
    return [ConversationResponse.model_validate(conv) for conv in conversations]


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def read_conversation(conversation_id: int, session: Session = Depends(get_session)):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # load messages for the conversation explicitly so they are returned
    messages = session.exec(
        select(Message).where(Message.conversation_id == conversation_id)
    ).all()
    conversation.messages = messages
    return ConversationResponse.model_validate(conversation)


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, session: Session = Depends(get_session)):
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    session.delete(conversation)
    session.commit()
    return {"ok": True}


@app.post("/messages/")
def create_message(message: Message, session: Session = Depends(get_session)):
    """
    Create a message. If it's a user message, call the LLM with the conversation history,
    save the assistant response, and return both user + assistant messages.
    Response is a dict:
      - if role == 'user': {"user": <Message>, "assistant": <Message>}
      - otherwise: {"message": <Message>}
    """
    # verify conversation exists
    conv = session.get(Conversation, message.conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # store the incoming message (user or assistant)
    session.add(message)
    session.commit()
    session.refresh(message)

    # If the incoming message is from the user, call LLM and save assistant reply
    if message.role == "user":
        # load full conversation history (ordered by created_at)
        history = session.exec(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
        ).all()

        # prepare messages for the model: map roles to 'user'/'assistant' etc.
        model_messages = []
        for m in history:
            role = m.role
            # normalize role if needed
            if role not in ("user", "assistant", "system"):
                role = "user"
            model_messages.append({"role": role, "content": m.content})

        # Call the LLM
        try:
            assistant_text = generate_llm_response(model_messages)
        except Exception as e:
            # If LLM fails, just return the user message and error info (don't crash)
            raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

        # create assistant message
        assistant_msg = Message(
            conversation_id=conv.id, role="assistant", content=assistant_text
        )
        session.add(assistant_msg)
        session.commit()
        session.refresh(assistant_msg)

        return {
            "user": MessageResponse.model_validate(message),
            "assistant": MessageResponse.model_validate(assistant_msg),
        }

    return {"message": MessageResponse.model_validate(message)}
