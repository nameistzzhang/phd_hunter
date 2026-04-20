"""Streamlit frontend for PhD Hunter."""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from phd_hunter.main import PhDHunter
from phd_hunter.utils import get_logger

logger = get_logger(__name__)

# Page config
st.set_page_config(
    page_title="PhD Hunter - 导师套磁筛选助手",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #0066CC;
        text-align: center;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .professor-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: #f9f9f9;
    }
    .score-badge {
        background: #0066CC;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 5px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application."""
    # Header
    st.markdown('<h1 class="main-header">🎓 PhD Hunter</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">智能化的 PhD 导师套磁筛选系统</p>',
        unsafe_allow_html=True
    )

    # Sidebar
    with st.sidebar:
        st.header("🔍 搜索设置")

        # University input
        universities = st.text_input(
            "目标大学 (用逗号分隔)",
            placeholder="MIT, Stanford, Berkeley",
            help="输入你想申请的大学名称"
        )
        uni_list = [u.strip() for u in universities.split(",") if u.strip()]

        # Research area
        research_area = st.selectbox(
            "研究领域",
            options=["", "AI", "ML", "NLP", "Computer Vision", "Systems", "Theory", "Security"],
            format_func=lambda x: "请选择..." if not x else x,
        )

        # Keywords
        keywords = st.text_input(
            "关键词 (可选)",
            placeholder="deep learning, reinforcement learning",
            help="额外的研究关键词"
        )
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]

        # Max results
        max_professors = st.slider(
            "最大结果数",
            min_value=10,
            max_value=200,
            value=50,
            step=10
        )

        # Search button
        search_button = st.button("🔍 开始搜索", type="primary", use_container_width=True)

    # Main content
    if search_button and (uni_list or research_area):
        with st.spinner("正在搜索教授信息..."):
            try:
                hunter = PhDHunter()
                result = asyncio.run(hunter.search(
                    universities=uni_list if uni_list else None,
                    research_area=research_area if research_area else None,
                    keywords=kw_list if kw_list else None,
                    max_professors=max_professors,
                ))

                st.success(f"✅ 找到 {len(result.professors)} 位教授")

                # Display results
                display_results(result.professors)

            except Exception as e:
                st.error(f"搜索失败: {e}")
                logger.error(f"Search failed: {e}")

    elif search_button:
        st.warning("请至少输入大学或选择研究领域")

    else:
        # Show welcome message
        st.info("👈 请在左侧设置搜索条件并点击'开始搜索'")

        # Show feature cards
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            ### 📊 智能匹配
            基于 LLM 分析论文和研究方向，计算匹配分数
            """)
        with col2:
            st.markdown("""
            ### 📈 数据驱动
            整合 CSRankings、Google Scholar、arXiv 数据
            """)
        with col3:
            st.markdown("""
            ### 📝 报告生成
            自动生成详细的套磁建议和风险评估
            """)


def display_results(professors: list[Professor]):
    """Display professor results."""
    if not professors:
        st.warning("未找到符合条件的教授")
        return

    # Sort by match score
    professors = sorted(professors, key=lambda p: p.match_score, reverse=True)

    # Summary stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("教授总数", len(professors))
    with col2:
        avg_score = sum(p.match_score for p in professors) / len(professors)
        st.metric("平均匹配分", f"{avg_score:.1f}%")
    with col3:
        accepting = sum(1 for p in professors if p.status == "accepting")
        st.metric("可能招生", accepting)
    with col4:
        high_score = sum(1 for p in professors if p.match_score >= 80)
        st.metric("高度匹配", high_score)

    st.divider()

    # Professor cards
    for prof in professors:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.subheader(f"{prof.name}")
                st.caption(f"🏫 {prof.university} | 📧 {prof.email or '邮箱未公开'}")

                if prof.research_interests:
                    tags = " ".join([f"`{tag}`" for tag in prof.research_interests[:5]])
                    st.markdown(f"**研究方向**: {tags}")

            with col2:
                st.metric("匹配度", f"{prof.match_score:.0f}%")
                st.metric("引用数", f"{prof.citation_count:,}")

            with col3:
                st.metric("H-index", prof.h_index)
                st.metric("近期论文", prof.recent_papers)

                # Action buttons
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("查看报告", key=f"report_{prof.id}"):
                        st.session_state.selected_professor = prof.id
                with btn_col2:
                    if st.button("保存", key=f"save_{prof.id}"):
                        st.success("已保存")

            st.divider()


if __name__ == "__main__":
    import asyncio
    main()
