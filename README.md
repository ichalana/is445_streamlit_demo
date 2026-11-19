# IS445 Streamlit Homework: Illinois State Buildings

A Streamlit app with two visualizations of the
[Illinois State Building Inventory](https://raw.githubusercontent.com/UIUC-iSchool-DataViz/is445_data/main/building_inventory.csv)
dataset, plus a write-up for each one.

1. **Two centuries of state construction:** a stacked bar chart of square footage built per decade, linked by an interval brush to an agency bar chart. Clicking the legend highlights a use type.
2. **Which agencies own which kinds of buildings?:** an agency × use heatmap. Streamlit widgets pick the measure (count, square footage or median age), the building status and the construction-year range.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```
