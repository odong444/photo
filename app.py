from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from config import Config
from models import db, Project, Photo
import boto3
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import io
import zipfile
import re
import os
import gspread
from google.oauth2.service_account import Credentials
import json

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

s3_client = boto3.client(
    's3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_REGION')
)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME')  

GOOGLE_SHEETS_ID = '1eAuotbbl7bbj8N8rCr4lbgE-g9Ja_l66ZUk_N9UVtEI'

def get_sheets_client():
    """Google Sheets 클라이언트 생성"""
    try:
        creds_json = os.environ.get('GOOGLE_CREDENTIALS')
        if not creds_json:
            print("GOOGLE_CREDENTIALS 환경변수가 없습니다")
            return None
        
        creds_dict = json.loads(creds_json)
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        print(f"Google Sheets 연결 오류: {e}")
        return None

def save_reviews_to_sheets(uploader_name, project_name, reviews):
    """리뷰 텍스트를 Google Sheets에 저장"""
    try:
        client = get_sheets_client()
        if not client:
            return False, "Google Sheets 연결 실패"
        
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
        worksheet = spreadsheet.sheet1
        
        rows_to_add = []
        for review in reviews:
            if review.strip():
                rows_to_add.append([uploader_name, project_name, review.strip()])
        
        if rows_to_add:
            worksheet.append_rows(rows_to_add)
        
        return True, f"{len(rows_to_add)}건 저장 완료"
    except Exception as e:
        print(f"Sheets 저장 오류: {e}")
        return False, str(e)

# S3 클라이언트
def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'],
        region_name=app.config['AWS_REGION']
    )

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def sanitize_folder_name(name):
    # 한글, 영문, 숫자, 언더스코어만 허용
    name = re.sub(r'[^\w가-힣]', '_', name)
    return name.lower()

# ==================== 일반 사용자 페이지 ====================

@app.route('/')
def index():
    """메인 페이지 - 활성화된 프로젝트 목록"""
    projects = Project.query.filter_by(is_active=True).order_by(Project.created_at.desc()).all()
    return render_template('index.html', projects=projects)

@app.route('/upload/<int:project_id>', methods=['GET', 'POST'])
def upload(project_id):
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        uploader_name = request.form.get('uploader_name', '').strip()
        
        if not uploader_name:
            flash('업로더 이름을 입력해주세요.')
            return redirect(url_for('upload', project_id=project_id))
        
        uploaded_count = 0
        review_count = 0
        
        # 1. 사진 업로드 처리 (기존 로직)
        files = request.files.getlist('photos')
        for file in files:
            if file and file.filename:
                if allowed_file(file.filename):
                    # 파일 처리
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    s3_key = f"{project.name}/{uploader_name}/{unique_filename}"
                    
                    try:
                        # S3 업로드
                        file.seek(0)
                        s3_client.upload_fileobj(
                            file,
                            S3_BUCKET,
                            s3_key,
                            ExtraArgs={'ContentType': file.content_type}
                        )
                        
                        # DB 저장
                        photo = Photo(
                            filename=unique_filename,
                            original_filename=file.filename,
                            s3_key=s3_key,
                            file_size=file.content_length or 0,
                            uploader_name=uploader_name,
                            project_id=project.id
                        )
                        db.session.add(photo)
                        uploaded_count += 1
                    except Exception as e:
                        print(f"Upload error: {e}")
                        continue
        
        # 2. 리뷰 텍스트 처리 (새로 추가)
        reviews = []
        for i in range(1, 6):
            review = request.form.get(f'review_{i}', '').strip()
            if review and len(review) >= 50:  # 50자 이상만 저장
                reviews.append(review)
        
        if reviews:
            success, message = save_reviews_to_sheets(uploader_name, project.name, reviews)
            if success:
                review_count = len(reviews)
            else:
                print(f"리뷰 저장 실패: {message}")
        
        # 3. 커밋 및 결과
        db.session.commit()
        
        if uploaded_count > 0 or review_count > 0:
            return redirect(url_for('upload_complete', project_id=project_id, 
                                    photo_count=uploaded_count, review_count=review_count))
        else:
            flash('업로드할 사진을 선택하거나 리뷰를 작성해주세요.')
            return redirect(url_for('upload', project_id=project_id))
    
    return render_template('upload.html', project=project)


