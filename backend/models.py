"""
SpeakScorer — Veritabanı Modelleri
Kullanıcılar, Paragraflar, Ödevler, Gönderimler, Oyunlaştırma
reading_app ile aynı mimari + İngilizce konuşma değerlendirmesi
"""
import enum
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float,
    DateTime, Date, Enum, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base


# ── Enums ─────────────────────────────────────────────────
# ── Enums ─────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    student = "ogrenci"
    teacher = "ogretmen"
    parent = "veli"
    admin = "yonetici"
    moderator = "moderator"


class UserStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    inactive = "inactive"
    rejected = "rejected"


class TargetType(str, enum.Enum):
    student = "student"
    class_group = "class"


# ── Users ─────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    ad_soyad = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(UserRole), nullable=False, default=UserRole.student)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.pending)
    sinif_duzeyi = Column(Integer, nullable=True)       # Sınıf seviyesi (5-12)
    sube = Column(String(10), nullable=True)            # Şube (A, B, C...)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Veli bağlantısı
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Profil & Permissions
    profil_fotografi = Column(String(500), nullable=True)  # Avatar
    permissions = Column(Text, nullable=True)              # JSON string for RBAC

    # Teacher profile fields
    brans = Column(String(100), nullable=True)
    biyografi = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Gamification relationships
    achievements = relationship("Achievement", back_populates="user")
    streak = relationship("UserStreak", back_populates="user", uselist=False)

    # Assignment relationships (as student)
    student_assignments = relationship(
        "Assignment",
        foreign_keys="Assignment.student_id",
        back_populates="student"
    )

    # Submissions
    submissions = relationship("Submission", back_populates="student")

    def __repr__(self):
        return f"<User {self.email} ({self.rol})>"


# ── Paragraphs ────────────────────────────────────────────
class Paragraph(Base):
    __tablename__ = "paragraphs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    text = Column(Text, nullable=False)
    audio_path = Column(String(500), nullable=True)      # TTS generated audio
    level = Column(Integer, default=1)                    # Seviye (1-5)
    category = Column(String(100), default="Genel")
    approved = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assignments = relationship("Assignment", back_populates="paragraph")
    questions = relationship("Question", back_populates="paragraph")


# ── Questions (Quiz) ──────────────────────────────────────
class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    paragraph_id = Column(Integer, ForeignKey("paragraphs.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    option_a = Column(String(300), nullable=False)
    option_b = Column(String(300), nullable=False)
    option_c = Column(String(300), nullable=False)
    option_d = Column(String(300), nullable=False)
    correct_answer = Column(String(1), nullable=False)   # A, B, C, D
    created_at = Column(DateTime, default=datetime.utcnow)

    paragraph = relationship("Paragraph", back_populates="questions")


# ── Assignments (Ödevler) ─────────────────────────────────
class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    paragraph_id = Column(Integer, ForeignKey("paragraphs.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    class_name = Column(String(50), nullable=True)       # Sınıf adı (5-A vb.)
    target_type = Column(Enum(TargetType), nullable=False, default=TargetType.student)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    teacher = relationship("User", foreign_keys=[teacher_id])
    paragraph = relationship("Paragraph", back_populates="assignments")
    student = relationship("User", foreign_keys=[student_id], back_populates="student_assignments")
    submissions = relationship("Submission", back_populates="assignment")


# ── Submissions (Gönderimler) ─────────────────────────────
class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=True)
    paragraph_id = Column(Integer, ForeignKey("paragraphs.id"), nullable=False)
    audio_path = Column(String(500), nullable=True)
    transcript = Column(Text, nullable=True)

    # AI scoring (4 criteria × 25 = 100)
    ai_score = Column(Float, nullable=True)
    ai_vocabulary = Column(Float, nullable=True)
    ai_grammar = Column(Float, nullable=True)
    ai_fluency = Column(Float, nullable=True)
    ai_coherence = Column(Float, nullable=True)
    ai_feedback = Column(Text, nullable=True)

    # Teacher scoring (same 4 criteria × 25 = 100)
    teacher_score = Column(Float, nullable=True)
    teacher_vocabulary = Column(Float, nullable=True)
    teacher_grammar = Column(Float, nullable=True)
    teacher_fluency = Column(Float, nullable=True)
    teacher_coherence = Column(Float, nullable=True)
    teacher_feedback = Column(Text, nullable=True)

    # Final score: teacher_score if exists, else ai_score
    final_score = Column(Float, nullable=True)

    status = Column(String(20), default="pending")   # pending, scored, reviewed
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", back_populates="submissions")
    assignment = relationship("Assignment", back_populates="submissions")
    paragraph = relationship("Paragraph")


# ── Achievement / Badges ──────────────────────────────────
class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_type = Column(String(50), nullable=False)
    earned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="achievements")

    __table_args__ = (
        UniqueConstraint('user_id', 'badge_type', name='unique_user_badge'),
    )


# ── User Streak & XP ─────────────────────────────────────
class UserStreak(Base):
    __tablename__ = "user_streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(Date, nullable=True)
    total_xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="streak")


# XP values for different actions
XP_VALUES = {
    "submission_complete": 10,       # Gönderim tamamlama
    "quiz_passed": 15,               # Quiz geçme
    "perfect_score": 25,             # Mükemmel puan (95+)
    "daily_login": 5,                # Günlük giriş
    "streak_bonus_3": 10,            # 3 gün seri bonus
    "streak_bonus_7": 25,            # 7 gün seri bonus
    "streak_bonus_30": 100,          # 30 gün seri bonus
    "badge_earned": 20,              # Rozet kazanma
    "high_score": 15,                # 80+ puan
}

# Level thresholds
LEVEL_THRESHOLDS = [
    0,      # Seviye 1
    100,    # Seviye 2
    250,    # Seviye 3
    500,    # Seviye 4
    1000,   # Seviye 5
    2000,   # Seviye 6
    3500,   # Seviye 7
    5000,   # Seviye 8
    7500,   # Seviye 9
    10000,  # Seviye 10
]

LEVEL_NAMES = {
    1: "Çırak",
    2: "Konuşmacı",
    3: "Hikayeci",
    4: "Söz Ustası",
    5: "İleri Konuşmacı",
    6: "Bilge",
    7: "Efsane",
    8: "Şampiyon",
    9: "Kahraman",
    10: "Efsanevi Konuşmacı"
}


def get_level_for_xp(xp: int) -> int:
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp < threshold:
            return i
    return len(LEVEL_THRESHOLDS)


def get_xp_for_next_level(current_xp: int, current_level: int) -> dict:
    if current_level >= len(LEVEL_THRESHOLDS):
        return {"current": current_xp, "needed": 0, "progress": 100}
    current_threshold = LEVEL_THRESHOLDS[current_level - 1] if current_level > 1 else 0
    next_threshold = LEVEL_THRESHOLDS[current_level] if current_level < len(LEVEL_THRESHOLDS) else current_xp
    xp_in_level = current_xp - current_threshold
    xp_needed = next_threshold - current_threshold
    progress = (xp_in_level / xp_needed * 100) if xp_needed > 0 else 100
    return {"current": xp_in_level, "needed": xp_needed, "progress": min(100, progress)}


# ── Commendation (Takdir) ─────────────────────────────────
class Commendation(Base):
    __tablename__ = "commendations"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    commendation_type = Column(String(50), nullable=False, default="takdir")
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    rank = Column(Integer, nullable=True)
    xp_reward = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", foreign_keys=[student_id])
    teacher = relationship("User", foreign_keys=[teacher_id])


# ── Notification ──────────────────────────────────────────
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), default="info")
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    link = Column(String(500), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
