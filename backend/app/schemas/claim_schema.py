"""
Claims Document Schema for Content Processing Solution Accelerator Pattern

This schema defines the structure for extracting key information from insurance claims documents
following the Microsoft Content Processing Solution Accelerator approach.
"""

from __future__ import annotations
import json
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ClaimAddress(BaseModel):
    """
    A class representing an address in a claim document.
    
    Attributes:
        street: Street address where loss occurred or insured property is located
        city: City name
        state: State or province
        postal_code: ZIP or postal code
        country: Country name
    """
    
    street: Optional[str] = Field(description="Street address, e.g. 123 Main St.")
    city: Optional[str] = Field(description="City name, e.g. Springfield")
    state: Optional[str] = Field(description="State or province, e.g. IL")
    postal_code: Optional[str] = Field(description="ZIP or postal code, e.g. 62701")
    country: Optional[str] = Field(description="Country name, e.g. USA")
    
    @staticmethod
    def example():
        """Creates an empty example ClaimAddress object."""
        return ClaimAddress(street="", city="", state="", postal_code="", country="")
    
    def to_dict(self):
        """Converts the ClaimAddress object to a dictionary."""
        return {
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country
        }


class ClaimContact(BaseModel):
    """
    A class representing contact information in a claim.
    
    Attributes:
        name: Full name of the contact person
        phone: Phone number
        email: Email address
        relationship: Relationship to the claim (e.g., policyholder, adjuster, witness)
    """
    
    name: Optional[str] = Field(description="Full name of the contact person, e.g. John Smith")
    phone: Optional[str] = Field(description="Phone number, e.g. (555) 123-4567")
    email: Optional[str] = Field(description="Email address, e.g. john.smith@email.com")
    relationship: Optional[str] = Field(description="Relationship to claim, e.g. policyholder, adjuster, witness")
    
    @staticmethod
    def example():
        """Creates an empty example ClaimContact object."""
        return ClaimContact(name="", phone="", email="", relationship="")
    
    def to_dict(self):
        """Converts the ClaimContact object to a dictionary."""
        return {
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "relationship": self.relationship
        }


class ClaimDamageItem(BaseModel):
    """
    A class representing a damaged item in a claim.
    
    Attributes:
        item_description: Description of the damaged item
        damage_description: Description of the damage
        estimated_repair_cost: Estimated cost to repair the item
        estimated_replacement_cost: Estimated cost to replace the item
        depreciation: Depreciation amount applied
        actual_cash_value: Actual cash value of the item
        category: Category of the item (e.g., structure, personal property, vehicle)
    """
    
    item_description: Optional[str] = Field(description="Description of the damaged item, e.g. Kitchen cabinets")
    damage_description: Optional[str] = Field(description="Description of the damage, e.g. Water damage from burst pipe")
    estimated_repair_cost: Optional[float] = Field(description="Estimated cost to repair, e.g. 2500.00")
    estimated_replacement_cost: Optional[float] = Field(description="Estimated replacement cost, e.g. 5000.00")
    depreciation: Optional[float] = Field(description="Depreciation amount, e.g. 500.00")
    actual_cash_value: Optional[float] = Field(description="Actual cash value after depreciation, e.g. 4500.00")
    category: Optional[str] = Field(description="Category of item, e.g. structure, personal property, vehicle")
    
    @staticmethod
    def example():
        """Creates an empty example ClaimDamageItem object."""
        return ClaimDamageItem(
            item_description="", damage_description="", estimated_repair_cost=0.0,
            estimated_replacement_cost=0.0, depreciation=0.0, actual_cash_value=0.0, category=""
        )
    
    def to_dict(self):
        """Converts the ClaimDamageItem object to a dictionary."""
        return {
            "item_description": self.item_description,
            "damage_description": self.damage_description,
            "estimated_repair_cost": f"{self.estimated_repair_cost:.2f}" if self.estimated_repair_cost is not None else None,
            "estimated_replacement_cost": f"{self.estimated_replacement_cost:.2f}" if self.estimated_replacement_cost is not None else None,
            "depreciation": f"{self.depreciation:.2f}" if self.depreciation is not None else None,
            "actual_cash_value": f"{self.actual_cash_value:.2f}" if self.actual_cash_value is not None else None,
            "category": self.category
        }


