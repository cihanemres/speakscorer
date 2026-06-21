"""
SpeakScorer — Veli Router
Çocuk ilerleme takibi (sadece görüntüleme)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from database import get_db
from models import User, UserRole, Submission, Assignment
from auth import require_role

router = APIRouter(prefix="/api/parent", tags=["parent"])


@router.get("/children")
def get_children(
    user: User = Depends(require_role(UserRole.parent)),
    db: Session = Depends(get_db),
):
    children = db.query(User).filter(
        User.parent_id == user.id,
        User.rol == UserRole.student,
    ).all()

    return [
        {
            "student_id": c.id,
            "ad_soyad": c.ad_soyad,
            "sinif_duzeyi": c.sinif_duzeyi,
        }
        for c in children
    ]


@router.get("/children/{student_id}/progress")
def get_child_progress(
    student_id: int,
    user: User = Depends(require_role(UserRole.parent)),
    db: Session = Depends(get_db),
):
    child = db.query(User).filter(
        User.id == student_id,
        User.parent_id == user.id,
    ).first()
    if not child:
        raise HTTPException(404, "Çocuk bulunamadı veya size ait değil")

    total = db.query(func.count(Submission.id)).filter(
        Submission.student_id == student_id
    ).scalar() or 0
    avg = db.query(func.avg(Submission.final_score)).filter(
        Submission.student_id == student_id,
        Submission.final_score != None,
    ).scalar() or 0
    best = db.query(func.max(Submission.final_score)).filter(
        Submission.student_id == student_id,
        Submission.final_score != None,
    ).scalar() or 0

    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_avg = db.query(func.avg(Submission.final_score)).filter(
        Submission.student_id == student_id,
        Submission.final_score != None,
        Submission.created_at >= week_ago,
    ).scalar() or 0

    history = db.query(Submission).filter(
        Submission.student_id == student_id,
        Submission.final_score != None,
    ).order_by(Submission.created_at).limit(20).all()

    return {
        "total_submissions": total,
        "avg_score": round(float(avg), 1),
        "best_score": round(float(best), 1),
        "weekly_avg": round(float(weekly_avg), 1),
        "history": [
            {
                "date": h.created_at.strftime("%d.%m") if h.created_at else "",
                "score": round(h.final_score, 1) if h.final_score else 0,
            }
            for h in history
        ],
    }


@router.get("/children/{student_id}/scores")
def get_child_scores(
    student_id: int,
    user: User = Depends(require_role(UserRole.parent)),
    db: Session = Depends(get_db),
):
    child = db.query(User).filter(User.id == student_id, User.parent_id == user.id).first()
    if not child:
        raise HTTPException(404, "Çocuk bulunamadı")

    subs = db.query(Submission).filter(
        Submission.student_id == student_id
    ).order_by(Submission.created_at.desc()).limit(20).all()

    return [
        {
            "id": s.id,
            "paragraph_title": s.paragraph.title if s.paragraph else "",
            "final_score": s.final_score,
            "teacher_score": s.teacher_score,
            "teacher_vocabulary": s.teacher_vocabulary,
            "teacher_grammar": s.teacher_grammar,
            "teacher_fluency": s.teacher_fluency,
            "teacher_coherence": s.teacher_coherence,
            "teacher_feedback": s.teacher_feedback,
            "ai_score": s.ai_score,
            "ai_vocabulary": s.ai_vocabulary,
            "ai_grammar": s.ai_grammar,
            "ai_fluency": s.ai_fluency,
            "ai_coherence": s.ai_coherence,
            "ai_feedback": s.ai_feedback,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in subs
    ]


@router.get("/children/{student_id}/badges")
def get_child_badges(
    student_id: int,
    user: User = Depends(require_role(UserRole.parent)),
    db: Session = Depends(get_db),
):
    child = db.query(User).filter(User.id == student_id, User.parent_id == user.id).first()
    if not child:
        raise HTTPException(404, "Çocuk bulunamadı")

    from models import Achievement
    from routers.student_router import BADGE_CRITERIA
    achievements = db.query(Achievement).filter(
        Achievement.user_id == child.id
    ).order_by(Achievement.earned_at.desc()).all()

    return [
        {
            "type": a.badge_type,
            "name": BADGE_CRITERIA.get(a.badge_type, {}).get("name", a.badge_type),
            "description": BADGE_CRITERIA.get(a.badge_type, {}).get("description", ""),
            "icon": BADGE_CRITERIA.get(a.badge_type, {}).get("icon", "🏅"),
            "earned_at": a.earned_at.isoformat() if a.earned_at else None,
        }
        for a in achievements
    ]


@router.get("/children/{student_id}/leaderboard")
def get_child_leaderboard(
    student_id: int,
    user: User = Depends(require_role(UserRole.parent)),
    db: Session = Depends(get_db),
):
    child = db.query(User).filter(User.id == student_id, User.parent_id == user.id).first()
    if not child:
        raise HTTPException(404, "Çocuk bulunamadı")

    # Re-use logic from student router via a direct query
    level_rankings = db.query(
        User.id,
        User.ad_soyad,
        func.count(Submission.id).label("submission_count"),
        func.avg(Submission.final_score).label("avg_score"),
    ).join(
        Submission, User.id == Submission.student_id
    ).filter(
        User.rol == UserRole.student,
        User.sinif_duzeyi == child.sinif_duzeyi,
        Submission.final_score != None,
    ).group_by(User.id).order_by(
        func.avg(Submission.final_score).desc()
    ).all()

    branch_rankings = [r for r in level_rankings if db.query(User.sube).filter(User.id == r.id).scalar() == child.sube]
    
    # Find child's specific rank
    level_rank = next((i + 1 for i, r in enumerate(level_rankings) if r.id == child.id), None)
    branch_rank = next((i + 1 for i, r in enumerate(branch_rankings) if r.id == child.id), None)
    
    return {
        "level_name": f"{child.sinif_duzeyi}. Sınıflar Genelinde",
        "level_rank": level_rank,
        "branch_name": f"{child.sinif_duzeyi}-{child.sube} Sınıfında" if child.sube else "Şube Yok",
        "branch_rank": branch_rank,
        "total_in_level": len(level_rankings),
        "total_in_branch": len(branch_rankings)
    }


@router.get("/children/{student_id}/assignments")
def get_child_assignments(
    student_id: int,
    user: User = Depends(require_role(UserRole.parent)),
    db: Session = Depends(get_db),
):
    child = db.query(User).filter(User.id == student_id, User.parent_id == user.id).first()
    if not child:
        raise HTTPException(404, "Çocuk bulunamadı")

    assignments = db.query(Assignment).filter(
        Assignment.student_id == student_id
    ).order_by(Assignment.created_at.desc()).all()

    result = []
    for a in assignments:
        sub = db.query(Submission).filter(
            Submission.assignment_id == a.id,
            Submission.student_id == student_id,
        ).first()
        result.append({
            "paragraph_title": a.paragraph.title if a.paragraph else "",
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "completed": sub is not None,
            "score": sub.final_score if sub else None,
        })
    return result
