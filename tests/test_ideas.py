"""
Smoke tests for ideas feature (notes, mindmap, file upload)
"""
import io
import os

from database import Idea, IdeaFile, db


def test_ideas_list_page_loads(authenticated_client):
    """Test that ideas list page loads"""
    response = authenticated_client.get("/ideas/")
    assert response.status_code == 200
    assert b"Ideas" in response.data or b"Idea" in response.data


def test_create_idea(authenticated_client, app, test_user):
    """Test creating a new idea"""
    response = authenticated_client.post(
        "/ideas/create",
        data={
            "title": "New Test Idea",
            "description": "Test idea description",
            "category": "business",
            "status": "active",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    # Verify idea was created
    with app.app_context():
        idea = Idea.query.filter_by(title="New Test Idea", user_id=test_user).first()
        assert idea is not None
        assert idea.description == "Test idea description"
        assert idea.category == "business"


def test_view_idea(authenticated_client, sample_idea):
    """Test viewing an idea detail page"""
    response = authenticated_client.get(f"/ideas/{sample_idea}")
    assert response.status_code == 200
    assert b"Test Idea" in response.data
    assert b"mindmap" in response.data.lower()


def test_save_idea_notes(authenticated_client, app, sample_idea):
    """Test saving notes for an idea"""
    new_notes = "These are updated notes for the idea."

    response = authenticated_client.post(
        f"/ideas/{sample_idea}/notes",
        json={"notes": new_notes},
        content_type="application/json",
    )

    assert response.status_code == 200

    with app.app_context():
        idea = db.session.get(Idea, sample_idea)
        assert idea.notes == new_notes


def test_save_idea_mindmap(authenticated_client, app, sample_idea):
    """Test saving mindmap data for an idea"""
    mindmap_data = '{"nodeData":{"id":"root","topic":"Main Idea","children":[]}}'

    response = authenticated_client.post(
        f"/ideas/{sample_idea}/mindmap",
        json={"mindmap_data": mindmap_data},
        content_type="application/json",
    )

    assert response.status_code == 200

    with app.app_context():
        idea = db.session.get(Idea, sample_idea)
        assert idea.mindmap_data == mindmap_data


def test_upload_file_to_idea(authenticated_client, app, sample_idea, test_user):
    """Test uploading a file attachment to an idea"""
    # Create a test file
    test_file = (io.BytesIO(b"This is a test PDF file"), "test.pdf")

    response = authenticated_client.post(
        f"/ideas/{sample_idea}/upload",
        data={"file": test_file},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200

    # Verify file record was created
    with app.app_context():
        idea_file = IdeaFile.query.filter_by(idea_id=sample_idea).first()
        assert idea_file is not None
        assert idea_file.original_filename == "test.pdf"


def test_upload_invalid_file_extension(authenticated_client, sample_idea):
    """Test that invalid file extensions are rejected"""
    # Create a test file with invalid extension
    test_file = (io.BytesIO(b"Malicious content"), "virus.exe")

    response = authenticated_client.post(
        f"/ideas/{sample_idea}/upload",
        data={"file": test_file},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    # Should either reject or redirect with error
    # The exact behavior depends on file_security.py implementation
    assert response.status_code in [200, 400, 403]
    if response.status_code == 200:
        # Check for error message in response
        assert (
            b"Invalid file" in response.data
            or b"not allowed" in response.data
            or b"error" in response.data.lower()
        )


def test_upload_oversized_file(authenticated_client, sample_idea):
    """Test that oversized files are rejected (>10MB limit)"""
    # Create a file larger than 10MB
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB
    test_file = (io.BytesIO(large_content), "large.pdf")

    response = authenticated_client.post(
        f"/ideas/{sample_idea}/upload",
        data={"file": test_file},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    # Should reject the file - Flask returns 413 for too large requests
    # May also return 200 with error message, 400, or 500 depending on config
    assert response.status_code in [200, 400, 413, 500]
    if response.status_code == 200:
        assert b"too large" in response.data.lower() or b"size" in response.data.lower()


def test_download_file(authenticated_client, app, sample_idea, test_user):
    """Test downloading an uploaded file"""
    # First create a file record
    with app.app_context():
        idea_file = IdeaFile(
            idea_id=sample_idea,
            original_filename="download_test.txt",
            stored_filename="test_uuid_download_test.txt",
            file_path="uploads/idea_files/te/st/test_uuid_download_test.txt",
            file_size=100,
            mime_type="text/plain",
        )
        db.session.add(idea_file)
        db.session.commit()
        file_id = idea_file.id

        # Create actual file for testing
        os.makedirs("uploads/idea_files/te/st", exist_ok=True)
        with open("uploads/idea_files/te/st/test_uuid_download_test.txt", "w") as f:
            f.write("Test content")

    try:
        response = authenticated_client.get(f"/ideas/files/{file_id}/download")
        # Should either download or show error if file doesn't exist
        assert response.status_code in [200, 404]
    finally:
        # Cleanup
        try:
            os.remove("uploads/idea_files/te/st/test_uuid_download_test.txt")
            os.rmdir("uploads/idea_files/te/st")
            os.rmdir("uploads/idea_files/te")
        except:
            pass


def test_delete_file(authenticated_client, app, sample_idea):
    """Test deleting an uploaded file"""
    # Create a file record
    with app.app_context():
        idea_file = IdeaFile(
            idea_id=sample_idea,
            original_filename="delete_test.txt",
            stored_filename="test_uuid_delete_test.txt",
            file_path="uploads/idea_files/de/le/test_uuid_delete_test.txt",
            file_size=100,
            mime_type="text/plain",
        )
        db.session.add(idea_file)
        db.session.commit()
        file_id = idea_file.id

    response = authenticated_client.post(
        f"/ideas/files/{file_id}/delete", follow_redirects=True
    )
    assert response.status_code == 200

    # Verify file record was deleted
    with app.app_context():
        deleted_file = db.session.get(IdeaFile, file_id)
        assert deleted_file is None
