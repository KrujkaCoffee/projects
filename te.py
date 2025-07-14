from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def read_root():
    file_path = "file:///Z:\MES_setup\Setup.lnk"
    return f'<a href="{file_path}">Открыть файл</a>'

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi.middleware.cors import CORSMiddleware


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)