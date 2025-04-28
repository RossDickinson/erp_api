# import sys # Can remove this line
import os
from fastapi import FastAPI, Depends, HTTPException, Query, Path
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from typing import List, Dict, Optional
from dotenv import load_dotenv
from datetime import datetime

# # Can remove these debug print lines
# print("--- Python Executable ---")
# print(sys.executable)
# print("--- sys.path ---")
# print(sys.path)
# print("-------------------------")

# Load environment variables
load_dotenv()

# Database configuration from environment
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_SSL = os.getenv("DB_SSL", "require")

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Construct database URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create database engine with SSL
engine = create_engine(
    DATABASE_URL, 
    connect_args={"sslmode": DB_SSL},
    echo=True  # Add this to see SQL queries in logs
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Updated StockLevel model to match the database table
class StockLevel(Base):
    __tablename__ = "stock_levels"  # Changed back to plural
    __table_args__ = {"schema": "inventory"}  # Add schema name
    
    stock_level_id = Column(Integer, primary_key=True)
    product_id = Column(Integer)
    sku = Column(String, unique=True, index=True)
    quantity = Column(Integer)
    warehouse_location = Column(String(100))
    last_updated = Column(DateTime, default=datetime.utcnow)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="Product API")

# Root endpoint
@app.get("/", 
    summary="API Status",
    description="Returns a simple message indicating the API is running."
)
def root():
    return {"message": "Product API is running"}

# Database test endpoint
@app.get("/api/db-test", 
    summary="Test Database Connection",
    description="Tests the connection to the database and returns a list of tables in the public schema."
)
def test_db_connection(db: Session = Depends(get_db)):
    # Try to execute a simple query
    result = db.execute(text("SELECT 1 AS test")).scalar()
    # Get list of tables in the database
    tables = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()
    return {
        "connection": "success" if result == 1 else "failed",
        "tables": [table[0] for table in tables]
    }

# Get all products endpoint
@app.get("/api/products/all", 
    summary="Get All Products",
    description="Returns a list of all products in the database (limited to 10 items)."
)
def get_all_products(db: Session = Depends(get_db)):
    """Get all products in the database (limited to 10)"""
    stock_items = db.query(StockLevel).limit(10).all()
    
    if not stock_items:
        return {"message": "No products found in database"}
    
    result = []
    for item in stock_items:
        result.append({
            "stock_level_id": item.stock_level_id,
            "product_id": item.product_id,
            "sku": item.sku,
            "quantity": item.quantity,
            "warehouse_location": item.warehouse_location,
            "last_updated": str(item.last_updated)
        })
    
    return {"products": result}

# Batch stock quantity query endpoint
@app.get("/api/products/batch/stock", 
    summary="Batch Stock Query",
    description="Returns stock quantities for multiple SKUs in a single request. SKUs should be provided as a comma-separated list."
)
def get_batch_stock_levels(
    skus: str = Query(..., description="Comma-separated list of SKUs (e.g., 'ALPHA-WDG-001,BASIC-WDG-002')"),
    db: Session = Depends(get_db)
):
    sku_list = sorted(skus.split(','))
    
    result = {}
    for sku in sku_list:
        stock_item = db.query(StockLevel).filter(StockLevel.sku == sku).first()
        if stock_item:
            result[sku] = {"quantity": stock_item.quantity}
        else:
            result[sku] = {"error": "Product not found"}
    return result

# Stock level endpoint
@app.get("/api/products/{sku}/stock", 
    summary="Get Product Stock Level",
    description="Returns the current stock quantity for a specific product SKU."
)
def get_stock_quantity(
    sku: str = Path(..., description="The SKU of the product to query"),
    db: Session = Depends(get_db)
):
    stock_item = db.query(StockLevel).filter(StockLevel.sku == sku).first()
    if not stock_item:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"sku": sku, "quantity": stock_item.quantity}

# Warehouse locations endpoint
@app.get("/api/products/{sku}/locations", 
    summary="Get Product Warehouse Locations",
    description="Returns the warehouse location(s) where a specific product SKU is stored."
)
def get_warehouse_locations(
    sku: str = Path(..., description="The SKU of the product to query"),
    db: Session = Depends(get_db)
):
    stock_items = db.query(StockLevel).filter(StockLevel.sku == sku).all()
    if not stock_items:
        raise HTTPException(status_code=404, detail="Product not found")
    
    locations = [item.warehouse_location for item in stock_items]
    return {"sku": sku, "locations": locations}

# Database inspection endpoint
@app.get("/api/db-inspect", 
    summary="Inspect Database",
    description="Advanced endpoint that inspects the database structure and returns details about tables, columns, and sample data."
)
def inspect_db(db: Session = Depends(get_db)):
    # Get list of tables in the inventory schema
    tables = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='inventory'")).fetchall()
    table_names = [table[0] for table in tables]
    
    # Check if our table exists
    if "stock_levels" in table_names:
        # Get column names
        columns = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='stock_levels' AND table_schema='inventory'")).fetchall()
        column_names = [col[0] for col in columns]
        
        # Get sample data (first 5 rows)
        sample_data = []
        try:
            rows = db.execute(text("SELECT * FROM inventory.stock_levels LIMIT 5")).fetchall()
            for row in rows:
                row_dict = {}
                for i, col in enumerate(row):
                    if i < len(column_names):
                        row_dict[column_names[i]] = str(col)  # Convert all values to string for JSON
                sample_data.append(row_dict)
        except Exception as e:
            return {"error": str(e)}
            
        return {
            "tables": table_names,
            "stock_levels_columns": column_names,
            "sample_data": sample_data
        }
    else:
        # If our table doesn't exist, check other tables for SKU data
        sku_tables = []
        for table in table_names:
            try:
                # Check if this table has a column named 'sku'
                has_sku = db.execute(
                    text(f"SELECT COUNT(*) FROM information_schema.columns WHERE table_name='{table}' AND table_schema='inventory' AND column_name='sku'")
                ).scalar()
                if has_sku:
                    sku_tables.append(table)
            except:
                pass
                
        return {
            "tables": table_names,
            "tables_with_sku_column": sku_tables
        }