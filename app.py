from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, Response
import markdown
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json, yaml
import os
import uvicorn
from datetime import datetime
from xml.etree import ElementTree as ET
from sqlalchemy.orm import Session
from database import get_db, ScaleResult
import geoip2.database
from datetime import datetime, UTC
import csv
from io import StringIO
from typing import Dict, List

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize GeoIP2 reader
try:
    geoip_reader = geoip2.database.Reader('GeoLite2-City.mmdb')
except FileNotFoundError:
    print("Warning: GeoLite2-City.mmdb not found. IP location lookup will be disabled.")
    geoip_reader = None

def get_location_from_ip(ip):
    if not geoip_reader:
        return None
    try:
        response = geoip_reader.city(ip)
        return {
            'country': response.country.name,
            'city': response.city.name,
            'latitude': response.location.latitude,
            'longitude': response.location.longitude
        }
    except Exception as e:
        print(f"Error getting location for IP {ip}: {e}")
        return None

# 加载所有问卷数据
def load_all_scales():
    scales = {}
    tags = []
    for root, dirs, files in os.walk(os.path.realpath('scales')):
        for filename in files:
            if filename.endswith(('.yaml', '.yml')):
                try:
                    with open(os.path.join(root, filename), 'r', encoding='utf-8') as f:
                        scale = yaml.safe_load(f)
                        scale['instructions']=markdown.markdown(scale['instructions'], extensions=['fenced_code','tables','mdx_math'])
                        scale['descriptions']=markdown.markdown(scale['descriptions'], extensions=['fenced_code','tables','mdx_math'])
                        scale['abstract']=markdown.markdown(scale['abstract'], extensions=['fenced_code','tables','mdx_math'])
                        if 'tag' not in scale:
                            scale['tag']='其他'
                        if scale['tag'] not in tags:
                            tags.append(scale['tag'])
                        scale_id = os.path.splitext(filename)[0] # 使用文件名作为标识
                        scales[scale_id] = scale
                except Exception as e:
                    print(f"Error loading scale {filename}: {e}")
    return tags, scales

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    tags, _ = load_all_scales()
    # 新增读取README.md的逻辑
    readme_content = ""
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            readme_content = markdown.markdown(f.read())
    except FileNotFoundError:
        pass  # 如果README不存在则静默失败
    return templates.TemplateResponse("index.html", {
        "request": request,
        "tags": tags,
        "readme_content": readme_content  # 新增模板变量
    })

@app.get("/tag/{tag}", response_class=HTMLResponse)
async def list(request: Request, tag: str):
    tags, scales = load_all_scales()
    return templates.TemplateResponse("list.html", {
        "request": request,
        "tags": tags,
        "scales": scales,
        "tag": tag
    })  

@app.get("/scales/{scale_id}", response_class=HTMLResponse)
async def scale(request: Request, scale_id: str):
    tags, scales = load_all_scales()
    scale = scales.get(scale_id)
    if scale:
        return templates.TemplateResponse("scale.html", {
            "request": request,
            "scale_id": scale_id,
            "scale": scale,
            "tags":tags
        })
    raise HTTPException(status_code=404, detail="问卷未找到")

@app.post("/scales/{scale_id}", response_class=HTMLResponse)
async def result(request: Request, scale_id: str, db: Session = Depends(get_db)):
    form_data = await request.form()
    tags, scales = load_all_scales()
    scale = scales.get(scale_id)
    if scale:
        responses = {}
        average = {}
        options = {}
        for subscale, qids in scale['subscales'].items():
            responses[subscale] = 0
            min_val = min(scale['options'].keys())
            max_val = max(scale['options'].keys())
            options[subscale] = [min_val*len(qids),max_val*len(qids)]
            for qid in qids:
                if qid<0:
                    responses[subscale] += min_val + max_val - int(form_data[str(-qid)])
                else:
                    responses[subscale] += int(form_data[str(qid)])
            average[subscale] = round(responses[subscale]/len(qids),2)
        try:
            # Save response to database
            ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or \
                request.headers.get("X-Real-IP", "") or \
                request.client.host # Get real IP address considering proxy headers
            location = get_location_from_ip(ip)# Get location information
            db_response = ScaleResult(
                scale_id=scale_id,
                user_agent=request.headers.get("user-agent", "Unknown"),
                ip_address=ip,
                location=location,
                raw_response=dict(form_data),
                sum_response=responses,
                avg_response=average,
                created_at=datetime.now(UTC)
            )
            db.add(db_response)
            db.commit()
        except Exception as e:
            print(e)
        return templates.TemplateResponse("result.html", {
            "request": request,
            "responses": responses,
            "average": average,
            "options": options,
            "scale": scale,
            "tags":tags
        })
    raise HTTPException(status_code=404, detail="问卷未找到")

