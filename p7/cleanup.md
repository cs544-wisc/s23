# Data Cleanup

We've already created `hdma-wi-2021.parquet` for you.  If you're
curious how, see the code below.  Among other cleanup work, we skip
some loans because of missing data (for example, no income) or because
of outliers (for example, properties over $10 million).

```python
import pandas as pd
columns = {
    "state_code": "string",
    "county_code": "string",
    "census_tract": "string",
    "action_taken": "int",
    "loan_amount": "float",
    "income": "float",
    "interest_rate": "float",
    "loan_term": "float",
}
df = pd.read_csv("hdma-wi-2021.csv", usecols=sorted(list(columns.keys())), dtype=columns, na_values=["Exempt"])
df["income"] *= 1000
df["approved"] = (df["action_taken"] == 1)
df = df[~df["income"].isna()]
df = df[(df["loan_amount"] < 10000000) &
        (df["income"] < 1000000) &
        (df["income"] >= 0) &
        (df["loan_term"].isin([120, 180, 240, 360]))]
df.drop(columns=["action_taken"])
df.to_parquet("hdma-wi-2021.parquet")
```