class ClaimPayment(BaseModel):
    """
    A class representing payment information in a claim.
    
    Attributes:
        payment_date: Date the payment was made
        payment_amount: Amount of the payment
        payment_type: Type of payment (e.g., partial, final, advance)
        check_number: Check number if applicable
        payment_method: Method of payment (e.g., check, ACH, wire transfer)
        payee: Who the payment was made to
    """
    
    payment_date: Optional[str] = Field(description="Date payment was made, e.g. 2024-01-15")
    payment_amount: Optional[float] = Field(description="Payment amount, e.g. 15000.00")
    payment_type: Optional[str] = Field(description="Type of payment, e.g. partial, final, advance")
    check_number: Optional[str] = Field(description="Check number if applicable, e.g. 12345")
    payment_method: Optional[str] = Field(description="Payment method, e.g. check, ACH, wire transfer")
    payee: Optional[str] = Field(description="Who payment was made to, e.g. John Smith")
    
    @staticmethod
    def example():
        """Creates an empty example ClaimPayment object."""
        return ClaimPayment(
            payment_date="", payment_amount=0.0, payment_type="",
            check_number="", payment_method="", payee=""
        )
    
    def to_dict(self):
        """Converts the ClaimPayment object to a dictionary."""
        return {
            "payment_date": self.payment_date,
            "payment_amount": f"{self.payment_amount:.2f}" if self.payment_amount is not None else None,
            "payment_type": self.payment_type,
            "check_number": self.check_number,
            "payment_method": self.payment_method,
            "payee": self.payee
        }


