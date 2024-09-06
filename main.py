from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
import io
import logging
# new package for cron task
import aiocron
import aiohttp
from datetime import datetime, time


app = FastAPI()

''' 
async def is_active_hours():
    now = datetime.now().time()
    return time(9,0) <= now <= time(18,0) # assume active time between 9:00 and 18:00
'''
@aiocron.crontab('*/10 * * * *')
async def self_ping():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://recieptapi.onrender.com/health') as response:
            print(f"Health check response: {response.status}")
   
@app.on_event("startup")
async def startup_event():
    self_ping.start()


# set log
# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mindee_endpoint = "https://api.mindee.net/v1/products/mindee/expense_receipts/v5/predict"
mindee_api_key = "413c3140cb93daff17536ec583083000"
@app.post("/upload/")
async def create_upload_file(uploaded_file: UploadFile = File(...)):
    if not uploaded_file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        raise HTTPException(status_code=415, detail="Unsupported file type")
    
    try:
        contents = await uploaded_file.read()
        logger.info(f"File size: {len(contents)} bytes")
        #使用Mindee API
        headers = {
            "Authorization": f"Token {mindee_api_key}"
        }
        files = {
            "document": (uploaded_file.filename, contents, uploaded_file.content_type)
        }
        r = requests.post(mindee_endpoint, headers=headers, files=files)
        '''
        r = requests.post(receiptOcrEndpoint, data={
            'client_id': 'TEST',
            'recognizer': 'auto',
            'ref_no': 'ocr_python_123',
        }, files={"file": (uploaded_file.filename, io.BytesIO(contents), uploaded_file.content_type)})
        '''
        logger.info(f"OCR Service Response status code: {r.status_code}")
        logger.info(f"OCR Service Response content: {r.text[:200]}...")  # 记录响应的前200个字符

        r.raise_for_status()  # 如果响应状态码不是200，将引发异常
        data = r.json()
        
        item_list = []
        if 'document' in data and 'inference' in data['document'] and 'prediction' in data['document']['inference']:
            line_items = data['document']['inference']['prediction'].get('line_items', [])
            item_list = [
                {
                    "description": item.get('description', ''),
                    "qty": item.get('quantity', '1')
                }
                for item in line_items
            ]
        
        return {"item_list": item_list}
        
    except requests.RequestException as e:
        logger.error(f"OCR Service request fail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR Service Request fail: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"OCR Service Returns Useless JSON: {str(e)}")
        raise HTTPException(status_code=500, detail="OCR Service Returns Useless JSON")
    except Exception as e:
        logger.error(f"File Processing Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File Processing Error: {str(e)}")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}