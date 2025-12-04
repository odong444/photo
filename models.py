from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    folder_name = db.Column(db.String(200), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    photos = db.relationship('Photo', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    @property
    def photo_count(self):
        return len(self.photos)
    
    @property
    def downloaded_count(self):
        return sum(1 for p in self.photos if p.is_downloaded)


class Photo(db.Model):
    __tablename__ = 'photos'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    filename = db.Column(db.String(500), nullable=False)  # S3 키
    original_filename = db.Column(db.String(500), nullable=False)
    uploader_name = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer)  # bytes
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_downloaded = db.Column(db.Boolean, default=False)
    downloaded_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Photo {self.original_filename} by {self.uploader_name}>'
    
    @property
    def s3_key(self):
        return self.filename
    
    @property
    def file_size_display(self):
        if self.file_size is None:
            return '-'
        if self.file_size < 1024:
            return f'{self.file_size} B'
        elif self.file_size < 1024 * 1024:
            return f'{self.file_size / 1024:.1f} KB'
        else:
            return f'{self.file_size / (1024 * 1024):.1f} MB'
