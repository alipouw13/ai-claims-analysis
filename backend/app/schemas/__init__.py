"""
Schemas package for the AI Claims Analysis application.

Contains Pydantic models and schemas for data validation and structure definition.
"""

from .claim_schema import (
    InsuranceClaim,
    ClaimAddress,
    ClaimContact,
    ClaimDamageItem,
    ClaimPayment
)

__all__ = [
    "InsuranceClaim",
    "ClaimAddress", 
    "ClaimContact",
    "ClaimDamageItem",
    "ClaimPayment"
]