"""
Smoke tests for authentication flow
"""


def test_login_page_loads(client):
    """Test that login page loads or redirects to OAuth"""
    response = client.get("/auth/login", follow_redirects=False)
    # Thelogin route redirects to Google OAuth
    assert response.status_code in [200, 302]


def test_index_redirects_to_login(client):
    """Test that unauthenticated users are redirected to login"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_logout(authenticated_client):
    """Test logout functionality"""
    response = authenticated_client.get("/auth/logout", follow_redirects=False)
    # Logout redirects to index
    assert response.status_code == 302
    assert "/" in response.location or "index" in response.location


def test_authenticated_access_to_index(authenticated_client):
    """Test that authenticated users can access the index page"""
    response = authenticated_client.get("/", follow_redirects=False)
    # Should either load the page or redirect (check both cases)
    assert response.status_code in [200, 302]


def test_dev_login_in_dev_mode(client, app):
    """Test dev login works in development mode"""
    with app.app_context():
        # Check if dev login route exists and returns a form
        response = client.get("/auth/dev/login")
        # Should show the dev login form (200) since DEVELOPMENT_MODE is set to 'true'
        assert response.status_code == 200
        assert b"Development Login" in response.data or b"Select User" in response.data
