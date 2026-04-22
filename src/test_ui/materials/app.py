import streamlit as st
import httpx
import asyncio
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"  # Adjust to your local API URL

st.set_page_config(page_title="RAG Materials Testing UI", layout="wide")

st.title("📚 Document RAG Testing UI")
st.markdown("Verify structural parsing (Levels 1-3) and retrieval quality.")

# Sidebar for Authentication
with st.sidebar:
    st.header("Authentication")
    firebase_uid = st.text_input("Firebase UID", value="", help="Simulate user identity for API requests")

    st.divider()
    st.info("This UI connects to the backend API to test file upload and structural search.")

# Helper for async API calls
async def api_call(method, endpoint, data=None, json=None, files=None, headers=None):
    async with httpx.AsyncClient() as client:
        # In a real scenario, we'd pass the Firebase token.
        # For testing purposes, we assume the backend is in a mode that accepts firebase_uid
        # or we mock the auth header.
        auth_headers = headers or {}
        if firebase_uid:
            auth_headers["x-firebase-uid"] = firebase_uid  # Custom header for testing mock auth

        response = await client.request(
            method,
            f"{API_BASE_URL}{endpoint}",
            data=data,
            json=json,
            files=files,
            headers=auth_headers,
            timeout=30.0
        )
        return response

def run_async(coro):
    return asyncio.run(coro)

# Main Tabs
tab1, tab2 = st.tabs(["📤 Upload & Index", "🔍 Structural Search"])

with tab1:
    st.header("Upload Document")
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx", "pptx", "txt"])

    if uploaded_file is not None:
        if st.button("Upload and Index"):
            if not firebase_uid:
                st.error("Please provide a Firebase UID in the sidebar first.")
            else:
                with st.spinner("Uploading and indexing..."):
                    # Prepare file for upload
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    try:
                        resp = run_async(api_call("POST", "/files/", files=files))
                        if resp.status_code == 201:
                            st.success(f"Successfully uploaded: {uploaded_file.name}")
                            st.json(resp.json())
                        else:
                            st.error(f"Upload failed: {resp.status_code}\n{resp.text}")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

with tab2:
    st.header("Search Materials")
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Search Query", placeholder="Enter a keyword or phrase...")
    with col2:
        limit = st.number_input("Limit", min_value=1, max_value=20, value=5)

    if st.button("Search"):
        if not firebase_uid:
            st.error("Please provide a Firebase UID in the sidebar first.")
        elif not query:
            st.warning("Please enter a search query.")
        else:
            with st.spinner("Searching..."):
                try:
                    payload = {"query": query, "limit": limit}
                    resp = run_async(api_call("POST", "/files/search", json=payload))

                    # Correction: if the API expects JSON body (which it does via DocumentSearchRequest),
                    # we should use json= instead of data= in httpx.
                    # Let's refine the helper if needed, but for now, try-catch.

                    if resp.status_code == 200:
                        results = resp.json()
                        if not results:
                            st.info("No results found.")
                        else:
                            st.subheader(f"Top {len(results)} Results")
                            for idx, chunk in enumerate(results):
                                with st.expander(f"Result {idx+1} - Page {chunk.get('metadata', {}).get('page_number', 'Unknown')}"):
                                    # Structural Hierarchy
                                    st.markdown("**Hierarchy:**")
                                    l1 = chunk.get("level1") or "N/A"
                                    l2 = chunk.get("level2") or "N/A"
                                    l3 = chunk.get("level3") or "N/A"
                                    st.markdown(f"`{l1}` $\\rightarrow$ `{l2}` $\\rightarrow$ `{l3}`")

                                    st.divider()
                                    st.markdown("**Content:**")
                                    st.write(chunk.get("content", ""))
                    else:
                        st.error(f"Search failed: {resp.status_code}\n{resp.text}")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
