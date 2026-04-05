from datetime import datetime, date
from ..extensions import db


class RecommendedTopic(db.Model):
    __tablename__ = 'recommended_topics'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    source = db.Column(db.String(50), default='claude')
    batch_date = db.Column(db.Date, nullable=False, default=date.today)
    is_selected = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Sub-agent validation scores (0-10)
    score_history = db.Column(db.Float, nullable=True)
    score_channel_fit = db.Column(db.Float, nullable=True)
    score_audience = db.Column(db.Float, nullable=True)
    score_total = db.Column(db.Float, nullable=True)
    validation_details = db.Column(db.Text, nullable=True)  # JSON string

    selected_topic = db.relationship('SelectedTopic', backref='recommended_topic', uselist=False)

    def to_dict(self):
        d = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'source': self.source,
            'batch_date': self.batch_date.isoformat() if self.batch_date else None,
            'is_selected': self.is_selected,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'score_history': self.score_history,
            'score_channel_fit': self.score_channel_fit,
            'score_audience': self.score_audience,
            'score_total': self.score_total,
            'validation_details': self.validation_details,
        }
        if self.selected_topic:
            d['video_type'] = self.selected_topic.video_type
            d['selected_topic_id'] = self.selected_topic.id
            d['has_pipeline_run'] = self.selected_topic.pipeline_runs.count() > 0
        return d


class SelectedTopic(db.Model):
    __tablename__ = 'selected_topics'

    id = db.Column(db.Integer, primary_key=True)
    recommended_topic_id = db.Column(db.Integer, db.ForeignKey('recommended_topics.id'))
    title = db.Column(db.String(500), nullable=False)
    video_type = db.Column(db.String(20), nullable=False, default='short')
    status = db.Column(db.String(30), default='selected')
    selected_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    scripts = db.relationship('Script', backref='selected_topic', lazy='dynamic')
    pipeline_runs = db.relationship('PipelineRun', backref='selected_topic', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'recommended_topic_id': self.recommended_topic_id,
            'title': self.title,
            'video_type': self.video_type,
            'status': self.status,
            'selected_at': self.selected_at.isoformat() if self.selected_at else None,
        }
