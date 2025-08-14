"""
Insurance Agents

This module provides domain-specific insurance agents for different types of insurance:
- Auto Insurance Agent
- Life Insurance Agent  
- Health Insurance Agent
- Dental Insurance Agent
- General Insurance Agent

Each agent is specialized for their respective domain and has access to relevant tools.
"""

import logging
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class InsuranceAgentBase(ABC):
    """
    Base class for insurance agents
    
    All insurance agents inherit from this base class and implement
    domain-specific methods for policy analysis and claims processing.
    """
    
    def __init__(self, domain: str, tools: List[Any]):
        self.domain = domain
        self.tools = tools
        self._initialized = False
        
    async def initialize(self):
        """Initialize the agent"""
        try:
            # Initialize tools
            for tool in self.tools:
                if hasattr(tool, 'initialize'):
                    await tool.initialize()
            
            self._initialized = True
            logger.info(f"Initialized {self.domain} insurance agent")
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.domain} insurance agent: {e}")
            raise
    
    @abstractmethod
    async def analyze_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze insurance policy"""
        pass
    
    @abstractmethod
    async def process_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process insurance claim"""
        pass
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "domain": self.domain,
            "tools_count": len(self.tools),
            "initialized": self._initialized,
            "agent_type": self.__class__.__name__
        }

class AutoInsuranceAgent(InsuranceAgentBase):
    """Auto insurance agent specialized for vehicle insurance"""
    
    def __init__(self, tools: List[Any]):
        super().__init__("auto", tools)
    
    async def analyze_auto_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze auto insurance policy"""
        try:
            # Extract auto-specific data
            vehicle_info = policy_data.get("vehicle_info", {})
            coverage = policy_data.get("coverage", {})
            
            analysis = {
                "domain": "auto",
                "analysis_type": "auto_policy",
                "vehicle_info": vehicle_info,
                "coverage_analysis": {
                    "liability": coverage.get("liability", {}),
                    "collision": coverage.get("collision", {}),
                    "comprehensive": coverage.get("comprehensive", {}),
                    "uninsured_motorist": coverage.get("uninsured_motorist", {})
                },
                "recommendations": []
            }
            
            # Add domain-specific analysis
            if vehicle_info.get("year", 0) < 2010:
                analysis["recommendations"].append("Consider comprehensive coverage for older vehicle")
            
            if coverage.get("liability", {}).get("limit", 0) < 50000:
                analysis["recommendations"].append("Consider increasing liability limits")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Auto policy analysis failed: {e}")
            return {"error": str(e), "domain": "auto"}
    
    async def process_auto_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process auto insurance claim"""
        try:
            # Extract auto-specific claim data
            accident_details = claim_data.get("accident_details", {})
            damage_estimate = claim_data.get("damage_estimate", 0)
            
            processing = {
                "domain": "auto",
                "processing_type": "auto_claim",
                "accident_details": accident_details,
                "damage_estimate": damage_estimate,
                "processing_steps": [
                    "Validate claim information",
                    "Assess damage",
                    "Determine liability",
                    "Calculate settlement"
                ],
                "status": "processing"
            }
            
            # Add domain-specific processing logic
            if accident_details.get("fault") == "other_party":
                processing["status"] = "pending_third_party"
            elif damage_estimate > 5000:
                processing["status"] = "requires_investigation"
            
            return processing
            
        except Exception as e:
            logger.error(f"Auto claim processing failed: {e}")
            return {"error": str(e), "domain": "auto"}
    
    async def analyze_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze auto insurance policy (alias for analyze_auto_policy)"""
        return await self.analyze_auto_policy(policy_data)
    
    async def process_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process auto insurance claim (alias for process_auto_claim)"""
        return await self.process_auto_claim(claim_data)

