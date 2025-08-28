import openai
import tiktoken
from typing import Dict, Any
from datetime import datetime
from openai_cost import validate_openai_cost_config, calculate_openai_cost
import time
from httpx import Timeout


class LogAnalyzer:
    
    def __init__(self, config: Dict[str, Any], openai_api_key: str, debug: bool = False):
        self.config = config
        self.debug = debug
        self.model = config['agent']['model']
        # Configure timeout for OpenAI client (120 seconds)
        timeout = Timeout(120.0, read=120.0, write=30.0, connect=10.0)
        self.openai_client = openai.OpenAI(api_key=openai_api_key, timeout=timeout)
        
        # Validate cost config on initialization
        if not validate_openai_cost_config():
            raise ValueError("OpenAI cost config validation failed")
            
        
    def create_prompts(self, logs_summary: str) -> tuple[str, str]:
        """
        Creates system and user prompts from a log summary.

        Args:
            logs_summary: A string containing the pre-formatted logs for analysis.

        Returns:
            A tuple containing the system and user prompts.
        """
        if not logs_summary:
            return "", ""
        
        # Directly use the system and user prompts from config, no context formatting
        return self.config['system_prompt'], self.config['user_prompt']
    
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        try:
            # Handle custom model names that tiktoken doesn't recognize
            if self.model in ["gpt-4o-mini", "gpt-4o"]:
                encoding = tiktoken.encoding_for_model("gpt-4")
            else:
                encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))
        except KeyError:
            # Fallback to gpt-4 encoding for unknown models
            try:
                encoding = tiktoken.encoding_for_model("gpt-4")
                return len(encoding.encode(text))
            except Exception:
                # Final fallback estimation
                return int(len(text.split()) * 1.3)
        except Exception:
            # Final fallback estimation
            return int(len(text.split()) * 1.3)
    
    def _call_openai(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> tuple[str, Dict[str, Any]]:
        """Call OpenAI API with retry logic and return result with usage statistics."""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                start_time = datetime.now()
                
                # Calculate input tokens
                input_tokens = self._count_tokens(system_prompt + user_prompt)
                
                if self.debug:
                    print(f"Attempt {attempt + 1}/{max_retries}: Calling OpenAI API with model '{self.model}'")
                    print(f"Input tokens: {input_tokens}")
                
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
           #         temperature=0.1,
           #         max_completion_tokens=4000
                )
                
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                
                if self.debug:
                    print(f"API call successful in {response_time:.2f}s")
                
                # Extract usage statistics
                prompt_tokens = response.usage.prompt_tokens if response.usage else input_tokens
                completion_tokens = response.usage.completion_tokens if response.usage else 0
                total_tokens = response.usage.total_tokens if response.usage else input_tokens
                
                # Calculate cost
                cost = calculate_openai_cost(self.model, prompt_tokens, completion_tokens)
                
                usage_stats = {
                    'model': self.model,
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                    'response_time_seconds': round(response_time, 2),
                    'timestamp': datetime.now().isoformat(),
                    'attempts': attempt + 1,
                    'cost_usd': cost
                }
                
                return response.choices[0].message.content, usage_stats
                
            except openai.RateLimitError as e:
                last_exception = e
                if self.debug:
                    print(f"Rate limit error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 1  # Exponential backoff
                    if self.debug:
                        print(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                    
            except (openai.APITimeoutError, openai.APIConnectionError) as e:
                last_exception = e
                if self.debug:
                    print(f"Connection/timeout error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2  # Longer wait for connection issues
                    if self.debug:
                        print(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                    
            except Exception as e:
                last_exception = e
                if self.debug:
                    print(f"Unexpected error on attempt {attempt + 1}: {e}")
                # Don't retry for unexpected errors
                break
        
        # All retries failed
        error_msg = f"OpenAI API call failed after {max_retries} attempts. Last error: {last_exception}"
        error_stats = {
            'model': self.model,
            'prompt_tokens': self._count_tokens(system_prompt + user_prompt),
            'completion_tokens': 0,
            'total_tokens': self._count_tokens(system_prompt + user_prompt),
            'error': str(last_exception),
            'timestamp': datetime.now().isoformat(),
            'attempts': max_retries,
            'failed': True
        }
        return error_msg, error_stats

    def analyze_logs(self, system_prompt: str, user_prompt: str) -> tuple[str, Dict[str, Any]]:
        """
        Analyze logs using AI with the given prompts.

        Args:
            system_prompt: The system prompt for the AI.
            user_prompt: The user prompt for the AI.

        Returns:
            Tuple of (analysis_result, usage_statistics)
        """
        if not system_prompt or not user_prompt:
            return "No logs to analyze.", {}

        return self._call_openai(system_prompt, user_prompt)
