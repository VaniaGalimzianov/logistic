from fastapi import FastAPI, Form, Request, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
import hashlib
from urllib.parse import unquote

from utils.db_handler import DbHandler


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="static")
pg_handler = DbHandler()

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


class WorkerCredentials(BaseModel):
    worker_code: int
    password: str


class CarInfo(BaseModel):
    name: str
    payload: int
    length: float
    width: float
    height: float
    status: str = "Свободно"


class OptionalCar(BaseModel):
    payload: int
    dimensions: str

@app.post("/login")
async def login(credentials: WorkerCredentials):
    employee_code, password = credentials.worker_code, credentials.password

    name = pg_handler.check_credentials(int(employee_code), password)
    if name:
        name = unquote(name)
        print(name)
        return RedirectResponse(url=f"/main?name={name}", status_code=303)


@app.get("/register", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/main", response_class=HTMLResponse)
async def main_page(request: Request, name: str = Query(None)):
    return templates.TemplateResponse("index.html", {"request": request, "name": name})


@app.get("/main/view", response_class=HTMLResponse)
async def view_page(request: Request):
    # Получение данных из БД
    cars_data = pg_handler.get_all_cars()
    cars_info = [CarInfo(**car) for car in cars_data]
    
    # Передача данных в Jinja2
    return templates.TemplateResponse("view.html", {"request": request, "rows": cars_info})


@app.post("/main/booking/get_cars", response_class=HTMLResponse)
async def view_page_handler(car_params: OptionalCar, request: Request):
    payload, dim = car_params.payload, car_params.dimensions
    length, width, heigth = dim.split(", ")
    print("[INFO]: findTransport")
    # Получение данных из БД
    cars_data = pg_handler.find_optimal_cars(
        payload_needed=payload,
        length_needed=float(length),
        width_needed=float(width),
        height_needed=float(heigth)
    )
    cars_info = [CarInfo(**car) for car in cars_data]
    
    # Передача данных в Jinja2
    return templates.TemplateResponse("booking_table.html", {"request": request, "rows": cars_info}).body.decode("utf-8")

@app.get("/main/booking", response_class=HTMLResponse)
async def booking_page(request: Request):
    return templates.TemplateResponse("booking.html", {"request": request})


@app.get("/main/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.post("/main/admin/add_car")
async def add_cars(car: CarInfo):
    if car:
        status_code = pg_handler.insert_car(
            name=car.name,
            payload=car.payload,
            length=car.length,
            width=car.width,
            height=car.height,
        )

    if status_code == 201:
        return {"message": "Автомобиль успешно добавлен"}
    
    else:
        raise HTTPException(
            detail="Произошла ошибка при добавлении авто в базу данных"
        )
    

@app.post("/main/admin/add_car_excel")
async def add_cars_excel(file: UploadFile = File(...)):
    if file.filename.endswith(".xlsx"):
        contents = await file.read()
        status_code = pg_handler.add_car_file(contents)
        
        if status_code == 201:
            return {"message": "Автомобиль успешно добавлен"}
        else:
            raise HTTPException(
                status_code=status_code,
                detail="Произошла ошибка при добавлении авто в базу данных"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Неверный формат файла. Пожалуйста, загрузите файл Excel (.xlsx)"
        )


@app.patch("/main/booking/get_cars/update_info")
async def update_car_info(car: CarInfo):
    # Отправка в db
    try:
        pg_handler.update_car_status(
            name=car.name,
            payload=car.payload,
            length=car.length,
            width=car.width,
            height=car.height,
            status=car.status,
        )
    
    except Exception as e:
        print(f"Ошибка добавления в базу данных: {e}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
