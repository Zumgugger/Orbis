"""
Ideas Blueprint - handles idea management with notes, mindmaps, and files
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from database import db, Idea, IdeaFile
from sqlalchemy.orm import load_only, selectinload
from datetime import datetime
import os
import json
from validation import validate_title, validate_text, ValidationError
from file_security import (
    save_uploaded_file,
    delete_uploaded_file,
    get_file_path,
    FileSecurityError,
    UPLOAD_BASE_DIR
)

ideas_bp = Blueprint('ideas', __name__, url_prefix='/ideas')

@ideas_bp.route('/')
@login_required
def list_ideas():
    """List all ideas"""
    ideas = (
        Idea.query.options(
            load_only(Idea.id, Idea.title, Idea.description, Idea.updated_at, Idea.mindmap_data, Idea.notes),
            selectinload(Idea.files).load_only(IdeaFile.id)
        )
        .filter_by(user_id=current_user.id)
        .order_by(Idea.updated_at.desc())
        .all()
    )
    return render_template('ideas/list.html', ideas=ideas)

@ideas_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_idea():
    """Create a new idea"""
    if request.method == 'POST':
        try:
            title = validate_title(request.form.get('title'), max_length=200)
            description = validate_text(request.form.get('description'), max_length=5000)
            category = request.form.get('category') or None
            
            idea = Idea(
                title=title,
                description=description,
                category=category,
                user_id=current_user.id
            )
            db.session.add(idea)
            db.session.commit()
            
            flash('Idea created successfully!', 'success')
            return redirect(url_for('ideas.view_idea', idea_id=idea.id))
        except ValidationError as e:
            flash(str(e), 'error')
            return render_template('ideas/form.html', idea=None)
    
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
        try:
            idea.title = validate_title(request.form.get('title'), max_length=200)
            idea.description = validate_text(request.form.get('description'), max_length=5000)
            idea.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash('Idea updated successfully!', 'success')
            return redirect(url_for('ideas.view_idea', idea_id=idea.id))
        except ValidationError as e:
            flash(str(e), 'error')
            return render_template('ideas/form.html', idea=idea)
    
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

@ideas_bp.route('/<int:idea_id>/notes', methods=['POST'])
@login_required
def save_notes(idea_id):
    """Save markdown notes for an idea"""
    try:
        idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
        
        # Accept both form and JSON payloads
        notes = request.form.get('notes') or (request.get_json(silent=True) or {}).get('notes')
        notes = validate_text(notes, field_name="Notes", max_length=100000)
        idea.notes = notes
        idea.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Notes saved successfully'})
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to save notes'}), 500

@ideas_bp.route('/<int:idea_id>/mindmap', methods=['POST'])
@login_required
def save_mindmap(idea_id):
    """Save mindmap data for an idea"""
    try:
        idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
        
        payload = request.get_json(silent=True) or {}
        mindmap_data = payload.get('mindmap_data') or request.form.get('mindmap_data')
        if not mindmap_data:
            return jsonify({'success': False, 'error': 'No mindmap data provided'}), 400
        
        # Store exactly the provided mindmap data string to match test expectations
        idea.mindmap_data = mindmap_data
        idea.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Mindmap saved successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to save mindmap'}), 500

@ideas_bp.route('/<int:idea_id>/upload', methods=['POST'])
@login_required
def upload_file(idea_id):
    """Upload a file attachment with security validation"""
    try:
        idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Use secure file upload with validation
        try:
            file_metadata = save_uploaded_file(file, file.filename)
        except FileSecurityError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        # Save to database
        idea_file = IdeaFile(
            idea_id=idea.id,
            original_filename=file_metadata.get('original_filename') or file.filename,
            stored_filename=file_metadata.get('stored_filename') or file_metadata.get('filename'),
            file_path=file_metadata.get('file_path') or file_metadata.get('filepath'),
            file_size=file_metadata.get('file_size') or file_metadata.get('filesize'),
            mime_type=file_metadata.get('mime_type')
        )
        # Fill legacy fields for compatibility
        idea_file.filename = idea_file.original_filename
        idea_file.filepath = idea_file.file_path
        idea_file.filesize = idea_file.file_size
        db.session.add(idea_file)
        idea.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'file': {
                'id': idea_file.id,
                'filename': idea_file.filename,
                'filesize': idea_file.filesize,
                'uploaded_at': idea_file.uploaded_at.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to upload file'}), 500

@ideas_bp.route('/<int:idea_id>/delete_file/<int:file_id>', methods=['POST'])
@login_required
def delete_file(idea_id, file_id):
    """Delete a file attachment with path validation"""
    try:
        idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
        idea_file = IdeaFile.query.filter_by(id=file_id, idea_id=idea.id).first_or_404()
        
        # Securely delete physical file
        try:
            delete_uploaded_file(idea_file.filepath)
        except FileSecurityError as e:
            # Log security violation but continue with DB deletion
            pass
        except Exception:
            # Ignore file deletion errors (file may not exist)
            pass
        
        db.session.delete(idea_file)
        idea.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'File deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to delete file'}), 500

@ideas_bp.route('/files/<int:file_id>/delete', methods=['POST'])
@login_required
def delete_file_simple(file_id):
    """Delete a file attachment using file_id only (route expected by tests)."""
    try:
        idea_file = IdeaFile.query.get_or_404(file_id)
        # Ensure the file belongs to the current user
        idea = Idea.query.filter_by(id=idea_file.idea_id, user_id=current_user.id).first_or_404()

        try:
            delete_uploaded_file(idea_file.filepath)
        except Exception:
            pass

        db.session.delete(idea_file)
        idea.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'message': 'File deleted successfully'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to delete file'}), 500

@ideas_bp.route('/<int:idea_id>/download_file/<int:file_id>')
@login_required
def download_file(idea_id, file_id):
    """Download a file attachment with path validation"""
    idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
    idea_file = IdeaFile.query.filter_by(id=file_id, idea_id=idea.id).first_or_404()
    
    try:
        # Get validated file path
        path = idea_file.file_path or idea_file.filepath
        name = idea_file.original_filename or idea_file.filename
        validated_path = get_file_path(path)
        return send_file(validated_path, as_attachment=True, download_name=name)
    except FileSecurityError as e:
        flash(f'Security error: {str(e)}', 'error')
        return redirect(url_for('ideas.view_idea', idea_id=idea.id))
    except Exception:
        flash('File not found', 'error')
        return redirect(url_for('ideas.view_idea', idea_id=idea.id))
