# ScreenExplore

Everything the system collected, filterable by decision. Default filter: Apply + Answer first; Not for now is one tap away, never removed. Table view mirrors `st.dataframe` (select rows → *Compare*, max 3); Cards view reuses OpportunityCard.

**Streamlit:** filters `st.pills(selection_mode="multi")`; view `st.segmented_control(["Cards","Table"])`; table `st.dataframe(on_select="rerun", selection_mode="multi-row")` with column_config for verdict and priority; compare bar with `st.button("Compare 2", type="primary")`.
