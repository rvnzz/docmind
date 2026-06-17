import streamlit as st
import requests
import os
from datetime import datetime

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(page_title="DocMind", page_icon="📄", layout="wide")
st.title("📄 DocMind")

tab1, tab2, tab3, tab4 = st.tabs(["Upload", "Documents", "Q&A", "History"])

# upload tab
with tab1:
    st.header("Upload Documents")
    
    with st.form("upload_form"):
        files = st.file_uploader(
            "Select files",
            accept_multiple_files=True,
            type=['pdf', 'docx', 'txt', 'md', 'html', 'xlsx', 'pptx']
        )
        
        submitted = st.form_submit_button("Upload")
        
        if submitted and files:
            with st.spinner("Processing..."):
                # TODO: handle large files better, this loads everything into memory
                file_data = [("files", (f.name, f.getvalue(), f.type)) for f in files]
                
                try:
                    resp = requests.post(f"{API_BASE}/upload-batch", files=file_data)
                    
                    if resp.status_code == 200:
                        res = resp.json()
                        st.success(f"Uploaded {res['success']}/{res['total']}")
                        
                        if res['errors'] > 0:
                            st.warning(f"Errors: {res['errors']}")
                            for err in res['error_details']:
                                st.error(f"{err['filename']}: {err['error']}")
                        
                        for r in res['results']:
                            st.info(f"📄 {r['filename']} - {r['id']}")
                    else:
                        st.error(f"Failed: {resp.text}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

# documents list
with tab2:
    st.header("Documents")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("Search", placeholder="filename...")
    with col2:
        refresh = st.button("🔄 Refresh")
    
    if refresh or 'docs_loaded' not in st.session_state:
        try:
            if search:
                resp = requests.post(
                    f"{API_BASE}/documents/search",
                    json={"query": search, "page": 1, "limit": 100}
                )
            else:
                resp = requests.get(f"{API_BASE}/documents", params={"page": 1, "limit": 100})
            
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.docs = data['documents']
                st.session_state.total_docs = data['total']
                st.session_state.docs_loaded = True
            else:
                st.error(f"Error: {resp.text}")
        except Exception as e:
            st.error(f"Connection error: {e}")
    
    if st.session_state.get('docs_loaded'):
        st.metric("Total", st.session_state.get('total_docs', 0))
        
        if st.session_state.docs:
            for doc in st.session_state.docs:
                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    
                    with c1:
                        st.markdown(f"**{doc['filename']}**")
                        st.caption(f"ID: {doc['id']}")
                    
                    with c2:
                        st.caption(f"Type: {doc['file_type']}")
                    
                    with c3:
                        st.caption(f"Status: {doc['status']}")
                    
                    with c4:
                        # FIXME: should confirm before delete
                        if st.button("🗑️", key=f"del_{doc['id']}"):
                            try:
                                del_resp = requests.delete(f"{API_BASE}/documents/{doc['id']}")
                                if del_resp.status_code == 200:
                                    st.success(f"Deleted: {doc['filename']}")
                                    st.session_state.docs_loaded = False
                                    st.rerun()
                                else:
                                    st.error(f"Delete failed: {del_resp.text}")
                            except Exception as e:
                                st.error(f"Error: {e}")
                    
                    st.divider()
        else:
            st.info("No documents found")

# qa tab
with tab3:
    st.header("Ask a Question")
    
    question = st.text_area("Your question:", height=100)
    
    col1, col2 = st.columns([1, 3])
    with col1:
        top_k = st.slider("Sources", 1, 10, 5)
    with col2:
        ask_btn = st.button("🔍 Ask", type="primary")
    
    if ask_btn and question:
        with st.spinner("Searching..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/ask",
                    json={
                        "question": question,
                        "top_k": top_k,
                        "include_sources": True
                    }
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    
                    st.success("Answer found")
                    st.markdown("### Answer")
                    st.write(result['answer'])
                    
                    if result.get('sources'):
                        st.markdown("### Sources")
                        for idx, src in enumerate(result['sources'], 1):
                            with st.expander(f"📄 {src['filename']} (chunk {src['chunk_index']})"):
                                st.write(src['content'])
                                if src.get('similarity_score'):
                                    st.caption(f"Similarity: {src['similarity_score']:.4f}")
                    
                    if result.get('processing_time_ms'):
                        st.caption(f"⏱️ {result['processing_time_ms']:.2f} ms")
                else:
                    st.error(f"Error: {resp.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")

# history
with tab4:
    st.header("History")
    
    if st.button("🔄 Load History"):
        try:
            resp = requests.get(f"{API_BASE}/history", params={"page": 1, "limit": 50})
            
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.history = data['history']
                st.session_state.total_history = data['total']
            else:
                st.error(f"Error: {resp.text}")
        except Exception as e:
            st.error(f"Connection error: {e}")
    
    if st.session_state.get('history'):
        st.metric("Total", st.session_state.get('total_history', 0))
        
        # reverse so newest at bottom, feels more natural
        for item in reversed(st.session_state.history):
            with st.expander(f"❓ {item['question'][:100]}..."):
                st.markdown("**Question:**")
                st.write(item['question'])
                
                st.markdown("**Answer:**")
                st.write(item['answer'])
                
                if item.get('sources'):
                    st.markdown("**Sources:**")
                    for src in item['sources']:
                        st.caption(f"📄 {src['filename']}")
                
                if item.get('created_at'):
                    st.caption(f"🕒 {item['created_at']}")
                
                st.divider()
    else:
        st.info("No history yet. Click 'Load History'")

st.divider()
st.caption("DocMind v1.0.0")
