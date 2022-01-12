#!./envlinux/bin/python
import os
from app import app

if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run()
