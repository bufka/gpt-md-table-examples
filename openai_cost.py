"""
OpenAI Cost Utilities

Simple module for calculating OpenAI API costs based on token usage.
"""
from pathlib import Path
from typing import Optional

def validate_openai_cost_config(pricing_path: str = "openai-costs.yaml") -> bool:
    """
    Validate the OpenAI pricing configuration file.
    
    Args:
        pricing_path: Path to pricing config (relative to this file)
        
    Returns:
        bool: True if config is valid, False otherwise
    """
    try:
        import yaml
        
        # Correct path resolution - looks in same directory as this file
        config_path = Path(__file__).parent / pricing_path
        print(f"Loading config from: {config_path}")
        
        with open(config_path) as f:
            pricing_data = yaml.safe_load(f)
        
        if "model" not in pricing_data:
            raise ValueError("Pricing YAML must contain 'model' key")
            
        required_fields = {
            "name": str,
            "input": (int, float),
            "cached_input": (int, float),
            "output": (int, float)
        }
        
        for model in pricing_data["model"]:
            for field, expected_type in required_fields.items():
                if field not in model:
                    raise ValueError(f"Missing required field '{field}' in model {model.get('name', 'unknown')}")
                if not isinstance(model[field], expected_type):
                    raise ValueError(f"Field '{field}' must be {expected_type}, got {type(model[field])} in model {model.get('name', 'unknown')}")
        
        return True
    except Exception as e:
        print(f" Invalid OpenAI cost config: {str(e)}")
        return False


def calculate_openai_cost(
    model: str, 
    input_tokens: int, 
    output_tokens: int,
    pricing_path: str = "openai-costs.yaml"
) -> Optional[float]:
    try:
        if not validate_openai_cost_config(pricing_path):
            return None
            
        import yaml
        
        # Correct path resolution - looks in same directory as this file
        config_path = Path(__file__).parent / pricing_path
        
        with open(config_path) as f:
            pricing_data = yaml.safe_load(f)
        
        model_pricing = next(
            (m for m in pricing_data["model"] if m["name"] == model),
            None
        )
        
        if not model_pricing:
            return None
            
        input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
        return round(input_cost + output_cost, 4)
    except Exception as e:
        print(f" Error calculating OpenAI cost: {str(e)}")
        return None
