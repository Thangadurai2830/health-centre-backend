from app.core.security import generate_otp_code, hash_password, verify_password


def test_generate_otp_code_length():
    code = generate_otp_code(6)
    assert len(code) == 6
    assert code.isdigit()


def test_generate_otp_code_is_random():
    codes = {generate_otp_code(6) for _ in range(20)}
    assert len(codes) > 1


def test_otp_hash_and_verify_roundtrip():
    code = "123456"
    hashed = hash_password(code)
    assert hashed != code
    assert verify_password(code, hashed) is True
    assert verify_password("654321", hashed) is False
