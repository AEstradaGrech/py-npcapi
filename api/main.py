from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.gameagent_api import router as agents_router 
from api.routes.datagen_api import router as datagen_router 
from api.routes.chats_mgmt_api import router as chatsmgmt_router 
from api.routes.praisebotapi import router as praisebot_router
from api.routes.summaries_api import router as summaries_router 
from api.routes.sysmsgs_api import router as sysmsgs_router  
from api.routes.devtests_api import router as devtests_router  

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
app.include_router(datagen_router)
app.include_router(chatsmgmt_router)
app.include_router(praisebot_router)
app.include_router(summaries_router)
app.include_router(sysmsgs_router)
app.include_router(agents_router)
app.include_router(devtests_router)