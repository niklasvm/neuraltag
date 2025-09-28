"""
Alternative approach to capture request information using Streamlit's 
experimental request features and environment variables
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
import streamlit as st

class RequestInfoCapture:
    """Capture request information in Streamlit Cloud or other deployments"""
    
    @staticmethod
    def get_request_info() -> Dict[str, Any]:
        """Get available request information from environment and Streamlit"""
        info = {
            'timestamp': datetime.now().isoformat(),
            'streamlit_version': st.__version__
        }
        
        # Try to get information from environment variables
        # These are often available in cloud deployments
        env_headers = [
            'HTTP_USER_AGENT',
            'HTTP_ACCEPT_LANGUAGE', 
            'HTTP_REFERER',
            'HTTP_X_FORWARDED_FOR',  # Real IP behind proxy
            'HTTP_X_REAL_IP',
            'HTTP_HOST',
            'REQUEST_METHOD',
            'QUERY_STRING',
            'REMOTE_ADDR',
            'SERVER_NAME',
            'SERVER_PORT'
        ]
        
        for header in env_headers:
            value = os.environ.get(header)
            if value:
                info[header.lower()] = value
        
        # Try Streamlit's experimental features (if available)
        try:
            # Some deployments expose this
            if hasattr(st, 'experimental_get_query_params'):
                query_params = st.experimental_get_query_params()
                if query_params:
                    info['query_params'] = query_params
        except Exception:
            pass
        
        # Try to get URL parameters
        try:
            query_params = st.query_params
            if query_params:
                info['url_params'] = dict(query_params)
        except Exception:
            pass
        
        return info
    
    @staticmethod
    def log_to_file(event_type: str, data: Optional[Dict] = None, filename: str = "request_info.jsonl"):
        """Log request info to file"""
        log_entry = {
            'event_type': event_type,
            'request_info': RequestInfoCapture.get_request_info(),
            'data': data or {},
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    @staticmethod
    def display_available_info():
        """Debug function to see what information is available"""
        st.subheader("Available Request Information")
        info = RequestInfoCapture.get_request_info()
        
        if info:
            st.json(info)
        else:
            st.write("No request information available")
        
        st.subheader("Environment Variables (HTTP_*)")
        env_vars = {k: v for k, v in os.environ.items() if k.startswith('HTTP_')}
        if env_vars:
            st.json(env_vars)
        else:
            st.write("No HTTP environment variables found")

# Usage example:
if __name__ == "__main__":
    # For debugging - add this to your app temporarily
    RequestInfoCapture.display_available_info()