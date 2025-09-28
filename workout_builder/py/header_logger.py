import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import streamlit as st

class HeaderLogger:
    def __init__(self, log_file: str = "user_headers.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
    
    def get_session_id(self) -> str:
        """Get or create session ID"""
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        return st.session_state.session_id
    
    def capture_headers(self) -> Dict[str, Any]:
        """Capture available headers and context from Streamlit"""
        headers = {}
        
        try:
            # Try to get headers from streamlit context
            if hasattr(st, 'context') and hasattr(st.context, 'headers'):
                # This works in some Streamlit deployments
                headers.update(dict(st.context.headers))
        except Exception:
            pass
        
        # Get URL parameters and query params
        try:
            query_params = st.query_params
            if query_params:
                headers['query_params'] = dict(query_params)
        except Exception:
            pass
        
        # Browser info that Streamlit can detect
        headers.update({
            'timestamp': datetime.now().isoformat(),
            'session_id': self.get_session_id(),
            'streamlit_version': st.__version__,
        })
        
        return headers
    
    def log_event(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        """Log an event with headers"""
        event = {
            'event_type': event_type,
            'headers': self.capture_headers(),
            'data': data or {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Append to JSONL file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(event) + '\n')
    
    def get_client_info(self) -> Dict[str, str]:
        """Extract useful client info from whatever we can capture"""
        headers = self.capture_headers()
        
        client_info = {
            'session_id': headers.get('session_id', 'unknown'),
            'user_agent': headers.get('user-agent', 'unknown'),
            'accept_language': headers.get('accept-language', 'unknown'),
            'referer': headers.get('referer', 'direct'),
            'timestamp': headers.get('timestamp', 'unknown')
        }
        
        return client_info