from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.routes.gameagent_api import router as agents_router 

origins = [
    "http://localhost",
    "http://localhost:4200",
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router)
