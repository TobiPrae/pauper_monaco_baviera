from auth import hash_password, check_password


def test_hash_and_check():
    pwd = "s3cret"
    h = hash_password(pwd)
    assert check_password(pwd, h)
    assert not check_password("wrong", h)