class InsuranceClaim(BaseModel):
    """
    A class representing a complete insurance claim document.
    
    This schema defines all the key fields that should be extracted from insurance claim documents
    to replace the current placeholder values with actual extracted data.
    
    Attributes:
        claim_number: Unique claim identifier
        policy_number: Insurance policy number
        insured_name: Name of the insured party
        insured_address: Address of the insured party
        loss_date: Date when the loss occurred
        report_date: Date when the claim was reported
        loss_location: Address where the loss occurred
        loss_description: Detailed description of what happened
        cause_of_loss: Primary cause of the loss (e.g., fire, theft, water damage)
        claim_amount_requested: Amount requested by the insured
        claim_amount_reserved: Amount reserved by the insurance company
        claim_amount_paid: Total amount paid on the claim
        deductible: Policy deductible amount
        coverage_type: Type of coverage (e.g., dwelling, contents, liability)
        adjuster_name: Name of the assigned adjuster
        adjuster_contact: Contact information for the adjuster
        claim_status: Current status of the claim
        damaged_items: List of damaged items with details
        payments: List of payments made on the claim
        contacts: List of relevant contacts
        attachments: List of supporting documents
        investigation_notes: Adjuster or investigator notes
        coverage_decision: Decision on coverage
        settlement_summary: Final settlement details
    """
    
    # Core Claim Information
    claim_number: Optional[str] = Field(description="Unique claim identifier, e.g. CLM-2024-001234")
    policy_number: Optional[str] = Field(description="Insurance policy number, e.g. POL-987654321")
    
    # Insured Information
    insured_name: Optional[str] = Field(description="Name of the insured party, e.g. John and Jane Smith")
    insured_address: Optional[ClaimAddress] = Field(description="Address of the insured party")
    
    # Loss Information
    loss_date: Optional[str] = Field(description="Date when the loss occurred, e.g. 2024-01-10")
    report_date: Optional[str] = Field(description="Date when the claim was reported, e.g. 2024-01-12")
    loss_location: Optional[ClaimAddress] = Field(description="Address where the loss occurred")
    loss_description: Optional[str] = Field(description="Detailed description of what happened")
    cause_of_loss: Optional[str] = Field(description="Primary cause of loss, e.g. fire, theft, water damage, wind")
    
    # Financial Information
    claim_amount_requested: Optional[float] = Field(description="Amount requested by insured, e.g. 25000.00")
    claim_amount_reserved: Optional[float] = Field(description="Amount reserved by insurance company, e.g. 20000.00")
    claim_amount_paid: Optional[float] = Field(description="Total amount paid on claim, e.g. 15000.00")
    deductible: Optional[float] = Field(description="Policy deductible amount, e.g. 1000.00")
    
    # Coverage Information
    coverage_type: Optional[str] = Field(description="Type of coverage, e.g. dwelling, contents, liability, comprehensive")
    policy_limits: Optional[float] = Field(description="Policy coverage limits, e.g. 300000.00")
    
    # Adjuster and Contacts
    adjuster_name: Optional[str] = Field(description="Name of assigned adjuster, e.g. Sarah Johnson")
    adjuster_contact: Optional[ClaimContact] = Field(description="Contact information for the adjuster")
    
    # Claim Processing
    claim_status: Optional[str] = Field(description="Current claim status, e.g. open, closed, pending, denied")
    date_closed: Optional[str] = Field(description="Date claim was closed, e.g. 2024-02-15")
    
    # Detailed Information
    damaged_items: Optional[List[ClaimDamageItem]] = Field(description="List of damaged items with details")
    payments: Optional[List[ClaimPayment]] = Field(description="List of payments made on the claim")
    contacts: Optional[List[ClaimContact]] = Field(description="List of relevant contacts")
    
    # Investigation and Documentation
    investigation_notes: Optional[str] = Field(description="Adjuster or investigator notes and findings")
    coverage_decision: Optional[str] = Field(description="Decision on coverage (covered, denied, partial)")
    denial_reason: Optional[str] = Field(description="Reason for denial if claim was denied")
    settlement_summary: Optional[str] = Field(description="Final settlement details and explanation")
    
    # Supporting Documentation
    attachments: Optional[List[str]] = Field(description="List of supporting documents, e.g. photos, police reports, estimates")
    witness_statements: Optional[List[str]] = Field(description="Witness statements if applicable")
    
    # Additional Metadata
    claim_type: Optional[str] = Field(description="Type of claim, e.g. property, auto, liability, workers compensation")
    urgency_level: Optional[str] = Field(description="Urgency level, e.g. routine, urgent, catastrophic")
    fraud_indicators: Optional[List[str]] = Field(description="Any fraud indicators noted during investigation")
    
    @staticmethod
    def example():
        """Creates an example InsuranceClaim object with sample data."""
        return InsuranceClaim(
            claim_number="CLM-2024-001234",
            policy_number="POL-987654321",
            insured_name="John and Jane Smith",
            insured_address=ClaimAddress.example(),
            loss_date="2024-01-10",
            report_date="2024-01-12",
            loss_location=ClaimAddress.example(),
            loss_description="Water damage due to burst pipe in kitchen",
            cause_of_loss="water damage",
            claim_amount_requested=25000.00,
            claim_amount_reserved=20000.00,
            claim_amount_paid=15000.00,
            deductible=1000.00,
            coverage_type="dwelling",
            policy_limits=300000.00,
            adjuster_name="Sarah Johnson",
            adjuster_contact=ClaimContact.example(),
            claim_status="closed",
            date_closed="2024-02-15",
            damaged_items=[ClaimDamageItem.example()],
            payments=[ClaimPayment.example()],
            contacts=[ClaimContact.example()],
            investigation_notes="",
            coverage_decision="covered",
            settlement_summary="",
            attachments=[],
            witness_statements=[],
            claim_type="property",
            urgency_level="routine",
            fraud_indicators=[]
        )
    
    @staticmethod
    def from_json(json_str: str):
        """Creates an InsuranceClaim object from a JSON string."""
        json_content = json.loads(json_str)
        
        def create_claim_address(address_data):
            """Creates a ClaimAddress object from dictionary data."""
            if address_data is None:
                return None
            return ClaimAddress(
                street=address_data.get("street", None),
                city=address_data.get("city", None),
                state=address_data.get("state", None),
                postal_code=address_data.get("postal_code", None),
                country=address_data.get("country", None)
            )
        
        def create_claim_contact(contact_data):
            """Creates a ClaimContact object from dictionary data."""
            if contact_data is None:
                return None
            return ClaimContact(
                name=contact_data.get("name", None),
                phone=contact_data.get("phone", None),
                email=contact_data.get("email", None),
                relationship=contact_data.get("relationship", None)
            )
        
        def create_damage_item(item_data):
            """Creates a ClaimDamageItem object from dictionary data."""
            if item_data is None:
                return None
            return ClaimDamageItem(
                item_description=item_data.get("item_description", None),
                damage_description=item_data.get("damage_description", None),
                estimated_repair_cost=item_data.get("estimated_repair_cost", None),
                estimated_replacement_cost=item_data.get("estimated_replacement_cost", None),
                depreciation=item_data.get("depreciation", None),
                actual_cash_value=item_data.get("actual_cash_value", None),
                category=item_data.get("category", None)
            )
        
        def create_payment(payment_data):
            """Creates a ClaimPayment object from dictionary data."""
            if payment_data is None:
                return None
            return ClaimPayment(
                payment_date=payment_data.get("payment_date", None),
                payment_amount=payment_data.get("payment_amount", None),
                payment_type=payment_data.get("payment_type", None),
                check_number=payment_data.get("check_number", None),
                payment_method=payment_data.get("payment_method", None),
                payee=payment_data.get("payee", None)
            )
        
        # Convert lists
        damaged_items = [
            create_damage_item(item) for item in json_content.get("damaged_items", [])
        ]
        payments = [
            create_payment(payment) for payment in json_content.get("payments", [])
        ]
        contacts = [
            create_claim_contact(contact) for contact in json_content.get("contacts", [])
        ]
        
        return InsuranceClaim(
            claim_number=json_content.get("claim_number", None),
            policy_number=json_content.get("policy_number", None),
            insured_name=json_content.get("insured_name", None),
            insured_address=create_claim_address(json_content.get("insured_address", None)),
            loss_date=json_content.get("loss_date", None),
            report_date=json_content.get("report_date", None),
            loss_location=create_claim_address(json_content.get("loss_location", None)),
            loss_description=json_content.get("loss_description", None),
            cause_of_loss=json_content.get("cause_of_loss", None),
            claim_amount_requested=json_content.get("claim_amount_requested", None),
            claim_amount_reserved=json_content.get("claim_amount_reserved", None),
            claim_amount_paid=json_content.get("claim_amount_paid", None),
            deductible=json_content.get("deductible", None),
            coverage_type=json_content.get("coverage_type", None),
            policy_limits=json_content.get("policy_limits", None),
            adjuster_name=json_content.get("adjuster_name", None),
            adjuster_contact=create_claim_contact(json_content.get("adjuster_contact", None)),
            claim_status=json_content.get("claim_status", None),
            date_closed=json_content.get("date_closed", None),
            damaged_items=damaged_items,
            payments=payments,
            contacts=contacts,
            investigation_notes=json_content.get("investigation_notes", None),
            coverage_decision=json_content.get("coverage_decision", None),
            denial_reason=json_content.get("denial_reason", None),
            settlement_summary=json_content.get("settlement_summary", None),
            attachments=json_content.get("attachments", []),
            witness_statements=json_content.get("witness_statements", []),
            claim_type=json_content.get("claim_type", None),
            urgency_level=json_content.get("urgency_level", None),
            fraud_indicators=json_content.get("fraud_indicators", [])
        )
    
    def to_dict(self):
        """Converts the InsuranceClaim object to a dictionary."""
        return {
            "claim_number": self.claim_number,
            "policy_number": self.policy_number,
            "insured_name": self.insured_name,
            "insured_address": self.insured_address.to_dict() if self.insured_address else None,
            "loss_date": self.loss_date,
            "report_date": self.report_date,
            "loss_location": self.loss_location.to_dict() if self.loss_location else None,
            "loss_description": self.loss_description,
            "cause_of_loss": self.cause_of_loss,
            "claim_amount_requested": f"{self.claim_amount_requested:.2f}" if self.claim_amount_requested is not None else None,
            "claim_amount_reserved": f"{self.claim_amount_reserved:.2f}" if self.claim_amount_reserved is not None else None,
            "claim_amount_paid": f"{self.claim_amount_paid:.2f}" if self.claim_amount_paid is not None else None,
            "deductible": f"{self.deductible:.2f}" if self.deductible is not None else None,
            "coverage_type": self.coverage_type,
            "policy_limits": f"{self.policy_limits:.2f}" if self.policy_limits is not None else None,
            "adjuster_name": self.adjuster_name,
            "adjuster_contact": self.adjuster_contact.to_dict() if self.adjuster_contact else None,
            "claim_status": self.claim_status,
            "date_closed": self.date_closed,
            "damaged_items": [item.to_dict() for item in self.damaged_items] if self.damaged_items else [],
            "payments": [payment.to_dict() for payment in self.payments] if self.payments else [],
            "contacts": [contact.to_dict() for contact in self.contacts] if self.contacts else [],
            "investigation_notes": self.investigation_notes,
            "coverage_decision": self.coverage_decision,
            "denial_reason": self.denial_reason,
            "settlement_summary": self.settlement_summary,
            "attachments": self.attachments or [],
            "witness_statements": self.witness_statements or [],
            "claim_type": self.claim_type,
            "urgency_level": self.urgency_level,
            "fraud_indicators": self.fraud_indicators or []
        }