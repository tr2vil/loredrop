from datetime import datetime
from ..extensions import db


class SceneImage(db.Model):
    __tablename__ = 'scene_images'

    id = db.Column(db.Integer, primary_key=True)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id', ondelete='CASCADE'), nullable=False)
    scene_index = db.Column(db.Integer, nullable=False)
    prompt = db.Column(db.Text)
    generation_id = db.Column(db.String(255))
    image_urls = db.Column(db.JSON)
    selected_url = db.Column(db.String(2000))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    script = db.relationship('Script', backref=db.backref('scene_images', lazy='dynamic',
                                                           cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'script_id': self.script_id,
            'scene_index': self.scene_index,
            'prompt': self.prompt,
            'generation_id': self.generation_id,
            'image_urls': self.image_urls or [],
            'selected_url': self.selected_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
