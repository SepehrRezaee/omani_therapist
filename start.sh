#!/bin/bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
cd frontend && streamlit run app.py --server.port 8501 --server.address 0.0.0.0
