from pydantic import BaseModel, ConfigDict, Field


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    name: str
    price_paise: int
    stock: int


class OrderCreate(BaseModel): 
    product_id: int
    quantity: int = Field(gt=0,le=10)

class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    quantity: int
    total_paise: int
    status: str    
    