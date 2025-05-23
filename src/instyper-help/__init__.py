import streamlit as st

st.set_page_config(page_title="Instyper - Download & Help", page_icon="🎤", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        margin: -1rem -1rem 3rem -1rem;
        color: white;
    }
    
    .logo-title {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1rem;
    }
    
    .feature-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .download-section {
        background: #ffffff;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 2rem 0;
    }
    
    .platform-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        text-align: center;
        margin: 1rem 0;
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }
    
    .platform-card:hover {
        border-color: #667eea;
        transform: translateY(-2px);
    }
    
    .stats-container {
        display: flex;
        justify-content: space-around;
        margin: 2rem 0;
        flex-wrap: wrap;
    }
    
    .stat-item {
        text-align: center;
        padding: 1rem;
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }
    
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .cta-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 3rem 2rem;
        border-radius: 12px;
        text-align: center;
        margin: 3rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("""
<div class='main-header'>
    <div class='logo-title'>
        <img src='https://freetubeapp.io/img/logo.svg' width='64'>
        <h1 style='margin: 0; font-size: 3rem;'>Instyper</h1>
    </div>
    <h3 style='margin: 0; font-weight: 300; opacity: 0.9;'>The Private Voice Typer</h3>
    <p style='margin: 1rem 0 0 0; font-size: 1.2rem; opacity: 0.8;'>
        Type with your voice, offline, in many languages. Your data stays private and local.
    </p>
</div>
""", unsafe_allow_html=True)

# --- QUICK STATS ---
st.markdown("""
<div class='stats-container'>
    <div class='stat-item'>
        <div class='stat-number'>🔒</div>
        <div>100% Private</div>
    </div>
    <div class='stat-item'>
        <div class='stat-number'>📱</div>
        <div>Cross Platform</div>
    </div>
    <div class='stat-item'>
        <div class='stat-number'>🆓</div>
        <div>Free & Open Source</div>
    </div>
    <div class='stat-item'>
        <div class='stat-number'>🌍</div>
        <div>50+ Languages</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- DOWNLOAD SECTION ---
st.markdown("""
<div class='download-section'>
    <h2 style='text-align: center; color: #333; margin-bottom: 2rem;'>
        📥 Download Instyper v1.0.0
    </h2>
    <p style='text-align: center; color: #666; margin-bottom: 2rem;'>
        Instyper is free to download thanks to its open source nature.
    </p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class='platform-card'>
        <h3>🪟 Windows</h3>
        <p>Windows 10 and later</p>
    </div>
    """, unsafe_allow_html=True)
    st.download_button("📦 .exe (x64)", "", file_name="instyper-windows.exe", disabled=True, use_container_width=True)
    st.download_button("🗜️ .zip (x64)", "", file_name="instyper-windows.zip", disabled=True, use_container_width=True)

with col2:
    st.markdown("""
    <div class='platform-card'>
        <h3>🍎 macOS</h3>
        <p>macOS 11 and later</p>
    </div>
    """, unsafe_allow_html=True)
    st.download_button("📦 .pkg (x64)", "", file_name="instyper-darwin.pkg", disabled=True, use_container_width=True)
    st.download_button("🗜️ .zip (x64)", "", file_name="instyper-darwin.zip", disabled=True, use_container_width=True)

with col3:
    st.markdown("""
    <div class='platform-card'>
        <h3>🐧 Linux</h3>
        <p>Ubuntu, Debian, Fedora</p>
    </div>
    """, unsafe_allow_html=True)
    st.download_button("📦 .deb (x64)", "", file_name="instyper-linux.deb", disabled=True, use_container_width=True)
    st.download_button("📦 .rpm (x64)", "", file_name="instyper-linux.rpm", disabled=True, use_container_width=True)

# --- FEATURES SECTION ---
st.markdown("## ✨ Current Features")

st.markdown("""
<div class='feature-grid'>
    <div class='feature-card'>
        <h4>🎤 Offline Voice Typing</h4>
        <p>Type with your voice without internet connection in 50+ languages</p>
    </div>
    
    <div class='feature-card'>
        <h4>🔒 Complete Privacy</h4>
        <p>All data stays on your device. No tracking, no data collection</p>
    </div>
    
    <div class='feature-card'>
        <h4>🚫 No Ads</h4>
        <p>Enjoy a clean, distraction-free experience</p>
    </div>
    
    <div class='feature-card'>
        <h4>💾 Local Storage</h4>
        <p>All your settings and data are stored locally on your machine</p>
    </div>
    
    <div class='feature-card'>
        <h4>🌍 Multi-Language</h4>
        <p>Support for 50+ languages with easy language switching</p>
    </div>
    
    <div class='feature-card'>
        <h4>⚡ Fast & Lightweight</h4>
        <p>Optimized performance with minimal system resource usage</p>
    </div>
    
    <div class='feature-card'>
        <h4>🎨 Familiar Design</h4>
        <p>Clean, intuitive interface that's easy to use</p>
    </div>
    
    <div class='feature-card'>
        <h4>🔓 Open Source</h4>
        <p>Free and Open Source Software under the MIT License</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- CTA SECTION ---
st.markdown("""
<div class='cta-section'>
    <h2>Ready to get started?</h2>
    <p style='font-size: 1.2rem; margin: 1rem 0 2rem 0;'>
        Join thousands of users who trust Instyper for private voice typing
    </p>
    <p>
        <strong>Download now and experience truly private voice typing!</strong>
    </p>
</div>
""", unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 📞 Contact & Support
    - [GitHub Issues](https://github.com/instyper/instyper/issues)
    - [Email Support](mailto:support@instyper.app)
    - [Community Forum](#)
    """)

with col2:
    st.markdown("""
    ### 🔗 Useful Links
    - [Documentation](#)
    - [Privacy Policy](#)
    - [Source Code](https://github.com/instyper/instyper)
    """)

with col3:
    st.markdown("""
    ### ❤️ Support the Project
    - [GitHub Sponsors](#)
    - [Buy us a coffee](#)
    - [Contribute Code](#)
    """)

st.markdown("""
---
<div style='text-align: center; color: #666; padding: 2rem 0;'>
    <small>
        Inspired by <a href='https://freetubeapp.io/' target='_blank'>FreeTube</a>. 
        Not affiliated. Made with ❤️ for privacy.
    </small>
</div>
""", unsafe_allow_html=True)
