import uvicorn
import sys
sys.path.insert(0, '.')
uvicorn.run('src.ui.server:app', host='0.0.0.0', port=8000)
