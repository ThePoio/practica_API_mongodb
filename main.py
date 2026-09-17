from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field, field_validator, ConfigDict
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import ReturnDocument
import os



load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("La variable MONGODB_URI no está definida en el archivo .env")
DB_NAME = os.getenv("MONGODB_DB", "Actividad1_noSQL")
COLL_ESTUDIANTES = os.getenv("COLL_ESTUDIANTES", "estudiantes")

@asynccontextmanager
async def lifespan(app: FastAPI):
# STARTUP: Conexión al iniciar
    global client, db, estudiantes
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME] 
    estudiantes = db[COLL_ESTUDIANTES]
    yield # La aplicación se mantiene activa
    # SHUTDOWN: Cierre de conexión al apagar
    if client:
        client.close()

app = FastAPI(
    title="API con FastAPI y MongoDB Atlas",
    lifespan=lifespan
)

class EstudianteIn(BaseModel):
    nombre: str
    email: str
    carrera: str
    semestre: int

class EstudianteOut(EstudianteIn):
    id: str = Field(alias="_id")
    @field_validator("id", mode="before")
    def objectid_to_str(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        return v
    model_config = ConfigDict(populate_by_name=True,
arbitrary_types_allowed=True)

@app.get("/")
def home():
    return {"ok": True}

@app.get("/estudiantes", response_model=list[EstudianteOut])
async def listar_estudiantes():
    return await estudiantes.find({}).to_list(length=50)

@app.get("/estudiantes/{id}", response_model=EstudianteOut)
async def obtener_estudiante(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="ID inválido.")
    doc = await estudiantes.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado.")
    return EstudianteOut(**doc)

@app.post("/estudiantes", response_model=EstudianteOut,
status_code=status.HTTP_201_CREATED)
async def crear_estudiante(e: EstudianteIn):
    result = await estudiantes.insert_one(e.model_dump())
    nuevo = await estudiantes.find_one({"_id": result.inserted_id})
    return nuevo

@app.put("/estudiantes/{id}", response_model=EstudianteOut)
async def actualizar_estudiante(id: str, e: EstudianteIn):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="ID inválido.")
    result = await estudiantes.find_one_and_update(
        {"_id": ObjectId(id)},
        {"$set": e.model_dump()},
        return_document=ReturnDocument.AFTER
)
    if not result:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado.")
    return result