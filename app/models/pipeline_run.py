from datetime import datetime
from ..extensions import db


class PipelineRun(db.Model):
    __tablename__ = 'pipeline_runs'

    id = db.Column(db.Integer, primary_key=True)
    selected_topic_id = db.Column(db.Integer, db.ForeignKey('selected_topics.id'), nullable=False)
    status = db.Column(db.String(30), default='pending')  # pending/running/paused/completed/failed
    current_step = db.Column(db.String(50))
    auto_mode = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    steps = db.relationship('PipelineStep', backref='run', lazy='dynamic',
                            order_by='PipelineStep.id',
                            cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'selected_topic_id': self.selected_topic_id,
            'status': self.status,
            'current_step': self.current_step,
            'auto_mode': self.auto_mode,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'steps': [s.to_dict() for s in self.steps],
        }


class PipelineStep(db.Model):
    __tablename__ = 'pipeline_steps'

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    step_name = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending/running/completed/failed/skipped
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    result_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('run_id', 'step_name', name='uq_run_step'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'run_id': self.run_id,
            'step_name': self.step_name,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'result_data': self.result_data,
        }
