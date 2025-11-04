"""
Enhanced metadata extractor for insurance documents.
Provides rich metadata extraction for both policy and claims documents.
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class PolicyMetadata:
    """Metadata structure for insurance policy documents."""
    policy_number: Optional[str] = None
    insured_name: Optional[str] = None
    insurance_company: Optional[str] = None
    line_of_business: Optional[str] = None
    state: Optional[str] = None
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    deductible: Optional[str] = None
    coverage_limits: Optional[Dict[str, str]] = field(default_factory=dict)
    coverage_types: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    endorsements: List[str] = field(default_factory=list)
    agent_name: Optional[str] = None
    premium_amount: Optional[str] = None
    property_address: Optional[str] = None
    vehicle_info: Optional[str] = None
    filename: str = ""
    section_type: str = "general"
    content_complexity: str = "medium"
    contains_monetary_values: bool = False


@dataclass
class ClaimMetadata:
    """Metadata structure for insurance claim documents."""
    claim_id: Optional[str] = None
    policy_number: Optional[str] = None
    insured_name: Optional[str] = None
    insurance_company: Optional[str] = None
    date_of_loss: Optional[str] = None
    reported_date: Optional[str] = None
    loss_cause: Optional[str] = None
    location: Optional[str] = None
    coverage_decision: Optional[str] = None
    settlement_summary: Optional[str] = None
    payout_amount: Optional[str] = None
    adjuster_name: Optional[str] = None
    claim_status: Optional[str] = None
    adjuster_notes: List[str] = field(default_factory=list)
    property_damage: Optional[str] = None
    injury_details: Optional[str] = None
    filename: str = ""
    section_type: str = "general"
    content_complexity: str = "medium"
    contains_monetary_values: bool = False


class InsuranceMetadataExtractor:
    """Enhanced metadata extractor for insurance documents with rich pattern matching."""
    
    def __init__(self):
        self.policy_patterns = self._initialize_policy_patterns()
        self.claim_patterns = self._initialize_claim_patterns()
        self.common_patterns = self._initialize_common_patterns()
    
    def _initialize_policy_patterns(self) -> Dict[str, List[str]]:
        """Initialize regex patterns for policy metadata extraction."""
        return {
            'policy_number': [
                r'policy\s*(?:number|no\.?|#)\s*:?\s*([A-Z0-9-]+)',
                r'policy\s*([A-Z]{2,4}-\d{4,}-\d{6,})',
                r'(?:pol|policy)\s*#?\s*([A-Z0-9]{8,})',
            ],
            'insured_name': [
                r'insured\s*:?\s*([A-Za-z\s,\.]+?)(?:\n|$)',
                r'named\s*insured\s*:?\s*([A-Za-z\s,\.]+?)(?:\n|$)',
                r'policyholder\s*:?\s*([A-Za-z\s,\.]+?)(?:\n|$)',
            ],
            'effective_date': [
                r'effective\s*(?:date)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'policy\s*period\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'from\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            ],
            'expiration_date': [
                r'expir(?:ation|es?)\s*(?:date)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'to\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'expires?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            ],
            'deductible': [
                r'deductible\s*:?\s*\$?([\d,]+)',
                r'ded\.?\s*:?\s*\$?([\d,]+)',
            ],
            'premium_amount': [
                r'premium\s*:?\s*\$?([\d,]+\.?\d*)',
                r'annual\s*premium\s*:?\s*\$?([\d,]+\.?\d*)',
                r'total\s*premium\s*:?\s*\$?([\d,]+\.?\d*)',
            ],
            'agent_name': [
                r'agent\s*:?\s*([A-Za-z\s,\.]+?)(?:\n|agency)',
                r'producer\s*:?\s*([A-Za-z\s,\.]+?)(?:\n|$)',
            ],
            'property_address': [
                r'property\s*address\s*:?\s*([^;\n]+)',
                r'location\s*:?\s*([^;\n]+)',
                r'premises\s*:?\s*([^;\n]+)',
            ],
        }
    
    def _initialize_claim_patterns(self) -> Dict[str, List[str]]:
        """Initialize regex patterns for claim metadata extraction."""
        return {
            'claim_id': [
                r'claim\s*(?:number|no\.?|#)\s*:?\s*([A-Z0-9-]+)',
                r'claim\s*([A-Z]{3,4}-\d{4,}-\d{6,})',
                r'file\s*(?:number|no\.?|#)\s*:?\s*([A-Z0-9-]+)',
            ],
            'date_of_loss': [
                r'date\s*of\s*loss\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'loss\s*date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'incident\s*date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            ],
            'reported_date': [
                r'reported\s*(?:date)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'report\s*date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'notice\s*date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            ],
            'loss_cause': [
                r'cause\s*of\s*loss\s*:?\s*([^;\n]+)',
                r'loss\s*cause\s*:?\s*([^;\n]+)',
                r'peril\s*:?\s*([^;\n]+)',
            ],
            'coverage_decision': [
                r'coverage\s*(?:decision|determination)\s*:?\s*([^;\n]+)',
                r'decision\s*:?\s*(covered|denied|pending|investigating)',
                r'status\s*:?\s*(covered|denied|pending|investigating)',
            ],
            'payout_amount': [
                r'settlement\s*(?:amount)?\s*:?\s*\$?([\d,]+\.?\d*)',
                r'payout\s*:?\s*\$?([\d,]+\.?\d*)',
                r'payment\s*:?\s*\$?([\d,]+\.?\d*)',
            ],
            'adjuster_name': [
                r'adjuster\s*:?\s*([A-Za-z\s,\.]+?)(?:\n|$)',
                r'examiner\s*:?\s*([A-Za-z\s,\.]+?)(?:\n|$)',
                r'inspector\s*:?\s*([A-Za-z\s,\.]+?)(?:\n|$)',
            ],
            'claim_status': [
                r'status\s*:?\s*(open|closed|pending|investigating|settled)',
                r'claim\s*status\s*:?\s*(open|closed|pending|investigating|settled)',
            ],
        }
    
    def _initialize_common_patterns(self) -> Dict[str, List[str]]:
        """Initialize common patterns used by both policies and claims."""
        return {
            'insurance_company': [
                r'(?:insurance\s*)?company\s*:?\s*([A-Za-z\s&,\.]+?)(?:\n|insurance)',
                r'carrier\s*:?\s*([A-Za-z\s&,\.]+?)(?:\n|$)',
                r'insurer\s*:?\s*([A-Za-z\s&,\.]+?)(?:\n|$)',
            ],
            'state': [
                r'\b([A-Z]{2})\s+\d{5}',  # State code in address
                r'state\s*:?\s*([A-Z]{2})',
                r',\s*([A-Z]{2})\s*\d',
            ],
            'location': [
                r'location\s*:?\s*([^;\n]+)',
                r'address\s*:?\s*([^;\n]+)',
                r'premises\s*:?\s*([^;\n]+)',
            ],
        }
    
    def extract_policy_metadata(self, content: str, filename: str = "") -> PolicyMetadata:
        """Extract comprehensive metadata from policy document content."""
        metadata = PolicyMetadata(filename=filename)
        content_lower = content.lower()
        
        # Extract basic policy information
        metadata.policy_number = self._extract_with_patterns(content, self.policy_patterns['policy_number'])
        metadata.insured_name = self._extract_with_patterns(content, self.policy_patterns['insured_name'])
        metadata.effective_date = self._extract_with_patterns(content, self.policy_patterns['effective_date'])
        metadata.expiration_date = self._extract_with_patterns(content, self.policy_patterns['expiration_date'])
        metadata.deductible = self._extract_with_patterns(content, self.policy_patterns['deductible'])
        metadata.premium_amount = self._extract_with_patterns(content, self.policy_patterns['premium_amount'])
        metadata.agent_name = self._extract_with_patterns(content, self.policy_patterns['agent_name'])
        metadata.property_address = self._extract_with_patterns(content, self.policy_patterns['property_address'])
        
        # Extract common fields
        metadata.insurance_company = self._extract_with_patterns(content, self.common_patterns['insurance_company'])
        metadata.state = self._extract_with_patterns(content, self.common_patterns['state'])
        
        # Extract coverage information
        metadata.coverage_limits = self._extract_coverage_limits(content)
        metadata.coverage_types = self._extract_coverage_types(content)
        metadata.exclusions = self._extract_exclusions(content)
        metadata.endorsements = self._extract_endorsements(content)
        
        # Determine line of business
        metadata.line_of_business = self._determine_line_of_business(content)
        
        # Analyze content characteristics
        metadata.section_type = self._determine_section_type(content)
        metadata.content_complexity = self._assess_content_complexity(content)
        metadata.contains_monetary_values = self._contains_monetary_values(content)
        
        return metadata
    
    def extract_claim_metadata(self, content: str, filename: str = "") -> ClaimMetadata:
        """Extract comprehensive metadata from claim document content."""
        metadata = ClaimMetadata(filename=filename)
        
        # Extract basic claim information
        metadata.claim_id = self._extract_with_patterns(content, self.claim_patterns['claim_id'])
        metadata.policy_number = self._extract_with_patterns(content, self.policy_patterns['policy_number'])
        metadata.insured_name = self._extract_with_patterns(content, self.policy_patterns['insured_name'])
        metadata.date_of_loss = self._extract_with_patterns(content, self.claim_patterns['date_of_loss'])
        metadata.reported_date = self._extract_with_patterns(content, self.claim_patterns['reported_date'])
        metadata.loss_cause = self._extract_with_patterns(content, self.claim_patterns['loss_cause'])
        metadata.coverage_decision = self._extract_with_patterns(content, self.claim_patterns['coverage_decision'])
        metadata.payout_amount = self._extract_with_patterns(content, self.claim_patterns['payout_amount'])
        metadata.adjuster_name = self._extract_with_patterns(content, self.claim_patterns['adjuster_name'])
        metadata.claim_status = self._extract_with_patterns(content, self.claim_patterns['claim_status'])
        
        # Extract common fields
        metadata.insurance_company = self._extract_with_patterns(content, self.common_patterns['insurance_company'])
        metadata.location = self._extract_with_patterns(content, self.common_patterns['location'])
        
        # Extract detailed claim information
        metadata.settlement_summary = self._extract_settlement_summary(content)
        metadata.adjuster_notes = self._extract_adjuster_notes(content)
        metadata.property_damage = self._extract_property_damage(content)
        metadata.injury_details = self._extract_injury_details(content)
        
        # Analyze content characteristics
        metadata.section_type = self._determine_section_type(content)
        metadata.content_complexity = self._assess_content_complexity(content)
        metadata.contains_monetary_values = self._contains_monetary_values(content)
        
        return metadata
    
    def _extract_with_patterns(self, content: str, patterns: List[str]) -> Optional[str]:
        """Extract information using multiple regex patterns."""
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                result = match.group(1).strip()
                # Clean up the extracted text
                result = re.sub(r'\s+', ' ', result)
                if result and len(result) > 1:
                    return result
        return None
    
    def _extract_coverage_limits(self, content: str) -> Dict[str, str]:
        """Extract coverage limits from policy content."""
        limits = {}
        
        # Common coverage patterns
        coverage_patterns = [
            (r'coverage\s*([a-z])\s*[:-]\s*([^;:\n]+?)\s*:?\s*\$?([\d,]+)', 'coverage_{}'),
            (r'(dwelling|building)\s*:?\s*\$?([\d,]+)', 'dwelling'),
            (r'(personal\s*property|contents)\s*:?\s*\$?([\d,]+)', 'personal_property'),
            (r'(liability)\s*:?\s*\$?([\d,]+)', 'liability'),
            (r'(medical\s*payments?)\s*:?\s*\$?([\d,]+)', 'medical_payments'),
        ]
        
        for pattern in coverage_patterns:
            if len(pattern) == 3:
                regex, key_template = pattern[0], pattern[1]
                matches = re.finditer(regex, content, re.IGNORECASE)
                for match in matches:
                    if '{}' in key_template:
                        key = key_template.format(match.group(1).lower())
                        limits[key] = match.group(3) if len(match.groups()) >= 3 else match.group(2)
                    else:
                        limits[key_template] = match.group(2)
            else:
                regex, key = pattern
                match = re.search(regex, content, re.IGNORECASE)
                if match:
                    limits[key] = match.group(2)
        
        return limits
    
    def _extract_coverage_types(self, content: str) -> List[str]:
        """Extract types of coverage from content."""
        coverage_types = []
        
        # Coverage type indicators
        indicators = [
            'liability', 'collision', 'comprehensive', 'uninsured', 'underinsured',
            'medical payments', 'personal injury protection', 'pip', 'dwelling',
            'personal property', 'loss of use', 'additional living expense'
        ]
        
        content_lower = content.lower()
        for indicator in indicators:
            if indicator in content_lower:
                coverage_types.append(indicator)
        
        return list(set(coverage_types))  # Remove duplicates
    
    def _extract_exclusions(self, content: str) -> List[str]:
        """Extract policy exclusions."""
        exclusions = []
        
        # Find exclusion sections
        exclusion_patterns = [
            r'exclusion[s]?\s*:?\s*([^;\n]+)',
            r'not\s*covered\s*:?\s*([^;\n]+)',
            r'we\s*do\s*not\s*cover\s*([^;\n]+)',
        ]
        
        for pattern in exclusion_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                exclusion = match.group(1).strip()
                if exclusion and len(exclusion) > 5:
                    exclusions.append(exclusion)
        
        return exclusions
    
    def _extract_endorsements(self, content: str) -> List[str]:
        """Extract policy endorsements."""
        endorsements = []
        
        # Find endorsement patterns
        endorsement_patterns = [
            r'endorsement\s*([^;\n]+)',
            r'rider\s*([^;\n]+)',
            r'amendment\s*([^;\n]+)',
        ]
        
        for pattern in endorsement_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                endorsement = match.group(1).strip()
                if endorsement and len(endorsement) > 3:
                    endorsements.append(endorsement)
        
        return endorsements
    
    def _determine_line_of_business(self, content: str) -> str:
        """Determine the line of business from content."""
        content_lower = content.lower()
        
        if any(term in content_lower for term in ['homeowner', 'dwelling', 'property']):
            return 'property'
        elif any(term in content_lower for term in ['auto', 'vehicle', 'car']):
            return 'auto'
        elif any(term in content_lower for term in ['life', 'death benefit']):
            return 'life'
        elif any(term in content_lower for term in ['health', 'medical']):
            return 'health'
        elif 'commercial' in content_lower:
            return 'commercial'
        else:
            return 'general'
    
    def _extract_settlement_summary(self, content: str) -> Optional[str]:
        """Extract settlement summary from claim content."""
        patterns = [
            r'settlement\s*(?:summary)?\s*:?\s*([^;\n]{20,})',
            r'resolution\s*:?\s*([^;\n]{20,})',
            r'outcome\s*:?\s*([^;\n]{20,})',
        ]
        
        return self._extract_with_patterns(content, patterns)
    
    def _extract_adjuster_notes(self, content: str) -> List[str]:
        """Extract adjuster notes from claim content."""
        notes = []
        
        patterns = [
            r'notes?\s*:?\s*([^;\n]{10,})',
            r'comments?\s*:?\s*([^;\n]{10,})',
            r'observations?\s*:?\s*([^;\n]{10,})',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                note = match.group(1).strip()
                if note and len(note) > 10:
                    notes.append(note)
        
        return notes
    
    def _extract_property_damage(self, content: str) -> Optional[str]:
        """Extract property damage description."""
        patterns = [
            r'property\s*damage\s*:?\s*([^;\n]{10,})',
            r'damage\s*(?:description)?\s*:?\s*([^;\n]{10,})',
            r'damages?\s*:?\s*([^;\n]{10,})',
        ]
        
        return self._extract_with_patterns(content, patterns)
    
    def _extract_injury_details(self, content: str) -> Optional[str]:
        """Extract injury details from claim content."""
        patterns = [
            r'injur(?:y|ies)\s*(?:details?)?\s*:?\s*([^;\n]{10,})',
            r'bodily\s*injury\s*:?\s*([^;\n]{10,})',
            r'medical\s*(?:condition|status)\s*:?\s*([^;\n]{10,})',
        ]
        
        return self._extract_with_patterns(content, patterns)
    
    def _determine_section_type(self, content: str) -> str:
        """Determine the type of section based on content."""
        content_lower = content.lower()
        
        if any(term in content_lower for term in ['coverage', 'limit', 'deductible']):
            return 'coverage'
        elif any(term in content_lower for term in ['exclusion', 'not covered']):
            return 'exclusions'
        elif any(term in content_lower for term in ['condition', 'requirement']):
            return 'conditions'
        elif any(term in content_lower for term in ['claim', 'loss', 'incident']):
            return 'claims'
        elif any(term in content_lower for term in ['premium', 'payment']):
            return 'billing'
        else:
            return 'general'
    
    def _assess_content_complexity(self, content: str) -> str:
        """Assess the complexity of the content."""
        word_count = len(content.split())
        sentence_count = len([s for s in content.split('.') if s.strip()])
        
        if word_count < 50:
            return 'low'
        elif word_count < 200:
            return 'medium'
        else:
            return 'high'
    
    def _contains_monetary_values(self, content: str) -> bool:
        """Check if content contains monetary values."""
        return bool(re.search(r'\$[\d,]+', content))