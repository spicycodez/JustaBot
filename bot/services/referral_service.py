import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from bot.models.user import User
from bot.models.referral import Referral

logger = logging.getLogger(__name__)

# Referral bonuses
REFERRAL_JOIN_XP = 50
REFERRAL_ACTIVATE_XP = 150
REFERRAL_LEVEL5_COINS = 300
REFERRAL_ACTIVATE_DAYS = 7


def _generate_referral_code(user_id: int) -> str:
    """Generate a unique 8-character referral code."""
    return secrets.token_hex(4).upper()


def generate_referral_link(user_id: int, bot_username: str) -> Dict[str, Any]:
    """
    Generate a referral link for a user.
    Format: t.me/bot?start=ref_{code}
    Returns dict with code and link.
    """
    code = _generate_referral_code(user_id)
    link = f"https://t.me/{bot_username}?start=ref_{code}"
    return {
        "code": code,
        "link": link,
    }


def process_referral_join(
    db: Session, referral_code: str, new_user_id: int
) -> Dict[str, Any]:
    """
    Process a new user joining via referral link.
    Creates a Referral record and awards 50 XP to the referrer.
    Returns referral details.
    """
    # Find the referrer by their code (code is stored on the user model or referral)
    # We look up the referrer - the code was generated for them
    referrer = db.query(User).filter(User.referral_code == referral_code).first()
    if not referrer:
        # Try to find from any user's stored code
        referrer = db.query(User).filter(User.referral_code == referral_code).first()

    if not referrer:
        raise ValueError(f"Invalid referral code: {referral_code}")

    if referrer.user_id == new_user_id:
        raise ValueError("Cannot refer yourself.")

    # Check if this user was already referred
    existing_ref = (
        db.query(Referral)
        .filter(Referral.referred_user_id == new_user_id)
        .first()
    )
    if existing_ref:
        raise ValueError("User has already been referred.")

    # Create referral record
    referral = Referral(
        referrer_user_id=referrer.user_id,
        referred_user_id=new_user_id,
        referral_code=referral_code,
        activated=False,
        join_date=datetime.utcnow(),
    )
    db.add(referral)

    # Award join XP to referrer
    referrer.total_xp += REFERRAL_JOIN_XP
    referrer.season_xp += REFERRAL_JOIN_XP
    referrer.total_referrals = (referrer.total_referrals or 0) + 1

    db.commit()
    db.refresh(referral)

    logger.info(
        f"User {new_user_id} joined via referral from {referrer.user_id}. +{REFERRAL_JOIN_XP} XP to referrer."
    )

    return {
        "referral_id": referral.id,
        "referrer_user_id": referrer.user_id,
        "referred_user_id": new_user_id,
        "referrer_xp_awarded": REFERRAL_JOIN_XP,
    }


def activate_referral(db: Session, referred_id: int) -> Dict[str, Any]:
    """
    Activate a referral after 7 days.
    Awards 150 XP to the referrer.
    Returns activation details.
    """
    referral = (
        db.query(Referral)
        .filter(
            Referral.referred_user_id == referred_id,
            Referral.activated == False,
        )
        .first()
    )
    if not referral:
        raise ValueError(f"No pending referral found for user {referred_id}.")

    # Check 7-day requirement
    elapsed = (datetime.utcnow() - referral.join_date).days
    if elapsed < REFERRAL_ACTIVATE_DAYS:
        raise ValueError(
            f"Referral cannot be activated yet. {REFERRAL_ACTIVATE_DAYS - elapsed} days remaining."
        )

    referral.activated = True
    referral.activated_at = datetime.utcnow()

    # Award bonus XP to referrer
    referrer = db.query(User).filter(User.user_id == referral.referrer_user_id).first()
    if referrer:
        referrer.total_xp += REFERRAL_ACTIVATE_XP
        referrer.season_xp += REFERRAL_ACTIVATE_XP

    db.commit()
    db.refresh(referral)

    logger.info(
        f"Referral activated: {referred_id} referred by {referral.referrer_user_id}. +{REFERRAL_ACTIVATE_XP} XP."
    )

    return {
        "referral_id": referral.id,
        "referrer_user_id": referral.referrer_user_id,
        "referred_user_id": referred_id,
        "activated": True,
        "referrer_xp_awarded": REFERRAL_ACTIVATE_XP,
        "activated_at": referral.activated_at.isoformat() if referral.activated_at else None,
    }


