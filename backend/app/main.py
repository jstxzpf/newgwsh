from fastapi import FastAPI

app = FastAPI(title="泰兴调查队公文处理系统 V3.0")

@app.get("/health")
async def health_check():
    return {"status": "ok"}