# upload_complete 함수도 수정 필요
@app.route('/upload/<int:project_id>/complete')
def upload_complete(project_id):
    project = Project.query.get_or_404(project_id)
    photo_count = request.args.get('photo_count', 0, type=int)
    review_count = request.args.get('review_count', 0, type=int)
    # 기존 count 파라미터도 호환
    if photo_count == 0:
        photo_count = request.args.get('count', 0, type=int)
    return render_template('upload_complete.html', project=project, 
                           photo_count=photo_count, review_count=review_count)

# ==================== 관리자 페이지 ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """관리자 로그인"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == app.config['ADMIN_PASSWORD']:
            session['is_admin'] = True
            flash('로그인 성공!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('비밀번호가 틀립니다.', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """관리자 로그아웃"""
    session.pop('is_admin', None)
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('index'))

def admin_required(f):
    """관리자 인증 데코레이터"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('관리자 로그인이 필요합니다.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_dashboard():
    """관리자 대시보드"""
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('admin_dashboard.html', projects=projects)

@app.route('/admin/project/new', methods=['GET', 'POST'])
@admin_required
def admin_project_new():
    """새 프로젝트 생성"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            flash('프로젝트 이름을 입력해주세요.', 'error')
            return render_template('admin_project_form.html', project=None)
        
        folder_name = sanitize_folder_name(name) + '_' + uuid.uuid4().hex[:8]
        
        project = Project(
            name=name,
            description=description,
            folder_name=folder_name
        )
        db.session.add(project)
        db.session.commit()
        
        flash(f'프로젝트 "{name}"이 생성되었습니다!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin_project_form.html', project=None)

