import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from bot.models.event import Event
from bot.models.user import User

logger = logging.getLogger(__name__)

MAX_PARTICIPANTS = 100


def create_event(
    db: Session,
    title: str,
    description: str,
    event_type: str,
    chat_id: int,
    host_id: int,
    reward_xp: int = 100,
) -> Event:
    """
    Create a new event.
    Returns the created Event object.
    """
    event = Event(
        title=title,
        description=description,
        event_type=event_type,
        chat_id=chat_id,
        host_id=host_id,
        reward_xp=reward_xp,
        status="pending",
        participants=[],
        created_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info(f"Event '{title}' created by user {host_id} in chat {chat_id}")
    return event


def start_event(db: Session, event_id: int) -> Event:
    """
    Start an event (change status to 'active').
    Returns the updated Event.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found.")

    if event.status != "pending":
        raise ValueError(f"Cannot start event with status '{event.status}'.")

    event.status = "active"
    event.started_at = datetime.utcnow()
    db.commit()
    db.refresh(event)
    logger.info(f"Event '{event.title}' started (id={event_id})")
    return event


def join_event(db: Session, event_id: int, user_id: int) -> Event:
    """
    Add a user to an event's participants list.
    Max 100 participants.
    Returns the updated Event.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found.")

    if event.status != "active":
        raise ValueError("Cannot join an event that is not active.")

    participants = event.participants or []
    if user_id in participants:
        raise ValueError("User is already a participant.")

    if len(participants) >= MAX_PARTICIPANTS:
        raise ValueError(f"Event is full (max {MAX_PARTICIPANTS} participants).")

    participants.append(user_id)
    event.participants = participants
    db.commit()
    db.refresh(event)
    logger.info(f"User {user_id} joined event '{event.title}'")
    return event


def end_event(db: Session, event_id: int) -> Dict[str, Any]:
    """
    End an event, distribute XP to participants.
    Host gets 1.5x bonus XP.
    Returns a summary dictionary.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found.")

    if event.status != "active":
        raise ValueError(f"Cannot end event with status '{event.status}'.")

    event.status = "completed"
    event.ended_at = datetime.utcnow()

    participants = event.participants or []
    base_xp = event.reward_xp
    host_bonus_xp = int(base_xp * 1.5)

    distributed = []
    for uid in participants:
        user = db.query(User).filter(User.user_id == uid).first()
        if not user:
            continue

        xp_awarded = host_bonus_xp if uid == event.host_id else base_xp
        user.total_xp += xp_awarded
        user.season_xp += xp_awarded
        user.events_participated = (user.events_participated or 0) + 1

        distributed.append({
            "user_id": uid,
            "xp_awarded": xp_awarded,
            "is_host": uid == event.host_id,
        })

    db.commit()
    db.refresh(event)

    summary = {
        "event_id": event.id,
        "title": event.title,
        "status": "completed",
        "total_participants": len(participants),
        "base_xp": base_xp,
        "host_bonus_xp": host_bonus_xp,
        "distributed": distributed,
        "ended_at": event.ended_at.isoformat() if event.ended_at else None,
    }

    logger.info(
        f"Event '{event.title}' ended. Distributed XP to {len(distributed)} participants."
    )
    return summary


def get_active_events(db: Session, chat_id: int) -> List[Dict[str, Any]]:
    """
    Get all active events for a chat.
    Returns a list of event dictionaries.
    """
    events = (
        db.query(Event)
        .filter(Event.chat_id == chat_id, Event.status == "active")
        .all()
    )

    return [
        {
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "event_type": e.event_type,
            "host_id": e.host_id,
            "reward_xp": e.reward_xp,
            "participant_count": len(e.participants or []),
            "started_at": e.started_at.isoformat() if e.started_at else None,
        }
        for e in events
    ]


def get_user_events(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """
    Get all events a user has participated in.
    Returns a list of event dictionaries.
    """
    events = db.query(Event).all()

    result = []
    for e in events:
        participants = e.participants or []
        if user_id in participants or user_id == e.host_id:
            result.append({
                "id": e.id,
                "title": e.title,
                "description": e.description,
                "event_type": e.event_type,
                "status": e.status,
                "is_host": user_id == e.host_id,
                "reward_xp": e.reward_xp,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "ended_at": e.ended_at.isoformat() if e.ended_at else None,
            })

    return result


def cancel_event(db: Session, event_id: int, admin_id: int) -> Event:
    """
    Cancel an event. Only the host or admin can cancel.
    Returns the updated Event.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found.")

    if event.status in ("completed", "cancelled"):
        raise ValueError(f"Cannot cancel event with status '{event.status}'.")

    event.status = "cancelled"
    event.ended_at = datetime.utcnow()
    db.commit()
    db.refresh(event)
    logger.info(f"Event '{event.title}' cancelled by admin {admin_id}")
    return event