class LifeInsuranceAgent(InsuranceAgentBase):
    """Life insurance agent specialized for life insurance policies"""
    
    def __init__(self, tools: List[Any]):
        super().__init__("life", tools)
    
    async def analyze_life_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze life insurance policy"""
        try:
            # Extract life-specific data
            insured_info = policy_data.get("insured_info", {})
            coverage = policy_data.get("coverage", {})
            
            analysis = {
                "domain": "life",
                "analysis_type": "life_policy",
                "insured_info": insured_info,
                "coverage_analysis": {
                    "death_benefit": coverage.get("death_benefit", 0),
                    "policy_type": coverage.get("policy_type", "term"),
                    "premium": coverage.get("premium", 0),
                    "term_length": coverage.get("term_length", 0)
                },
                "recommendations": []
            }
            
            # Add domain-specific analysis
            age = insured_info.get("age", 0)
            death_benefit = coverage.get("death_benefit", 0)
            
            if age > 50 and death_benefit < 100000:
                analysis["recommendations"].append("Consider increasing death benefit for older insured")
            
            if coverage.get("policy_type") == "term" and age < 40:
                analysis["recommendations"].append("Consider permanent life insurance for younger insured")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Life policy analysis failed: {e}")
            return {"error": str(e), "domain": "life"}
    
    async def process_life_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process life insurance claim"""
        try:
            # Extract life-specific claim data
            beneficiary_info = claim_data.get("beneficiary_info", {})
            death_certificate = claim_data.get("death_certificate", {})
            
            processing = {
                "domain": "life",
                "processing_type": "life_claim",
                "beneficiary_info": beneficiary_info,
                "death_certificate": death_certificate,
                "processing_steps": [
                    "Validate death certificate",
                    "Verify beneficiary information",
                    "Calculate death benefit",
                    "Process payment"
                ],
                "status": "processing"
            }
            
            # Add domain-specific processing logic
            if not death_certificate.get("verified"):
                processing["status"] = "pending_verification"
            elif not beneficiary_info.get("contacted"):
                processing["status"] = "pending_beneficiary_contact"
            
            return processing
            
        except Exception as e:
            logger.error(f"Life claim processing failed: {e}")
            return {"error": str(e), "domain": "life"}
    
    async def analyze_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze life insurance policy (alias for analyze_life_policy)"""
        return await self.analyze_life_policy(policy_data)
    
    async def process_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process life insurance claim (alias for process_life_claim)"""
        return await self.process_life_claim(claim_data)

class HealthInsuranceAgent(InsuranceAgentBase):
    """Health insurance agent specialized for health insurance policies"""
    
    def __init__(self, tools: List[Any]):
        super().__init__("health", tools)
    
    async def analyze_health_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze health insurance policy"""
        try:
            # Extract health-specific data
            insured_info = policy_data.get("insured_info", {})
            coverage = policy_data.get("coverage", {})
            
            analysis = {
                "domain": "health",
                "analysis_type": "health_policy",
                "insured_info": insured_info,
                "coverage_analysis": {
                    "deductible": coverage.get("deductible", 0),
                    "copay": coverage.get("copay", {}),
                    "prescription_coverage": coverage.get("prescription_coverage", {}),
                    "network_type": coverage.get("network_type", "ppo")
                },
                "recommendations": []
            }
            
            # Add domain-specific analysis
            deductible = coverage.get("deductible", 0)
            family_size = insured_info.get("family_size", 1)
            
            if deductible > 5000 and family_size > 1:
                analysis["recommendations"].append("Consider lower deductible for family coverage")
            
            if not coverage.get("prescription_coverage"):
                analysis["recommendations"].append("Consider adding prescription coverage")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Health policy analysis failed: {e}")
            return {"error": str(e), "domain": "health"}
    
    async def process_health_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process health insurance claim"""
        try:
            # Extract health-specific claim data
            medical_procedure = claim_data.get("medical_procedure", {})
            provider_info = claim_data.get("provider_info", {})
            
            processing = {
                "domain": "health",
                "processing_type": "health_claim",
                "medical_procedure": medical_procedure,
                "provider_info": provider_info,
                "processing_steps": [
                    "Verify provider network",
                    "Check coverage eligibility",
                    "Calculate patient responsibility",
                    "Process claim payment"
                ],
                "status": "processing"
            }
            
            # Add domain-specific processing logic
            if not provider_info.get("in_network"):
                processing["status"] = "out_of_network_review"
            elif medical_procedure.get("requires_preauth") and not medical_procedure.get("preauth_approved"):
                processing["status"] = "pending_preauthorization"
            
            return processing
            
        except Exception as e:
            logger.error(f"Health claim processing failed: {e}")
            return {"error": str(e), "domain": "health"}
    
    async def analyze_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze health insurance policy (alias for analyze_health_policy)"""
        return await self.analyze_health_policy(policy_data)
    
    async def process_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process health insurance claim (alias for process_health_claim)"""
        return await self.process_health_claim(claim_data)

