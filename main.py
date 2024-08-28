from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
import io
import logging

app = FastAPI()

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

receiptOcrEndpoint = 'https://ocr.asprise.com/api/v1/receipt'

@app.post("/upload/")
async def create_upload_file(uploaded_file: UploadFile = File(...)):
    if not uploaded_file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        raise HTTPException(status_code=415, detail="不支持的文件类型")
    
    try:
        contents = await uploaded_file.read()
        logger.info(f"文件大小: {len(contents)} 字节")

        r = requests.post(receiptOcrEndpoint, data={
            'client_id': 'TEST',
            'recognizer': 'auto',
            'ref_no': 'ocr_python_123',
        }, files={"file": (uploaded_file.filename, io.BytesIO(contents), uploaded_file.content_type)})
        
        logger.info(f"OCR服务响应状态码: {r.status_code}")
        logger.info(f"OCR服务响应内容: {r.text[:200]}...")  # 记录响应的前200个字符

        r.raise_for_status()  # 如果响应状态码不是200，将引发异常
        data = r.json()
        
        item_list = []
        if 'receipts' in data and data['receipts'] and 'items' in data['receipts'][0]:
            items = data['receipts'][0]['items']
            item_list = [item['description'] for item in items]
        
        return {"item_list": item_list}
    except requests.RequestException as e:
        logger.error(f"OCR服务请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR服务请求失败: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"OCR服务返回了无效的JSON: {str(e)}")
        raise HTTPException(status_code=500, detail="OCR服务返回了无效的JSON")
    except Exception as e:
        logger.error(f"处理文件时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理文件时发生错误: {str(e)}")
