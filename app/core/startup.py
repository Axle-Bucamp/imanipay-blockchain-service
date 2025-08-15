# /imanipay-blockchain-service/app/core/startup.py
from fastapi import FastAPI
from app.core.config import get_settings
from app.api import wallets, transactions # escrow , mobile_money

settings = get_settings()

def create_app() -> FastAPI:
    app = FastAPI(title=settings.project_name)
    app.include_router(wallets.router)    
    print(f"PROJECT_NAME: {settings.project_name}")
    print(f"ALGORAND_NODE_URL: {settings.algorand.algod_address}")
    print(f"ALGORAND_API_KEY: {settings.algorand.algod_token}")

    app.include_router(transactions.router)
    # app.include_router(escrow.router)
    # app.include_router(mobile_money.router)
    return app

app = create_app()