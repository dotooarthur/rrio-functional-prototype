# RRIO Functional Prototype

This repository contains a functional prototype of **RRIO: Rapid Response Instruction Optimizer**.

## Purpose
This prototype demonstrates how RRIO can move from classroom assessment evidence to a grounded, reviewable next-day instructional response.

## What the prototype shows
- Uploading classroom assessment data
- Computing summary cards
- Identifying a likely skill gap or misconception focus
- Grouping students for instructional support
- Generating a next-day lesson draft
- Showing materials and export options
- Supporting teacher review and approval

## Files
- `rrio_demo_enhanced_v2.py` – main Streamlit app
- `rrio_demo_sample_v2.csv` – sample input file
- `requirements.txt` – Python dependencies

## Run locally
```bash
pip install -r requirements.txt
streamlit run rrio_demo_enhanced_v2.py
