from datetime import datetime
from ..extensions import db


class Script(db.Model):
    __tablename__ = 'scripts'

    id = db.Column(db.Integer, primary_key=True)
    selected_topic_id = db.Column(db.Integer, db.ForeignKey('selected_topics.id'), nullable=False)
    version = db.Column(db.Integer, default=1)
    full_text = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(10), default='ko')
    word_count = db.Column(db.Integer)
    estimated_duration = db.Column(db.Integer)  # seconds
    prompt_used = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    paragraphs = db.relationship('ScriptParagraph', backref='script', lazy='dynamic',
                                 order_by='ScriptParagraph.paragraph_index',
                                 cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'selected_topic_id': self.selected_topic_id,
            'version': self.version,
            'full_text': self.full_text,
            'language': self.language,
            'word_count': self.word_count,
            'estimated_duration': self.estimated_duration,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'paragraphs': [p.to_dict() for p in self.paragraphs],
        }


class ScriptParagraph(db.Model):
    __tablename__ = 'script_paragraphs'

    id = db.Column(db.Integer, primary_key=True)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id', ondelete='CASCADE'), nullable=False)
    paragraph_index = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    scene_direction = db.Column(db.Text)
    mood = db.Column(db.String(100))
    audio_path = db.Column(db.String(500))
    audio_duration = db.Column(db.Float)
    image_path = db.Column(db.String(500))
    image_prompt = db.Column(db.String(2000))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('ix_script_paragraph_order', 'script_id', 'paragraph_index'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'paragraph_index': self.paragraph_index,
            'text': self.text,
            'scene_direction': self.scene_direction,
            'mood': self.mood,
            'audio_path': self.audio_path,
            'audio_duration': self.audio_duration,
            'image_path': self.image_path,
            'image_prompt': self.image_prompt,
        }
