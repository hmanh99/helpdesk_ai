from datetime import datetime, timezone
import logging
from typing import Optional
import uuid

from fastapi import HTTPException, status

from app.ai.schemas import TicketDraft
from app.models.chat import ChatMessage, ChatSession, MessageSource
from app.models.enums import Channel, Intent, MessageSender, Priority
from app.models.user import AppUser
from app.repo.category import CategoryRepository
from app.repo.chat import ChatRepository
from app.schemas.chat import (
    ChatMessageResponse,
    ChatReplyResponse,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    MessageSourceRequestResponse,
)
from app.schemas.ticket import TicketCreate, TicketResponse
from app.security.policies import can_access_chat_session
from app.service.classifier import ClassifierService, IntentClassifier
from app.service.rag import RagService
from app.service.ticket import TicketService

logger = logging.getLogger(__name__)


class ChatService:
    """Service điều phối toàn bộ luồng Chatbot: Phân loại ý định, RAG, phản hồi và tạo Ticket."""

    def __init__(
        self,
        chat_repo: ChatRepository,
        category_repo: CategoryRepository,
        intent_classifier: IntentClassifier,
        rag_service: RagService,
        classifier_service: ClassifierService,
        ticket_service: TicketService,
    ) -> None:
        self.chat_repo = chat_repo
        self.category_repo = category_repo
        self.intent_classifier = intent_classifier
        self.rag_service = rag_service
        self.classifier_service = classifier_service
        self.ticket_service = ticket_service

    def _message_to_response(self, msg: ChatMessage) -> ChatMessageResponse:
        sources_resp = [
            MessageSourceRequestResponse(
                knowledge_document_id=s.knowledge_document_id,
                title=s.knowledge_document.title if s.knowledge_document else "Tài liệu",
                source_url=s.knowledge_document.source_url if s.knowledge_document else None,
                relevance_score=s.relevance_score,
            )
            for s in msg.sources
        ]
        return ChatMessageResponse(
            id=msg.id,
            sender=msg.sender,
            content=msg.content,
            intent=msg.intent,
            confidence_score=msg.confidence_score,
            ticket_draft=msg.ticket_draft,
            sources=sources_resp,
            created_at=msg.created_at,
        )

    def _session_to_response(self, session: ChatSession) -> ChatSessionResponse:
        return ChatSessionResponse(
            id=session.id,
            user_id=session.user_id,
            started_at=session.started_at,
            ended_at=session.ended_at,
            is_resolved_by_bot=session.is_resolved_by_bot,
            message_count=len(session.messages) if session.messages else 0,
            ticket_id=session.ticket.id if session.ticket else None,
        )

    async def create_session(self, current_user: AppUser) -> ChatSessionResponse:
        session = ChatSession(user_id=current_user.id)
        await self.chat_repo.create_session(session)
        await self.chat_repo.commit()
        await self.chat_repo.refresh(session)
        return self._session_to_response(session)

    async def get_session(
        self, session_id: uuid.UUID, current_user: AppUser
    ) -> ChatSessionDetailResponse:
        session = await self.chat_repo.get_session_by_id(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiên chat",
            )
        if not can_access_chat_session(current_user, session):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập phiên chat này",
            )

        messages = [self._message_to_response(m) for m in session.messages]
        return ChatSessionDetailResponse(
            session=self._session_to_response(session),
            messages=messages,
        )

    async def list_sessions(
        self, current_user: AppUser, skip: int = 0, limit: int = 50
    ) -> list[ChatSessionResponse]:
        if current_user.role.value == "ADMIN":
            sessions = await self.chat_repo.list_all_sessions(skip=skip, limit=limit)
        else:
            sessions = await self.chat_repo.list_sessions_by_user(
                user_id=current_user.id, skip=skip, limit=limit
            )
        return [self._session_to_response(s) for s in sessions]

    async def send_message(
        self, session_id: uuid.UUID, current_user: AppUser, content: str
    ) -> ChatReplyResponse:
        session = await self.chat_repo.get_session_by_id(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiên chat",
            )
        if not can_access_chat_session(current_user, session):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền gửi tin nhắn trong phiên chat này",
            )

        if session.ended_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phiên chat này đã kết thúc",
            )

        # 1. Lưu tin nhắn của USER
        user_msg = ChatMessage(
            chat_session_id=session.id,
            sender=MessageSender.USER,
            content=content.strip(),
        )
        await self.chat_repo.add_message(user_msg)
        await self.chat_repo.commit()
        await self.chat_repo.refresh(user_msg)

        # Lấy danh sách category active
        categories = await self.category_repo.list_categories(active_only=True)

        # 2. Phân loại ý định (Intent Classification)
        intent_result = await self.intent_classifier.classify(
            message=content,
            history=session.messages,
            categories=categories,
        )

        suggest_ticket = False
        ticket_draft: Optional[TicketDraft] = None
        bot_content = ""
        sources_to_attach: list[MessageSource] = []
        bot_confidence: Optional[float] = intent_result.confidence

        # 3. Xử lý rẽ nhánh theo sơ đồ luồng
        if intent_result.intent in (Intent.KB_QUESTION, Intent.SIMPLE_TROUBLESHOOT):
            cat_id_uuid = uuid.UUID(intent_result.category_id) if intent_result.category_id else None
            answer_text, used_docs, can_resolve, top_score = await self.rag_service.answer(
                question=content,
                history=session.messages,
                category_id=cat_id_uuid,
            )
            bot_content = answer_text
            bot_confidence = top_score

            # Tạo bot message trước
            bot_msg = ChatMessage(
                chat_session_id=session.id,
                sender=MessageSender.BOT,
                content=bot_content,
                intent=intent_result.intent,
                confidence_score=bot_confidence,
            )
            await self.chat_repo.add_message(bot_msg)
            await self.chat_repo.commit()
            await self.chat_repo.refresh(bot_msg)

            # Gắn các nguồn tài liệu
            for doc, score in used_docs:
                ms = MessageSource(
                    chat_message_id=bot_msg.id,
                    knowledge_document_id=doc.id,
                    relevance_score=score,
                )
                ms.knowledge_document = doc
                sources_to_attach.append(ms)
            if sources_to_attach:
                bot_msg.sources = sources_to_attach
                await self.chat_repo.add_sources(sources_to_attach)
                await self.chat_repo.commit()

            if not can_resolve:
                suggest_ticket = True
                ticket_draft = await self.classifier_service.generate_ticket_draft(
                    session.messages + [user_msg], categories
                )
                bot_msg.ticket_draft = ticket_draft.model_dump()
                await self.chat_repo.commit()

        elif intent_result.intent == Intent.NEEDS_DEPARTMENT:
            suggest_ticket = True
            ticket_draft = await self.classifier_service.generate_ticket_draft(
                session.messages + [user_msg], categories
            )
            bot_content = (
                "Yêu cầu của bạn cần được cán bộ/phòng ban phụ trách tiếp nhận và xử lý trực tiếp. "
                "Tôi đã tạo sẵn một bản nháp Phiếu hỗ trợ (Ticket) bên dưới, bạn hãy kiểm tra lại thông tin và xác nhận để gửi tới phòng ban nhé!"
            )
            bot_msg = ChatMessage(
                chat_session_id=session.id,
                sender=MessageSender.BOT,
                content=bot_content,
                intent=Intent.NEEDS_DEPARTMENT,
                confidence_score=bot_confidence,
                ticket_draft=ticket_draft.model_dump(),
            )
            await self.chat_repo.add_message(bot_msg)
            await self.chat_repo.commit()
            await self.chat_repo.refresh(bot_msg)

        elif intent_result.intent == Intent.SMALLTALK:
            bot_content = (
                "Xin chào bạn! Tôi là trợ lý ảo hỗ trợ kỹ thuật và học vụ Helpdesk AI. "
                "Tôi có thể giúp bạn giải đáp thắc mắc về quy chế, mạng wifi, tài khoản, hoặc hỗ trợ bạn tạo phiếu yêu cầu tới các phòng ban. "
                "Bạn cần hỗ trợ điều gì hôm nay?"
            )
            bot_msg = ChatMessage(
                chat_session_id=session.id,
                sender=MessageSender.BOT,
                content=bot_content,
                intent=Intent.SMALLTALK,
                confidence_score=bot_confidence,
            )
            await self.chat_repo.add_message(bot_msg)
            await self.chat_repo.commit()
            await self.chat_repo.refresh(bot_msg)

        else:  # UNCLEAR
            bot_content = (
                intent_result.clarification_question
                or "Tôi chưa hiểu rõ câu hỏi của bạn. Bạn vui lòng mô tả cụ thể hơn sự cố hoặc thủ tục bạn cần hỗ trợ nhé!"
            )
            bot_msg = ChatMessage(
                chat_session_id=session.id,
                sender=MessageSender.BOT,
                content=bot_content,
                intent=Intent.UNCLEAR,
                confidence_score=bot_confidence,
            )
            await self.chat_repo.add_message(bot_msg)
            await self.chat_repo.commit()
            await self.chat_repo.refresh(bot_msg)

        return ChatReplyResponse(
            message=self._message_to_response(bot_msg),
            suggest_ticket=suggest_ticket,
            ticket_draft=ticket_draft,
        )

    async def submit_feedback(
        self, session_id: uuid.UUID, current_user: AppUser, resolved: bool
    ) -> ChatReplyResponse:
        session = await self.chat_repo.get_session_by_id(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiên chat",
            )
        if not can_access_chat_session(current_user, session):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền đánh giá phiên chat này",
            )

        session.is_resolved_by_bot = resolved

        if resolved:
            bot_msg = ChatMessage(
                chat_session_id=session.id,
                sender=MessageSender.BOT,
                content="Cảm ơn bạn đã phản hồi! Rất vui vì đã hỗ trợ được vấn đề của bạn.",
            )
            await self.chat_repo.add_message(bot_msg)
            await self.chat_repo.commit()
            await self.chat_repo.refresh(bot_msg)
            return ChatReplyResponse(
                message=self._message_to_response(bot_msg),
                suggest_ticket=False,
            )
        else:
            categories = await self.category_repo.list_categories(active_only=True)
            ticket_draft = await self.classifier_service.generate_ticket_draft(
                session.messages, categories
            )
            bot_content = (
                "Rất tiếc vì thông tin hướng dẫn trên chưa giải quyết được vấn đề của bạn. "
                "Tôi đã tạo sẵn bản nháp Phiếu hỗ trợ (Ticket) dưới đây để chuyển sự cố tới các kỹ thuật viên. "
                "Bạn vui lòng kiểm tra và xác nhận nhé!"
            )
            bot_msg = ChatMessage(
                chat_session_id=session.id,
                sender=MessageSender.BOT,
                content=bot_content,
                ticket_draft=ticket_draft.model_dump(),
            )
            await self.chat_repo.add_message(bot_msg)
            await self.chat_repo.commit()
            await self.chat_repo.refresh(bot_msg)
            return ChatReplyResponse(
                message=self._message_to_response(bot_msg),
                suggest_ticket=True,
                ticket_draft=ticket_draft,
            )

    async def confirm_ticket_from_session(
        self,
        session_id: uuid.UUID,
        current_user: AppUser,
        draft_edits: Optional[TicketCreate] = None,
    ) -> TicketResponse:
        session = await self.chat_repo.get_session_by_id(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiên chat",
            )
        if not can_access_chat_session(current_user, session):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền tạo ticket từ phiên chat này",
            )

        # Kiểm tra nếu phiên này đã có ticket
        if session.ticket is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Phiên chat này đã có phiếu hỗ trợ tương ứng (Ticket ID: {session.ticket.id})",
            )

        # Lấy thông tin nháp từ tin nhắn cuối hoặc từ payload sửa đổi
        last_draft_dict = None
        for m in reversed(session.messages):
            if m.ticket_draft:
                last_draft_dict = m.ticket_draft
                break

        title = draft_edits.title if draft_edits and draft_edits.title else (last_draft_dict.get("title") if last_draft_dict else "Yêu cầu hỗ trợ từ Chatbot")
        description = draft_edits.description if draft_edits and draft_edits.description else (last_draft_dict.get("description") if last_draft_dict else "Sự cố được chuyển tiếp từ phiên chat")
        category_id = draft_edits.category_id if draft_edits and draft_edits.category_id else (
            uuid.UUID(last_draft_dict["category_id"]) if last_draft_dict and last_draft_dict.get("category_id") else None
        )
        priority = draft_edits.priority if draft_edits and draft_edits.priority else (
            Priority(last_draft_dict.get("priority", "MEDIUM")) if last_draft_dict else Priority.MEDIUM
        )

        ticket_create_body = TicketCreate(
            title=title,
            description=description,
            category_id=category_id,
            priority=priority,
            channel=Channel.CHATBOT,
            chat_session_id=session.id,
        )

        ticket_response = await self.ticket_service.create_ticket(
            body=ticket_create_body,
            current_user=current_user,
        )

        # Đánh dấu phiên chat kết thúc
        session.ended_at = datetime.now(timezone.utc)
        session.is_resolved_by_bot = False
        await self.chat_repo.commit()

        return ticket_response