class DentalInsuranceAgent(InsuranceAgentBase):
    """Dental insurance agent specialized for dental insurance policies"""
    
    def __init__(self, tools: List[Any]):
        super().__init__("dental", tools)
    
    async def analyze_dental_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze dental insurance policy"""
        try:
            # Extract dental-specific data
            insured_info = policy_data.get("insured_info", {})
            coverage = policy_data.get("coverage", {})
            
            analysis = {
                "domain": "dental",
                "analysis_type": "dental_policy",
                "insured_info": insured_info,
                "coverage_analysis": {
                    "annual_maximum": coverage.get("annual_maximum", 0),
                    "deductible": coverage.get("deductible", 0),
                    "preventive_coverage": coverage.get("preventive_coverage", {}),
                    "major_restorative": coverage.get("major_restorative", {})
                },
                "recommendations": []
            }
            
            # Add domain-specific analysis
            annual_max = coverage.get("annual_maximum", 0)
            family_size = insured_info.get("family_size", 1)
            
            if annual_max < 1500 and family_size > 1:
                analysis["recommendations"].append("Consider higher annual maximum for family")
            
            if not coverage.get("preventive_coverage", {}).get("covered"):
                analysis["recommendations"].append("Ensure preventive care is covered")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Dental policy analysis failed: {e}")
            return {"error": str(e), "domain": "dental"}
    
    async def process_dental_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process dental insurance claim"""
        try:
            # Extract dental-specific claim data
            dental_procedure = claim_data.get("dental_procedure", {})
            provider_info = claim_data.get("provider_info", {})
            
            processing = {
                "domain": "dental",
                "processing_type": "dental_claim",
                "dental_procedure": dental_procedure,
                "provider_info": provider_info,
                "processing_steps": [
                    "Verify provider network",
                    "Check annual maximum",
                    "Calculate coverage percentage",
                    "Process claim payment"
                ],
                "status": "processing"
            }
            
            # Add domain-specific processing logic
            procedure_type = dental_procedure.get("type", "")
            if procedure_type == "major_restorative":
                processing["status"] = "requires_estimate"
            elif procedure_type == "preventive":
                processing["status"] = "standard_processing"
            
            return processing
            
        except Exception as e:
            logger.error(f"Dental claim processing failed: {e}")
            return {"error": str(e), "domain": "dental"}
    
    async def analyze_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze dental insurance policy (alias for analyze_dental_policy)"""
        return await self.analyze_dental_policy(policy_data)
    
    async def process_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process dental insurance claim (alias for process_dental_claim)"""
        return await self.process_dental_claim(claim_data)

class GeneralInsuranceAgent(InsuranceAgentBase):
    """General insurance agent for fallback and general insurance tasks"""
    
    def __init__(self, tools: List[Any]):
        super().__init__("general", tools)
    
    async def analyze_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze insurance policy (general implementation)"""
        try:
            analysis = {
                "domain": "general",
                "analysis_type": "general_policy",
                "policy_data": policy_data,
                "analysis_notes": [
                    "General policy analysis performed",
                    "Review coverage details",
                    "Check policy terms and conditions"
                ],
                "recommendations": [
                    "Consult with insurance specialist for domain-specific advice"
                ]
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"General policy analysis failed: {e}")
            return {"error": str(e), "domain": "general"}
    
    async def process_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process insurance claim (general implementation)"""
        try:
            processing = {
                "domain": "general",
                "processing_type": "general_claim",
                "claim_data": claim_data,
                "processing_steps": [
                    "Review claim information",
                    "Validate documentation",
                    "Assess coverage",
                    "Process claim"
                ],
                "status": "processing",
                "notes": [
                    "General claim processing performed",
                    "Domain-specific processing may be required"
                ]
            }
            
            return processing
            
        except Exception as e:
            logger.error(f"General claim processing failed: {e}")
            return {"error": str(e), "domain": "general"}

def create_insurance_agent(domain: str, tools: List[Any]) -> InsuranceAgentBase:
    """
    Factory function to create domain-specific insurance agents
    
    Args:
        domain: Insurance domain ("auto", "life", "health", "dental", "general")
        tools: List of tools to provide to the agent
        
    Returns:
        Domain-specific insurance agent instance
    """
    domain = domain.lower()
    
    if domain == "auto":
        return AutoInsuranceAgent(tools)
    elif domain == "life":
        return LifeInsuranceAgent(tools)
    elif domain == "health":
        return HealthInsuranceAgent(tools)
    elif domain == "dental":
        return DentalInsuranceAgent(tools)
    elif domain == "general":
        return GeneralInsuranceAgent(tools)
    else:
        logger.warning(f"Unknown domain '{domain}', using general agent")
        return GeneralInsuranceAgent(tools)