@app.get("/download/{scale_id}")
async def download_scale_results(scale_id: str, db: Session = Depends(get_db)):
    
    if scale_id == "psychoscales.db":
        public_path = os.path.join("psychoscales.db")
        if os.path.isfile(public_path):
            return FileResponse(public_path)
        raise HTTPException(status_code=404, detail="File not found")

    # Get all responses for this scale
    responses = db.query(ScaleResult).filter(ScaleResult.scale_id == scale_id).all()
    
    if not responses:
        raise HTTPException(status_code=404, detail="No responses found for this scale")
    
    # Load scale definition to get question IDs
    _, scales = load_all_scales()
    scale = scales.get(scale_id)
    if not scale:
        raise HTTPException(status_code=404, detail="Scale not found")
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    headers = [
        "id", "created_at", "ip_address", "user_agent",
        "country", "city", "latitude", "longitude"
    ]
    
    # Add question IDs as headers
    question_ids = []
    for qid in scale['items'].keys():
        question_ids.append(str(qid))
    headers.extend(question_ids)
    
    # Add subscale scores
    for subscale in scale['subscales'].keys():
        headers.extend([f"{subscale}_sum", f"{subscale}_avg"])
    
    writer.writerow(headers)
    
    # Write data rows
    for response in responses:
        row = [
            response.id,
            response.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            response.ip_address,
            response.user_agent,
            response.location.get('country', '') if response.location else '',
            response.location.get('city', '') if response.location else '',
            response.location.get('latitude', '') if response.location else '',
            response.location.get('longitude', '') if response.location else ''
        ]
        
        # Add raw responses
        raw_responses = response.raw_response
        for qid in question_ids:
            row.append(raw_responses.get(qid, ''))
        
        # Add subscale scores
        for subscale in scale['subscales'].keys():
            row.extend([
                response.sum_response.get(subscale, ''),
                response.avg_response.get(subscale, '')
            ])
        
        writer.writerow(row)
    
    # Prepare response
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{scale_id}_responses.csv"'
        }
    )

def generate_sitemap():
    # Create the root element
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    
    latest_mtime = max(
        os.path.getmtime(os.path.join(root, f))
        for root, _, files in os.walk('scales')
        for f in files if f.endswith(('.yaml', '.yml'))
    )

    # Add static routes
    static_routes = ["/"]  # Add your static routes here
    for route in static_routes:
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = f"https://www.psychoscales.org{route}"
        ET.SubElement(url, "lastmod").text = datetime.fromtimestamp(latest_mtime).strftime("%Y-%m-%d")
        ET.SubElement(url, "changefreq").text = "monthly"
        ET.SubElement(url, "priority").text = "0.8"
    
    # Add dynamic tag routes
    tags, scales = load_all_scales()
    for tag in tags:
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = f"https://www.psychoscales.org/tag/{tag}"
        ET.SubElement(url, "lastmod").text = datetime.fromtimestamp(latest_mtime).strftime("%Y-%m-%d")
        ET.SubElement(url, "changefreq").text = "weekly"
        ET.SubElement(url, "priority").text = "0.6"

    # Add dynamic scale routes
    for scale_id in scales.keys():
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = f"https://www.psychoscales.org/scales/{scale_id}"
        # For individual scale pages, use the actual file modification time
        scale_file = os.path.join('scales', f"{scale_id}.yaml")
        if os.path.exists(scale_file):
            mtime = os.path.getmtime(scale_file)
            ET.SubElement(url, "lastmod").text = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        ET.SubElement(url, "changefreq").text = "monthly"
        ET.SubElement(url, "priority").text = "0.6"
    
    # Convert to string
    return ET.tostring(urlset, encoding='unicode', method='xml')

# Mount all files from public directory to root
@app.get("/{filename}")
async def get_public_file(filename: str):
    if filename == "sitemap.xml":
        return Response(
        content=generate_sitemap(),
        media_type="application/xml"
    )
    public_path = os.path.join("public", filename)
    if os.path.isfile(public_path):
        return FileResponse(public_path)
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == '__main__':
   uvicorn.run(app,host='0.0.0.0',port=8000)