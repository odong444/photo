import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///photo_manager.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # AWS S3 설정
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-2')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
    
    # 관리자 비밀번호
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin1234')
    
    # 업로드 설정
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB 제한
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