def check_level5_bonus(db: Session, referred_id: int) -> Dict[str, Any]:
    """
    Check and award level 5 bonus to the referrer.
    Awards 300 Coins to the referrer when referred user reaches level 5.
    Returns bonus details.
    """
    referral = (
        db.query(Referral)
        .filter(
            Referral.referred_user_id == referred_id,
            Referral.activated == True,
            Referral.level5_bonus_awarded == False,
        )
        .first()
    )
    if not referral:
        return {"awarded": False, "reason": "No eligible referral found."}

    # Check if referred user reached level 5
    referred_user = db.query(User).filter(User.user_id == referred_id).first()
    if not referred_user or referred_user.level < 5:
        return {"awarded": False, "reason": "Referred user has not reached level 5 yet."}

    # Award bonus
    referral.level5_bonus_awarded = True
    referral.level5_bonus_at = datetime.utcnow()

    referrer = db.query(User).filter(User.user_id == referral.referrer_user_id).first()
    if referrer:
        referrer.coins += REFERRAL_LEVEL5_COINS

    db.commit()
    db.refresh(referral)

    logger.info(
        f"Level 5 bonus awarded: {referred_id} reached level 5. Referrer {referral.referrer_user_id} gets +{REFERRAL_LEVEL5_COINS} coins."
    )

    return {
        "awarded": True,
        "referrer_user_id": referral.referrer_user_id,
        "referred_user_id": referred_id,
        "coins_awarded": REFERRAL_LEVEL5_COINS,
        "awarded_at": referral.level5_bonus_at.isoformat() if referral.level5_bonus_at else None,
    }


def get_referral_stats(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Get referral statistics for a user.
    Returns total, active, and XP earned counts.
    """
    total = (
        db.query(Referral)
        .filter(Referral.referrer_user_id == user_id)
        .count()
    )
    active = (
        db.query(Referral)
        .filter(Referral.referrer_user_id == user_id, Referral.activated == True)
        .count()
    )

    # Calculate XP earned from referrals
    all_refs = (
        db.query(Referral)
        .filter(Referral.referrer_user_id == user_id)
        .all()
    )
    xp_earned = 0
    for ref in all_refs:
        xp_earned += REFERRAL_JOIN_XP
        if ref.activated:
            xp_earned += REFERRAL_ACTIVATE_XP

    return {
        "user_id": user_id,
        "total_referrals": total,
        "active_referrals": active,
        "pending_referrals": total - active,
        "xp_earned": xp_earned,
        "coins_from_level5": sum(
            REFERRAL_LEVEL5_COINS
            for ref in all_refs
            if ref.level5_bonus_awarded
        ),
    }


def cleanup_stale_referrals(db: Session) -> int:
    """
    Clean up stale referral records.
    Removes referrals older than 30 days that have never been activated
    and the referred user has no activity.
    Returns count of cleaned up referrals.
    """
    cutoff = datetime.utcnow() - timedelta(days=30)

    stale = (
        db.query(Referral)
        .filter(
            Referral.activated == False,
            Referral.join_date < cutoff,
        )
        .all()
    )

    cleaned = 0
    for ref in stale:
        # Check if referred user has any activity
        referred = db.query(User).filter(User.user_id == ref.referred_user_id).first()
        if not referred or referred.total_messages < 1:
            db.delete(ref)
            cleaned += 1

    db.commit()
    logger.info(f"Cleaned up {cleaned} stale referral records.")
    return cleaned