@app.route('/admin/project/<int:project_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_project_edit(project_id):
    """프로젝트 수정"""
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        project.name = request.form.get('name', '').strip()
        project.description = request.form.get('description', '').strip()
        project.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        
        flash('프로젝트가 수정되었습니다.', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin_project_form.html', project=project)

@app.route('/admin/project/<int:project_id>/delete', methods=['POST'])
@admin_required
def admin_project_delete(project_id):
    """프로젝트 삭제"""
    project = Project.query.get_or_404(project_id)
    
    # S3에서 파일들 삭제
    s3 = get_s3_client()
    for photo in project.photos:
        try:
            s3.delete_object(Bucket=app.config['S3_BUCKET_NAME'], Key=photo.s3_key)
        except:
            pass
    
    db.session.delete(project)
    db.session.commit()
    
    flash(f'프로젝트 "{project.name}"이 삭제되었습니다.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/project/<int:project_id>')
@admin_required
def admin_project_detail(project_id):
    """프로젝트 상세 - 사진 목록"""
    project = Project.query.get_or_404(project_id)
    
    # 업로더별 그룹핑
    uploaders = {}
    for photo in project.photos:
        if photo.uploader_name not in uploaders:
            uploaders[photo.uploader_name] = []
        uploaders[photo.uploader_name].append(photo)
    
    return render_template('admin_project_detail.html', project=project, uploaders=uploaders)

@app.route('/admin/photo/<int:photo_id>/download')
@admin_required
def admin_photo_download(photo_id):
    """개별 사진 다운로드"""
    photo = Photo.query.get_or_404(photo_id)
    
    s3 = get_s3_client()
    try:
        response = s3.get_object(Bucket=app.config['S3_BUCKET_NAME'], Key=photo.s3_key)
        
        # 다운로드 표시
        photo.is_downloaded = True
        photo.downloaded_at = datetime.utcnow()
        db.session.commit()
        
        return send_file(
            io.BytesIO(response['Body'].read()),
            download_name=f"{photo.uploader_name}_{photo.original_filename}",
            as_attachment=True
        )
    except ClientError as e:
        flash(f'다운로드 오류: {str(e)}', 'error')
        return redirect(url_for('admin_project_detail', project_id=photo.project_id))

@app.route('/admin/photo/<int:photo_id>/preview')
@admin_required
def admin_photo_preview(photo_id):
    """사진 미리보기 URL (presigned)"""
    photo = Photo.query.get_or_404(photo_id)
    
    s3 = get_s3_client()
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': app.config['S3_BUCKET_NAME'], 'Key': photo.s3_key},
            ExpiresIn=3600
        )
        return jsonify({'url': url})
    except ClientError:
        return jsonify({'error': 'URL 생성 실패'}), 500

@app.route('/admin/project/<int:project_id>/download-all')
@admin_required
def admin_project_download_all(project_id):
    """프로젝트 전체 ZIP 다운로드"""
    project = Project.query.get_or_404(project_id)
    
    if not project.photos:
        flash('다운로드할 사진이 없습니다.', 'error')
        return redirect(url_for('admin_project_detail', project_id=project_id))
    
    s3 = get_s3_client()
    
    # ZIP 파일 생성
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for photo in project.photos:
            try:
                response = s3.get_object(Bucket=app.config['S3_BUCKET_NAME'], Key=photo.s3_key)
                file_data = response['Body'].read()
                
                # 업로더별 폴더로 구분
                zip_path = f"{photo.uploader_name}/{photo.original_filename}"
                zip_file.writestr(zip_path, file_data)
                
                # 다운로드 표시
                photo.is_downloaded = True
                photo.downloaded_at = datetime.utcnow()
                
            except ClientError:
                continue
    
    db.session.commit()
    zip_buffer.seek(0)
    
    return send_file(
        zip_buffer,
        download_name=f"{project.name}_전체사진.zip",
        as_attachment=True,
        mimetype='application/zip'
    )

@app.route('/admin/uploader/<int:project_id>/<uploader_name>/download')
@admin_required
def admin_uploader_download(project_id, uploader_name):
    """특정 업로더의 사진만 ZIP 다운로드"""
    project = Project.query.get_or_404(project_id)
    photos = Photo.query.filter_by(project_id=project_id, uploader_name=uploader_name).all()
    
    if not photos:
        flash('다운로드할 사진이 없습니다.', 'error')
        return redirect(url_for('admin_project_detail', project_id=project_id))
    
    s3 = get_s3_client()
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for photo in photos:
            try:
                response = s3.get_object(Bucket=app.config['S3_BUCKET_NAME'], Key=photo.s3_key)
                file_data = response['Body'].read()
                zip_file.writestr(photo.original_filename, file_data)
                
                photo.is_downloaded = True
                photo.downloaded_at = datetime.utcnow()
                
            except ClientError:
                continue
    
    db.session.commit()
    zip_buffer.seek(0)
    
    return send_file(
        zip_buffer,
        download_name=f"{project.name}_{uploader_name}.zip",
        as_attachment=True,
        mimetype='application/zip'
    )

@app.route('/admin/photo/<int:photo_id>/delete', methods=['POST'])
@admin_required
def admin_photo_delete(photo_id):
    """개별 사진 삭제"""
    photo = Photo.query.get_or_404(photo_id)
    project_id = photo.project_id
    
    s3 = get_s3_client()
    try:
        s3.delete_object(Bucket=app.config['S3_BUCKET_NAME'], Key=photo.s3_key)
    except:
        pass
    
    db.session.delete(photo)
    db.session.commit()
    
    flash('사진이 삭제되었습니다.', 'success')
    return redirect(url_for('admin_project_detail', project_id=project_id))

# DB 초기화
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


@app.route('/upload/<int:project_id>/text', methods=['GET', 'POST'])
def upload_text(project_id):
    """텍스트(리뷰) 제출 페이지"""
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        uploader_name = request.form.get('uploader_name', '').strip()
        
        if not uploader_name:
            flash('업로더 이름을 입력해주세요.')
            return redirect(url_for('upload_text', project_id=project_id))
        
        reviews = []
        for i in range(1, 6):
            review = request.form.get(f'review_{i}', '').strip()
            if review:
                reviews.append(review)
        
        if not reviews:
            flash('최소 1개 이상의 리뷰를 입력해주세요.')
            return redirect(url_for('upload_text', project_id=project_id))
        
        success, message = save_reviews_to_sheets(uploader_name, project.name, reviews)
        
        if success:
            flash(f'리뷰 {message}')
            return redirect(url_for('upload_text_complete', project_id=project_id, count=len(reviews)))
        else:
            flash(f'저장 실패: {message}')
            return redirect(url_for('upload_text', project_id=project_id))
    
    return render_template('upload_text.html', project=project)


@app.route('/upload/<int:project_id>/text/complete')
def upload_text_complete(project_id):
    """텍스트 제출 완료 페이지"""
    project = Project.query.get_or_404(project_id)
    count = request.args.get('count', 0, type=int)
    return render_template('upload_text_complete.html', project=project, count=count)
