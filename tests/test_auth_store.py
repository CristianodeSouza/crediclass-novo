from pathlib import Path

import backend.auth_store as auth_store


def setup_store(tmp_path: Path):
    auth_store.AUTH_DB_PATH = tmp_path / "auth.sqlite3"
    auth_store.init_auth_store({
        "adm": {"password": "admin-password", "name": "Administrador", "role": "Administrador"},
    })


def test_invitation_activation_does_not_expose_password(tmp_path):
    setup_store(tmp_path)
    admin = auth_store.get_user("adm")
    user, token = auth_store.create_invitation("Ana Operadora", "ana@example.com", "5511999999999", "Operador", admin["id"])

    assert user["status"] == "Convite pendente"
    assert "password" not in user
    activated = auth_store.activate_invitation(token, "senha-segura-123")
    assert activated["status"] == "Ativo"
    assert auth_store.authenticate("ana@example.com", "senha-segura-123")["email"] == "ana@example.com"
    assert auth_store.activate_invitation(token, "outra-senha-123") is None


def test_inactive_user_cannot_authenticate_and_session_is_revoked(tmp_path):
    setup_store(tmp_path)
    admin = auth_store.get_user("adm")
    user, token = auth_store.create_invitation("Bruno Operador", "bruno@example.com", "5511888888888", "Operador", admin["id"])
    activated = auth_store.activate_invitation(token, "senha-segura-123")
    session = auth_store.create_session(activated["id"])
    assert auth_store.get_session(session) is not None

    auth_store.set_user_status(user["id"], "Inativo", admin["id"])
    assert auth_store.authenticate("bruno@example.com", "senha-segura-123") is None
    assert auth_store.get_session(session) is None


def test_wrong_password_and_explicit_session_revocation(tmp_path):
    setup_store(tmp_path)
    admin = auth_store.get_user("adm")
    user, token = auth_store.create_invitation("Carla Operadora", "carla@example.com", "5511777777777", "Operador", admin["id"])
    activated = auth_store.activate_invitation(token, "senha-segura-123")
    assert auth_store.authenticate("carla@example.com", "senha-errada") is None
    session = auth_store.create_session(activated["id"])
    auth_store.revoke_session(session)
    assert auth_store.get_session(session) is None
