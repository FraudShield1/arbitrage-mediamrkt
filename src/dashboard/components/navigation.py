"""
Navigation Manager for Multi-Tab Dashboard

Handles sidebar navigation, page routing, and breadcrumb generation.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class NavigationManager:
    """Manages navigation state and rendering for the dashboard."""
    
    def __init__(self):
        """Initialize navigation manager."""
        self.current_page = None
        self.page_history = []
    
    def render_sidebar_navigation(self, pages: Dict[str, Any]) -> str:
        """
        Render sidebar navigation and return selected page.
        
        Args:
            pages: Dictionary of page configurations
            
        Returns:
            Selected page key
        """
        with st.sidebar:
            st.markdown("### 🧭 Navigation")
            
            # Sort pages by order
            sorted_pages = sorted(pages.items(), key=lambda x: x[1]['order'])
            
            # Create navigation options
            page_options = [page_info['title'] for page_key, page_info in sorted_pages]
            page_keys = [page_key for page_key, page_info in sorted_pages]
            
            # Get current selection
            if 'current_page' not in st.session_state:
                st.session_state.current_page = page_keys[0]
            
            # Find current index
            try:
                current_index = page_keys.index(st.session_state.current_page)
            except ValueError:
                current_index = 0
                st.session_state.current_page = page_keys[0]
            
            # Render navigation
            selected_index = st.radio(
                "Select Page",
                range(len(page_options)),
                format_func=lambda x: page_options[x],
                index=current_index,
                label_visibility="collapsed"
            )
            
            # Update current page
            selected_page = page_keys[selected_index]
            if selected_page != st.session_state.current_page:
                # Update page history
                if st.session_state.current_page not in self.page_history:
                    self.page_history.append(st.session_state.current_page)
                st.session_state.current_page = selected_page
                self.current_page = selected_page
            
            # Show page description
            current_page_info = pages[selected_page]
            st.markdown(f"*{current_page_info['description']}*")
            
            return selected_page
    
    def render_breadcrumbs(self, pages: Dict[str, Any], current_page: str):
        """
        Render breadcrumb navigation.
        
        Args:
            pages: Dictionary of page configurations
            current_page: Currently selected page key
        """
        if current_page in pages:
            page_title = pages[current_page]['title']
            st.markdown(f"**📍 {page_title}**")
            st.markdown("---")
    
    def get_page_context(self, page_key: str) -> Dict[str, Any]:
        """
        Get context information for a specific page.
        
        Args:
            page_key: Page identifier
            
        Returns:
            Page context dictionary
        """
        return {
            'page_key': page_key,
            'visit_count': self._get_visit_count(page_key),
            'last_visited': self._get_last_visited(page_key),
            'is_new_session': self._is_new_session()
        }
    
    def _get_visit_count(self, page_key: str) -> int:
        """Get visit count for a page."""
        if 'page_visits' not in st.session_state:
            st.session_state.page_visits = {}
        
        return st.session_state.page_visits.get(page_key, 0)
    
    def _increment_visit_count(self, page_key: str):
        """Increment visit count for a page."""
        if 'page_visits' not in st.session_state:
            st.session_state.page_visits = {}
        
        st.session_state.page_visits[page_key] = st.session_state.page_visits.get(page_key, 0) + 1
    
    def _get_last_visited(self, page_key: str) -> Optional[str]:
        """Get last visited timestamp for a page."""
        if 'page_last_visited' not in st.session_state:
            st.session_state.page_last_visited = {}
        
        return st.session_state.page_last_visited.get(page_key)
    
    def _update_last_visited(self, page_key: str):
        """Update last visited timestamp for a page."""
        if 'page_last_visited' not in st.session_state:
            st.session_state.page_last_visited = {}
        
        from datetime import datetime
        st.session_state.page_last_visited[page_key] = datetime.now().isoformat()
    
    def _is_new_session(self) -> bool:
        """Check if this is a new session."""
        return 'session_initialized' not in st.session_state
    
    def track_page_visit(self, page_key: str):
        """
        Track a page visit for analytics.
        
        Args:
            page_key: Page identifier
        """
        self._increment_visit_count(page_key)
        self._update_last_visited(page_key)
        
        # Mark session as initialized
        st.session_state.session_initialized = True 