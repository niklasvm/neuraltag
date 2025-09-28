#!/usr/bin/env python3
"""
Simple script to analyze workout builder user headers and behavior
"""

import json
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any
import pandas as pd

class WorkoutAnalyzer:
    def __init__(self, log_file: str = "workout_headers.jsonl"):
        self.log_file = Path(log_file)
        self.events = []
        self.load_events()
    
    def load_events(self):
        """Load events from JSONL file"""
        if not self.log_file.exists():
            print(f"Log file {self.log_file} not found")
            return
        
        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    self.events.append(event)
                except json.JSONDecodeError:
                    continue
    
    def get_header_summary(self) -> Dict[str, Any]:
        """Analyze captured headers"""
        if not self.events:
            return {}
        
        # Extract unique headers and their frequency
        header_keys = Counter()
        user_agents = Counter()
        languages = Counter()
        referrers = Counter()
        
        for event in self.events:
            headers = event.get('headers', {})
            
            # Count header keys
            header_keys.update(headers.keys())
            
            # Analyze specific headers
            if 'user-agent' in headers:
                user_agents[headers['user-agent']] += 1
            
            if 'accept-language' in headers:
                languages[headers['accept-language']] += 1
            
            if 'referer' in headers:
                referrers[headers['referer']] += 1
        
        return {
            'total_events': len(self.events),
            'unique_sessions': len(set(e.get('headers', {}).get('session_id') for e in self.events)),
            'header_keys': dict(header_keys.most_common()),
            'user_agents': dict(user_agents.most_common(10)),
            'languages': dict(languages.most_common()),
            'referrers': dict(referrers.most_common())
        }
    
    def get_user_behavior(self) -> Dict[str, Any]:
        """Analyze user behavior patterns"""
        if not self.events:
            return {}
        
        # Group events by session
        sessions = defaultdict(list)
        for event in self.events:
            session_id = event.get('headers', {}).get('session_id')
            if session_id:
                sessions[session_id].append(event)
        
        # Analyze behavior patterns
        event_types = Counter()
        session_lengths = []
        conversion_funnel = {
            'page_visits': 0,
            'input_changes': 0,
            'generation_attempts': 0,
            'successful_generations': 0,
            'fit_downloads': 0,
            'yaml_views': 0
        }
        
        for session_id, session_events in sessions.items():
            session_lengths.append(len(session_events))
            
            session_event_types = [e.get('event_type') for e in session_events]
            event_types.update(session_event_types)
            
            # Update conversion funnel
            if 'page_visit' in session_event_types:
                conversion_funnel['page_visits'] += 1
            if 'input_change' in session_event_types:
                conversion_funnel['input_changes'] += 1
            if 'button_click' in session_event_types:
                conversion_funnel['generation_attempts'] += 1
            if 'generation_success' in session_event_types:
                conversion_funnel['successful_generations'] += 1
            if 'fit_download' in session_event_types:
                conversion_funnel['fit_downloads'] += 1
            if 'yaml_viewed' in session_event_types:
                conversion_funnel['yaml_views'] += 1
        
        # Calculate conversion rates
        if conversion_funnel['page_visits'] > 0:
            conversion_rates = {
                'input_rate': conversion_funnel['input_changes'] / conversion_funnel['page_visits'] * 100,
                'generation_rate': conversion_funnel['generation_attempts'] / conversion_funnel['page_visits'] * 100,
                'success_rate': conversion_funnel['successful_generations'] / max(conversion_funnel['generation_attempts'], 1) * 100,
                'download_rate': conversion_funnel['fit_downloads'] / max(conversion_funnel['successful_generations'], 1) * 100,
            }
        else:
            conversion_rates = {}
        
        return {
            'total_sessions': len(sessions),
            'event_types': dict(event_types.most_common()),
            'avg_session_length': sum(session_lengths) / len(session_lengths) if session_lengths else 0,
            'conversion_funnel': conversion_funnel,
            'conversion_rates': conversion_rates
        }
    
    def get_workout_insights(self) -> Dict[str, Any]:
        """Analyze workout-specific data"""
        workout_names = []
        prompt_lengths = []
        error_types = Counter()
        
        for event in self.events:
            data = event.get('data', {})
            
            if event.get('event_type') == 'generation_start':
                if 'workout_name' in data:
                    workout_names.append(data['workout_name'])
                if 'prompt_length' in data:
                    prompt_lengths.append(data['prompt_length'])
            
            if event.get('event_type') == 'generation_error':
                error_type = data.get('error_type', 'unknown')
                error_types[error_type] += 1
        
        return {
            'popular_workout_names': dict(Counter(workout_names).most_common(10)),
            'avg_prompt_length': sum(prompt_lengths) / len(prompt_lengths) if prompt_lengths else 0,
            'error_types': dict(error_types.most_common())
        }
    
    def print_report(self):
        """Print a comprehensive report"""
        print("=" * 50)
        print("WORKOUT BUILDER ANALYTICS REPORT")
        print("=" * 50)
        
        # Header Analysis
        header_summary = self.get_header_summary()
        print(f"\n📊 HEADER ANALYSIS")
        print(f"Total Events: {header_summary.get('total_events', 0)}")
        print(f"Unique Sessions: {header_summary.get('unique_sessions', 0)}")
        
        if header_summary.get('user_agents'):
            print(f"\n🌐 User Agents:")
            for ua, count in list(header_summary['user_agents'].items())[:3]:
                print(f"  {count}x: {ua[:80]}...")
        
        if header_summary.get('languages'):
            print(f"\n🗣️ Languages:")
            for lang, count in header_summary['languages'].items():
                print(f"  {count}x: {lang}")
        
        # Behavior Analysis
        behavior = self.get_user_behavior()
        print(f"\n📈 USER BEHAVIOR")
        print(f"Total Sessions: {behavior.get('total_sessions', 0)}")
        print(f"Avg Events per Session: {behavior.get('avg_session_length', 0):.1f}")
        
        print(f"\n🔄 Conversion Funnel:")
        funnel = behavior.get('conversion_funnel', {})
        for stage, count in funnel.items():
            print(f"  {stage.replace('_', ' ').title()}: {count}")
        
        print(f"\n📊 Conversion Rates:")
        rates = behavior.get('conversion_rates', {})
        for rate_name, rate_value in rates.items():
            print(f"  {rate_name.replace('_', ' ').title()}: {rate_value:.1f}%")
        
        # Workout Insights
        workout_insights = self.get_workout_insights()
        print(f"\n🏃 WORKOUT INSIGHTS")
        
        if workout_insights.get('popular_workout_names'):
            print(f"Popular Workout Names:")
            for name, count in list(workout_insights['popular_workout_names'].items())[:5]:
                print(f"  {count}x: {name}")
        
        print(f"Average Prompt Length: {workout_insights.get('avg_prompt_length', 0):.0f} characters")
        
        if workout_insights.get('error_types'):
            print(f"\nError Types:")
            for error_type, count in workout_insights['error_types'].items():
                print(f"  {count}x: {error_type}")

if __name__ == "__main__":
    analyzer = WorkoutAnalyzer()
    analyzer.print_report()