#!/bin/bash

# 1. git pull
git pull

# 2. cd backend && pip install
cd backend && pip install -r requirements.txt --break-system-packages

# 3. kill any existing process on port 8000
kill -9 $(lsof -t -i:8000) 2>/dev/null || true

# 4. start uvicorn in the background, logging to backend.log
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
