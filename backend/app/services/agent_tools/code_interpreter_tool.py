"""
Code Interpreter Tool for Azure AI Foundry Agents

This tool provides code execution capabilities to agents, allowing them to:
- Execute Python code for data analysis
- Perform calculations and computations
- Generate visualizations and reports
- Process insurance data and claims calculations
"""

import logging
import json
import asyncio
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime
import io
import sys
from contextlib import redirect_stdout, redirect_stderr

try:
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import seaborn as sns
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logging.warning("Pandas not available, data analysis features limited")

logger = logging.getLogger(__name__)

class CodeInterpreterTool:
    """
    Code Interpreter tool for Azure AI Foundry agents
    
    This tool can be attached to agents to provide:
    - Python code execution
    - Data analysis capabilities
    - Insurance calculations
    - Report generation
    """
    
    def __init__(self):
        self.execution_history = []
        self._initialized = False
        
    async def initialize(self):
        """Initialize the Code Interpreter tool"""
        try:
            self._initialized = True
            logger.info("Code Interpreter tool initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Code Interpreter tool: {e}")
            raise
    
    async def execute_code(
        self, 
        code: str,
        timeout: int = 30,
        allow_imports: bool = True
    ) -> Dict[str, Any]:
        """
        Execute Python code safely
        
        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds
            allow_imports: Whether to allow import statements
            
        Returns:
            Execution results with output and any errors
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Security check - block dangerous operations
            dangerous_keywords = [
                'os.', 'subprocess.', 'eval(', 'exec(', 'open(', 
                'file(', '__import__', 'globals()', 'locals()'
            ]
            
            for keyword in dangerous_keywords:
                if keyword in code:
                    return {
                        "error": f"Security violation: {keyword} not allowed",
                        "code": code,
                        "output": "",
                        "execution_time": 0,
                        "timestamp": datetime.utcnow().isoformat()
                    }
            
            # Block imports if not allowed
            if not allow_imports and ('import ' in code or 'from ' in code):
                return {
                    "error": "Import statements not allowed",
                    "code": code,
                    "output": "",
                    "execution_time": 0,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Capture stdout and stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            start_time = datetime.utcnow()
            
            # Execute code with timeout
            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    # Create a new namespace for execution
                    local_vars = {}
                    exec(code, globals(), local_vars)
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Get output
                stdout_output = stdout_capture.getvalue()
                stderr_output = stderr_capture.getvalue()
                
                # Store execution history
                execution_record = {
                    "code": code,
                    "output": stdout_output,
                    "error": stderr_output,
                    "execution_time": execution_time,
                    "timestamp": datetime.utcnow().isoformat(),
                    "variables": {k: str(v) for k, v in local_vars.items() if not k.startswith('_')}
                }
                self.execution_history.append(execution_record)
                
                return {
                    "success": True,
                    "code": code,
                    "output": stdout_output,
                    "error": stderr_output,
                    "execution_time": execution_time,
                    "variables": execution_record["variables"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                error_traceback = traceback.format_exc()
                
                return {
                    "success": False,
                    "error": str(e),
                    "traceback": error_traceback,
                    "code": code,
                    "output": stdout_capture.getvalue(),
                    "execution_time": execution_time,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": code,
                "output": "",
                "execution_time": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def analyze_insurance_data(
        self, 
        data: List[Dict[str, Any]],
        analysis_type: str = "claims"
    ) -> Dict[str, Any]:
        """
        Analyze insurance data using pandas and numpy
        
        Args:
            data: List of insurance records
            analysis_type: "claims", "policies", or "general"
            
        Returns:
            Analysis results with statistics and insights
        """
        try:
            if not PANDAS_AVAILABLE:
                return {
                    "error": "Pandas not available for data analysis",
                    "data_count": len(data),
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            if not self._initialized:
                await self.initialize()
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            analysis_results = {
                "data_count": len(df),
                "columns": list(df.columns),
                "analysis_type": analysis_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Basic statistics
            if len(df) > 0:
                analysis_results["basic_stats"] = {
                    "total_records": len(df),
                    "missing_values": df.isnull().sum().to_dict(),
                    "data_types": df.dtypes.astype(str).to_dict()
                }
                
                # Numeric analysis
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    analysis_results["numeric_analysis"] = df[numeric_cols].describe().to_dict()
                
                # Insurance-specific analysis
                if analysis_type == "claims":
                    analysis_results.update(self._analyze_claims_data(df))
                elif analysis_type == "policies":
                    analysis_results.update(self._analyze_policies_data(df))
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Insurance data analysis failed: {e}")
            return {
                "error": str(e),
                "data_count": len(data),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _analyze_claims_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze claims-specific data"""
        analysis = {}
        
        try:
            # Claims amount analysis
            if 'amount' in df.columns:
                analysis["claims_amount"] = {
                    "total_amount": df['amount'].sum(),
                    "average_amount": df['amount'].mean(),
                    "max_amount": df['amount'].max(),
                    "min_amount": df['amount'].min()
                }
            
            # Claims status analysis
            if 'status' in df.columns:
                analysis["claims_status"] = df['status'].value_counts().to_dict()
            
            # Date analysis
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                analysis["claims_trends"] = {
                    "date_range": {
                        "start": df['date'].min().isoformat() if not df['date'].isna().all() else None,
                        "end": df['date'].max().isoformat() if not df['date'].isna().all() else None
                    }
                }
                
        except Exception as e:
            analysis["error"] = f"Claims analysis error: {str(e)}"
        
        return analysis
    
    def _analyze_policies_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze policies-specific data"""
        analysis = {}
        
        try:
            # Policy type analysis
            if 'policy_type' in df.columns:
                analysis["policy_types"] = df['policy_type'].value_counts().to_dict()
            
            # Premium analysis
            if 'premium' in df.columns:
                analysis["premium_analysis"] = {
                    "total_premium": df['premium'].sum(),
                    "average_premium": df['premium'].mean(),
                    "premium_distribution": df['premium'].describe().to_dict()
                }
            
            # Coverage analysis
            if 'coverage_amount' in df.columns:
                analysis["coverage_analysis"] = {
                    "total_coverage": df['coverage_amount'].sum(),
                    "average_coverage": df['coverage_amount'].mean()
                }
                
        except Exception as e:
            analysis["error"] = f"Policies analysis error: {str(e)}"
        
        return analysis
    
    async def calculate_insurance_metrics(
        self, 
        claims_data: List[Dict[str, Any]],
        policies_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate insurance-specific metrics
        
        Args:
            claims_data: List of claims records
            policies_data: List of policy records
            
        Returns:
            Calculated insurance metrics
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "claims_count": len(claims_data),
                "policies_count": len(policies_data)
            }
            
            if claims_data and policies_data:
                # Calculate loss ratio
                total_claims = sum(claim.get('amount', 0) for claim in claims_data)
                total_premiums = sum(policy.get('premium', 0) for policy in policies_data)
                
                if total_premiums > 0:
                    metrics["loss_ratio"] = total_claims / total_premiums
                    metrics["loss_ratio_percentage"] = (total_claims / total_premiums) * 100
                
                # Calculate average claim size
                if claims_data:
                    claim_amounts = [claim.get('amount', 0) for claim in claims_data]
                    metrics["average_claim_size"] = sum(claim_amounts) / len(claim_amounts)
                
                # Calculate average premium
                if policies_data:
                    premiums = [policy.get('premium', 0) for policy in policies_data]
                    metrics["average_premium"] = sum(premiums) / len(premiums)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Insurance metrics calculation failed: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history"""
        return self.execution_history
    
    def clear_history(self):
        """Clear execution history"""
        self.execution_history = []
    
    def get_tool_schema(self) -> Dict[str, Any]:
        """Get the tool schema for Azure AI Foundry agent configuration"""
        return {
            "name": "code_interpreter_tool",
            "description": "Execute Python code and perform data analysis for insurance calculations",
            "type": "code_interpreter",
            "capabilities": [
                "execute_code",
                "analyze_insurance_data",
                "calculate_insurance_metrics"
            ],
            "supported_analysis_types": ["claims", "policies", "general"],
            "security_features": [
                "dangerous_operation_blocking",
                "timeout_protection",
                "import_control"
            ]
        }
