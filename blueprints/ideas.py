"""
Ideas Blueprint - handles idea management with notes, mindmaps, and files
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from database import db, Idea, IdeaFile
from datetime import datetime
import os
import json
from werkzeug.utils import secure_filename

ideas_bp = Blueprint('ideas', __name__, url_prefix='/ideas')

UPLOAD_FOLDER = 'instance/idea_files'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'md'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@ideas_bp.route('/')
@login_required
def list_ideas():
    """List all ideas"""
    ideas = Idea.query.filter_by(user_id=current_user.id).order_by(Idea.updated_at.desc()).all()
    return render_template('ideas/list.html', ideas=ideas)

@ideas_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_idea():
    """Create a new idea"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        if not title:
            flash('Title is required!', 'error')
            return redirect(url_for('ideas.create_idea'))
        
        idea = Idea(
            title=title,
            description=description,
            user_id=current_user.id
        )
        db.session.add(idea)
        db.session.commit()
        
        flash('Idea created successfully!', 'success')
        return redirect(url_for('ideas.view_idea', idea_id=idea.id))
    
    return render_template('ideas/form.html', idea=None)

@ideas_bp.route('/<int:idea_id>')
@login_required
def view_idea(idea_id):
    """View and edit an idea"""
    idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
    return render_template('ideas/view.html', idea=idea)

@ideas_bp.route('/<int:idea_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_idea(idea_id):
    """Edit idea title and description"""
    idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        idea.title = request.form.get('title')
        idea.description = request.form.get('description')
        idea.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Idea updated successfully!', 'success')
        return redirect(url_for('ideas.view_idea', idea_id=idea.id))
    
    return render_template('ideas/form.html', idea=idea)

@ideas_bp.route('/<int:idea_id>/delete', methods=['POST'])
@login_required
def delete_idea(idea_id):
    """Delete an idea"""
    idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
    
    # Delete associated files
    for file in idea.files:
        try:
            if os.path.exists(file.filepath):
                os.remove(file.filepath)
        except:
            pass
    
    db.session.delete(idea)
    db.session.commit()
    
    flash('Idea deleted successfully!', 'success')
    return redirect(url_for('ideas.list_ideas'))

@ideas_bp.route('/<int:idea_id>/save_notes', methods=['POST'])
@login_required
def save_notes(idea_id):
    """Save markdown notes for an idea"""
    idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
    
    notes = request.form.get('notes', '')
    idea.notes = notes
    idea.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Notes saved successfully'})

@ideas_bp.route('/<int:idea_id>/save_mindmap', methods=['POST'])
@login_required
def save_mindmap(idea_id):
    """Save mindmap data for an idea"""
    idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
    
    mindmap_data = request.get_json()
    idea.set_mindmap_data(mindmap_data)
    idea.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Mindmap saved successfully'})

@ideas_bp.route('/<int:idea_id>/upload_file', methods=['POST'])
@login_required
def upload_file(idea_id):
    """Upload a file attachment"""
    idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        # Create upload folder if it doesn't exist
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        filename = secure_filename(file.filename)
        # Add timestamp to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        file.save(filepath)
        filesize = os.path.getsize(filepath)
        
        idea_file = IdeaFile(
            idea_id=idea.id,
            filename=file.filename,
            filepath=filepath,
            filesize=filesize
        )
        db.session.add(idea_file)
        idea.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'File uploaded successfully', 'file': {
            'id': idea_file.id,
            'filename': idea_file.filename,
            'filesize': idea_file.filesize,
            'uploaded_at': idea_file.uploaded_at.isoformat()
        }})
    
    return jsonify({'success': False, 'message': 'Invalid file type'}), 400

@ideas_bp.route('/<int:idea_id>/delete_file/<int:file_id>', methods=['POST'])
@login_required
def delete_file(idea_id, file_id):
    """Delete a file attachment"""
    idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
    idea_file = IdeaFile.query.filter_by(id=file_id, idea_id=idea.id).first_or_404()
    
    # Delete physical file
    try:
        if os.path.exists(idea_file.filepath):
            os.remove(idea_file.filepath)
    except:
        pass
    
    db.session.delete(idea_file)
    idea.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'File deleted successfully'})

@ideas_bp.route('/<int:idea_id>/download_file/<int:file_id>')
@login_required
def download_file(idea_id, file_id):
    """Download a file attachment"""
    idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
    idea_file = IdeaFile.query.filter_by(id=file_id, idea_id=idea.id).first_or_404()
    
    if os.path.exists(idea_file.filepath):
        return send_file(idea_file.filepath, as_attachment=True, download_name=idea_file.filename)
    
    flash('File not found', 'error')
    return redirect(url_for('ideas.view_idea', idea_id=idea.id))
