from flask import session


def test_index_redirect(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.location == "/login"


def test_login_success(client, regular_user, verify_id_token_mock):
    response = client.post(
        "/login",
        data={"idToken": "test_token"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Login successful!" in response.data
    assert session["user_id"] == regular_user.id


def test_login_failure(client, mocker):
    mocker.patch("src.cambios.firebase.verify_id_token", side_effect=ValueError)
    response = client.post(
        "/login",
        data={"idToken": "invalid_token"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Login failed. Please try again." in response.data


def test_logout(client, regular_user, verify_id_token_mock):
    client.post("/login", data={"idToken": "test_token"})
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data
    assert "user_id" not in session


def test_upload_get(client, regular_user, verify_id_token_mock):
    client.post("/login", data={"idToken": "test_token"})
    response = client.get("/upload")
    assert response.status_code == 200
    assert b"Carga de Turnero" in response.data


def test_upload_post_no_file(client, regular_user, verify_id_token_mock):
    client.post("/login", data={"idToken": "test_token"})
    response = client.post("/upload", data={}, follow_redirects=True)
    assert response.status_code == 200
    assert b"No file selected" in response.data
