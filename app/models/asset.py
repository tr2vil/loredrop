from datetime import datetime
from ..extensions import db


class Asset(db.Model):
    __tablename__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    pipeline_run_id = db.Column(db.Integer, db.ForeignKey('pipeline_runs.id'))
    asset_type = db.Column(db.String(20), nullable=False)  # audio/image/video
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    duration = db.Column(db.Float)  # for audio/video
    metadata_ = db.Column('metadata', db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'pipeline_run_id': self.pipeline_run_id,
            'asset_type': self.asset_type,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'duration': self.duration,
            'metadata': self.metadata_,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
