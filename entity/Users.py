class Users:
    def __init__(self, id=None, username=None, password=None):
        self.id = id
        self.username = username
        self.password = password

    def __str__(self):
        return f"User(id={self.id}, username={self.username})"