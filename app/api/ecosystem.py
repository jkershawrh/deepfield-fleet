"""Published schemas for DeepField-owned ecosystem events."""

from fastapi import APIRouter, HTTPException

from app.contracts.events_v1 import CONTRACT_MODELS_V1

router = APIRouter(
    prefix="/api/v1/ecosystem/contracts",
    tags=["ecosystem-contracts"],
)


@router.get("/schemas")
async def list_contract_schemas_v1():
    return {
        name: model.model_json_schema(mode="validation")
        for name, model in CONTRACT_MODELS_V1.items()
    }


@router.get("/schemas/{contract_name}")
async def get_contract_schema_v1(contract_name: str):
    model = CONTRACT_MODELS_V1.get(contract_name)
    if model is None:
        raise HTTPException(status_code=404, detail="Unknown DeepField v1 contract")
    return model.model_json_schema(mode="validation")
