import os
import pandas as pd

countries_dir = os.path.join(os.path.dirname(__file__), "countries")

for filename in os.listdir(countries_dir):
    if filename.endswith(".csv"):
        filepath = os.path.join(countries_dir, filename)
        df = pd.read_csv(filepath)
        print(f"\r\n=== {filename} ===")
        # print(df.info())

        # Find the minimum, maximum years
        min_year = df['Year'].min()
        print(f"Minimum Year = {min_year}", end=", ")
        max_year = df['Year'].max()
        print(f"Maximum Year = {max_year}", end=", ")

        # Min GDP
        min_gdp = df.loc[df['Year'].idxmin(), "GDP"] / 10**9
        print(f"Min GDP = {min_gdp:.2f}", end=", ")

        # Max GDP
        max_gdp = df.loc[df['Year'].idxmax(), "GDP"] / 10**9
        print(f"Max GDP = {max_gdp:.2f}", end=", ")

        # AVG
        avg = df["GDP"].mean() / 10**9
        print(f"Avg value = {avg:.2f}", end=", ")

        # Growing in percent
        print(f"Growing in percent = {((max_gdp - min_gdp) / min_gdp) * 100:.2f}%", end=", ")