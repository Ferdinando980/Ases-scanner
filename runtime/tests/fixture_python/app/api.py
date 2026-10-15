from fastapi import FastAPI
app = FastAPI()

def login_required(fn):
    return fn

@app.get("/users")
@login_required
def list_users():
    return load_users()

def load_users():
    return []
