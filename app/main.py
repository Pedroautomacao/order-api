from fastapi import FastAPI

app = FastAPI(title="Order API")


@app.get("/health")
def health_check():
    return {"status": "ok"}
