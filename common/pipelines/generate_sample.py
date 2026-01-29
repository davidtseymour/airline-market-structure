import sqlite3
from datetime import timedelta
from pathlib import Path


import numpy as np
import pandas as pd
from tqdm import tqdm
from pprint import pprint


def create_sub_sample(
    pct_subsample: float,
    db_source: str,
    random_seed: int,
    year_min: int = 2004,
) -> tuple[pd.DataFrame, int]:
    """
    Draw a reproducible random subsample of flights from the SQLite `flights_data` table.

    This function samples by SQLite `rowid`, then reads the underlying table in rowid
    ranges ("chunks") and filters to the sampled rowids. It returns the subsampled flights
    as a DataFrame and the total number of eligible flights.

    Parameters
    ----------
    pct_subsample : float
        Fraction of eligible flights to sample (e.g., 0.02 for 2%).
    db_source : str
        Path to the SQLite database.
    random_seed : int
        Seed for reproducible random sampling.
    year_min : int, default 2004
        Minimum year to include when defining the sampling frame.

    Returns
    -------
    (return_df, num_total_flights) : tuple[pd.DataFrame, int]
        return_df is the subsampled flights DataFrame with selected columns renamed to
        snake_case. num_total_flights is the total number of eligible flights.
    """
    # Pull actual rowids (robust to gaps) for the sampling frame.
    with sqlite3.connect(db_source) as conn:
        rowids = pd.read_sql_query(
            "SELECT rowid FROM flights_data WHERE year >= ?",
            conn,
            params=(year_min,),
        )["rowid"].to_numpy()

    rng = np.random.default_rng(random_seed)
    num_total_flights = len(rowids)

    # Number of flights to sample (rounded to nearest integer).
    k = round(num_total_flights * pct_subsample)

    # Randomly sample rowids without replacement; sort for stable min/max chunking.
    sampled = np.sort(rng.choice(rowids, size=k, replace=False))
    sampled_set = set(sampled.tolist())

    print(f"Sampling {k} of {num_total_flights} flights.")

    chunks: list[pd.DataFrame] = []
    with sqlite3.connect(db_source) as conn:
        # Read the table in 100 rowid ranges between sampled min/max, then filter to sampled rowids.
        rmin, rmax = int(sampled.min()), int(sampled.max()) + 1
        for x in tqdm(range(100), desc="Reading flights_data chunks"):
            low = rmin + int(x * (rmax - rmin) / 100)
            high = rmin + int((x + 1) * (rmax - rmin) / 100)

            temp_df = pd.read_sql_query(
                "SELECT rowid, * FROM flights_data WHERE rowid >= ? AND rowid < ? AND year >= ?",
                conn,
                params=(low, high, year_min),
            )

            # Keep only sampled rowids within this chunk.
            chunks.append(temp_df[temp_df["rowid"].isin(sampled_set)])

    print("")
    return_df = pd.concat(chunks, ignore_index=True)

    # Normalize columns to snake_case for pipeline consistency.
    return_df = return_df.rename(
        columns={
            "DepDelay": "dep_delay",
            "ArrDelay": "arr_delay",
            "ActualElapsedTime": "actual_elapsed_time",
            "CRSElapsedTime": "crs_elapsed_time",
            "OriginAirportID": "origin_airport_id",
            "DestAirportID": "dest_airport_id",
            "DOT_ID_Reporting_Airline": "dot_id_reporting_airline",
            "ScheduledHour": "scheduled_hour",
            "Year": "year",
            "Month": "month",
            "DayofMonth": "day_of_month",
            "DayOfWeek": "day_of_week",
            "MonopolyRoute": "monopoly_route",
            "Distance": "distance",
            "TailNumberId": "tail_number_id",
            "Flight_Number_Reporting_Airline": "flight_number_reporting_airline",
            "CRSDepTime": "crs_dep_time",
            "CRSArrTime": "crs_arr_time",
            "DepTime": "dep_time",
            "ArrTime": "arr_time",
        }
    )

    return return_df, num_total_flights


def print_subsample_diagnosis(flights_df: pd.DataFrame) -> None:
    """Print basic shape and column diagnostics for a subsampled flights DataFrame."""
    print("Produced dataframe")
    print("  rows:", len(flights_df))
    print("  cols:", flights_df.shape[1])
    print("  columns:")
    pprint(flights_df.columns.tolist(), width=100, compact=True, indent=4)
    print("")

def determine_percent_flights(
    flights_df: pd.DataFrame,
    carrier_info: pd.DataFrame,
    airlines_list: pd.DataFrame,
) -> tuple[pd.Series, np.ndarray]:
    """
    Identify 'large' airlines based on an average-percent rule and return:
      (keep_mask, large_airlines_array)

    Expects snake_case columns:
      flights_df: dot_id_reporting_airline, year, month
      airlines_list: dot_id_reporting_airline
      carrier_info: airline_id (optional; used only for optional diagnostics)
    """
    percent_flights = (
        flights_df["dot_id_reporting_airline"]
        .value_counts(normalize=True)
        .mul(100)
        .rename("percent")
        .to_frame()
    )

    yearmonth = flights_df["year"] + flights_df["month"] / 12

    span = (
        pd.DataFrame(
            {
                "dot_id_reporting_airline": flights_df["dot_id_reporting_airline"].to_numpy(),
                "yearmonth": yearmonth.to_numpy(),
            }
        )
        .groupby("dot_id_reporting_airline")["yearmonth"]
        .agg(["min", "max"])
    )

    percent_flights["years_in_sample"] = (span["max"] - span["min"] + 1 / 12).values
    percent_flights["average_percent"] = percent_flights["percent"] * 16 / percent_flights["years_in_sample"]

    percent_flights = percent_flights.reset_index().rename(columns={"dot_id_reporting_airline": "airline_id"})

    large_airlines = percent_flights.loc[percent_flights["average_percent"] > 1, "airline_id"].to_numpy()

    # Optional diagnostics (assign if you want to use it)
    # pf_diag = (percent_flights
    #            .merge(carrier_info, on="airline_id", how="left")
    #            .sort_values("average_percent"))

    keep_large_airlines = (
        flights_df["dot_id_reporting_airline"].isin(large_airlines)
        & flights_df["dot_id_reporting_airline"].isin(airlines_list["dot_id_reporting_airline"])
    )

    return keep_large_airlines, large_airlines


def print_selection_criteria_flights(
    num_total_flights,
    subsample_num_flights,
    keep_large_airports,
    keep_large_airlines,
) -> None:
    """
    Print a short summary of how many flights are kept/dropped by sample-selection filters.

    Parameters
    ----------
    num_total_flights
        Total number of eligible flights in the full dataset (before subsampling).
    subsample_num_flights
        Number of flights in the random subsample (before applying filters).
    keep_large_airports
        Boolean mask over the subsample indicating flights on routes where both origin and
        destination airports meet the airport inclusion criteria.
    keep_large_airlines
        Boolean mask over the subsample indicating flights operated by airlines that meet
        the airline inclusion criteria.

    Notes
    -----
    Percentages are computed relative to the subsample size (subsample_num_flights).
    """
    # Normalize to plain Python ints for clean formatted printing.
    n_total = int(num_total_flights)
    n_sub = int(subsample_num_flights)

    # Count how many subsample flights pass each filter.
    n_airport_keep = int(keep_large_airports.sum())
    n_airline_keep = int(keep_large_airlines.sum())
    n_keep_both = int((keep_large_airlines & keep_large_airports).sum())

    # Print counts (with thousands separators) and shares of the subsample.
    print(f"{'Total number of flights':<41} {n_total:>12,}")
    print(f"{'Initial observations (2.5%)':<41} {n_sub:>12,}")

    print(f"{'Flights from airports with 10+ / day':<41} {n_airport_keep:>12,}  ({n_airport_keep / n_sub:>6.1%})")
    print(f"{'Flights from airlines with >1% of flights':<41} {n_airline_keep:>12,}  ({n_airline_keep / n_sub:>6.1%})")
    print(f"{'Flights kept (both filters)':<41} {n_keep_both:>12,}  ({n_keep_both / n_sub:>6.1%})")
    print("")



def add_tail_numbers(flights_df: pd.DataFrame, db_source: str) -> pd.DataFrame:
    """
    Add aircraft seat capacity (num_seats) to the flights dataset using tail_number_id.

    This function reads the tail number lookup table from the SQLite database and
    left-joins it onto the flight-level DataFrame. Flights with missing tail numbers
    or unmatched IDs will have num_seats as NA.

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level data containing a 'tail_number_id' column.
    db_source : str
        Path to the SQLite database.

    Returns
    -------
    pd.DataFrame
        flights_df with an additional 'num_seats' column.
    """
    # Load tail-number seat capacity lookup.
    with sqlite3.connect(db_source) as conn:
        tail_num_seats = pd.read_sql_query(
            """
            SELECT
                id AS tail_number_id,
                num_seats
            FROM tail_num_seats
            """,
            conn,
        )

    # Left join so all flights are preserved; unmatched tail numbers produce missing num_seats.
    flights_df = flights_df.merge(tail_num_seats, how="left", on="tail_number_id")
    return flights_df


def add_segment(
    flights_df: pd.DataFrame,
    db_source: str,
    large_airlines: pd.Series,
    airports_to_analyze: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge segment-level variables (e.g., load factor) onto the flight-level dataset.

    The segment table is filtered to:
      - airlines in `large_airlines`
      - routes where both origin and destination airports are in `airports_to_analyze`

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level data with keys:
        ['dot_id_reporting_airline', 'origin_airport_id', 'dest_airport_id', 'year', 'month'].
    db_source : str
        Path to the SQLite database.
    large_airlines : pd.Series or array-like
        Airline IDs to keep (typically produced by the airline selection step).
    airports_to_analyze : pd.DataFrame
        DataFrame containing the airports to include. Must contain an 'origin_airport_id' column.

    Returns
    -------
    pd.DataFrame
        flights_df with segment variables merged in (left join).
    """
    # Load segment table with standardized column names.
    with sqlite3.connect(db_source) as conn:
        segment = pd.read_sql_query(
            """
            SELECT
                Year              AS year,
                Month             AS month,
                Airline_Id        AS dot_id_reporting_airline,
                Origin_Airport_Id AS origin_airport_id,
                Dest_Airport_Id   AS dest_airport_id,
                Loadfactor        AS load_factor
            FROM segment
            """,
            conn,
        )

    # Apply the same airline and airport inclusion criteria to the segment data.
    segment_large_airline = segment["dot_id_reporting_airline"].isin(large_airlines)
    segment_large_airports = (
        segment["origin_airport_id"].isin(airports_to_analyze["origin_airport_id"])
        & segment["dest_airport_id"].isin(airports_to_analyze["origin_airport_id"])
    )
    segment = segment.loc[segment_large_airline & segment_large_airports].copy()

    # Left-join: keep all flights; segment variables are missing if no match is found.
    flights_df = flights_df.merge(
        segment,
        how="left",
        on=["dot_id_reporting_airline", "origin_airport_id", "dest_airport_id", "year", "month"],
    )
    return flights_df


def add_market_structure(flights_df: pd.DataFrame, db_source: str) -> pd.DataFrame:
    """
    Add airport-level market structure measures (hub size and HHI) for both origin and destination.

    This function:
      1) Loads origin-airport hub size from `airport_market_info`
      2) Loads origin-airport HHI (and lagged HHI) from `new_HHI`
      3) Merges these measures onto flights by (airport_id, year, month) for the origin airport
      4) Reuses the same airport-level table, renaming columns to represent the destination airport,
         and merges again by (dest_airport_id, year, month)

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level data containing at least:
        ['origin_airport_id', 'dest_airport_id', 'year', 'month'].
    db_source : str
        Path to the SQLite database.

    Returns
    -------
    pd.DataFrame
        flights_df with additional columns for origin and destination market structure.
    """
    # Load airport-level hub size and HHI measures (keyed by airport, year, month).
    with sqlite3.connect(db_source) as conn:
        market_hub_size = pd.read_sql_query(
            """
            SELECT
                OriginAirportID AS origin_airport_id,
                Year            AS year,
                Month           AS month,
                HubSize         AS airport_hub_size_origin
            FROM airport_market_info
            """,
            conn,
        )
        market_lagged_hhi = pd.read_sql_query(
            """
            SELECT
                OriginAirportID AS origin_airport_id,
                Year            AS year,
                Month           AS month,
                HHI             AS hhi_origin,
                HHI_lagged      AS hhi_origin_lagged
            FROM new_HHI
            """,
            conn,
        )

    # Combine hub size + HHI into a single origin-airport market structure table.
    market_origin = market_hub_size.merge(
        market_lagged_hhi,
        on=["origin_airport_id", "year", "month"],
        how="inner",
    )

    # Merge origin-airport market structure onto flights.
    flights_df = flights_df.merge(
        market_origin,
        how="left",
        on=["origin_airport_id", "year", "month"],
    )

    # Reuse the same airport-level measures for the destination airport by renaming columns.
    market_dest = market_origin.rename(
        columns={
            "origin_airport_id": "dest_airport_id",
            "hhi_origin": "hhi_dest",
            "hhi_origin_lagged": "hhi_dest_lagged",
            "airport_hub_size_origin": "airport_hub_size_dest",
        }
    )

    # Merge destination-airport market structure onto flights.
    flights_df = flights_df.merge(
        market_dest,
        how="left",
        on=["dest_airport_id", "year", "month"],
    )

    return flights_df



def misspecification_test(flights_df: pd.DataFrame, db_source: str) -> pd.DataFrame:
    """
    Add additional airline-airport market structure variables used for misspecification tests.

    This function merges (airline, airport, year, month)-level variables onto the flight-level data
    for both the origin and destination airports. The added variables include market share terms,
    squared terms, HHI-minus terms, and lagged versions (as available in the source tables).

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level data containing merge keys:
        ['origin_airport_id', 'dest_airport_id', 'dot_id_reporting_airline', 'year', 'month'].
    db_source : str
        Path to the SQLite database.

    Returns
    -------
    pd.DataFrame
        flights_df with additional origin- and destination-side misspecification-test variables.
    """
    # Load airline-airport market share and hub-size information (origin-side keys).
    with sqlite3.connect(db_source) as conn:
        airline_market_origin = pd.read_sql_query(
            """
            SELECT
                OriginAirportID          AS origin_airport_id,
                DOT_ID_Reporting_Airline AS dot_id_reporting_airline,
                Year                     AS year,
                Month                    AS month,
                HubSize                  AS airline_hub_size_origin
            FROM airport_airline_market_info
            """,
            conn,
        )

        # Load additional market structure measures (including squared and lagged terms).
        airline_market_structure = pd.read_sql_query(
            """
            SELECT
                OriginAirportID          AS origin_airport_id,
                DOT_ID_Reporting_Airline AS dot_id_reporting_airline,
                Year                     AS year,
                Month                    AS month,
                market_share             AS market_share_origin,
                market_share_squared     AS market_share_squared_origin,
                HHIminus                 AS hhi_minus_origin,
                market_share_lagged      AS market_share_origin_lagged,
                market_share_squared_lagged AS market_share_squared_origin_lagged,
                HHI_minus_lagged         AS hhi_minus_origin_lagged
            FROM new_market_share
            """,
            conn,
        )

    # Combine the two origin-side tables into a single (airline, origin_airport, year, month) table.
    airline_market_origin = airline_market_origin.merge(
        airline_market_structure,
        on=["origin_airport_id", "dot_id_reporting_airline", "year", "month"],
        how="inner",
    )

    # Merge origin-side measures onto flights.
    flights_df = flights_df.merge(
        airline_market_origin,
        how="left",
        on=["origin_airport_id", "dot_id_reporting_airline", "year", "month"],
    )

    # Reuse the same measures for destination by renaming origin columns to destination columns.
    airline_market_destination = airline_market_origin.rename(
        columns={
            "origin_airport_id": "dest_airport_id",
            "market_share_origin": "market_share_dest",
            "market_share_squared_origin": "market_share_squared_dest",
            "hhi_minus_origin": "hhi_minus_dest",
            "airline_hub_size_origin": "airline_hub_size_dest",
            "market_share_origin_lagged": "market_share_dest_lagged",
            "market_share_squared_origin_lagged": "market_share_squared_dest_lagged",
            "hhi_minus_origin_lagged": "hhi_minus_dest_lagged",
        }
    )

    # Merge destination-side measures onto flights.
    flights_df = flights_df.merge(
        airline_market_destination,
        how="left",
        on=["dest_airport_id", "dot_id_reporting_airline", "year", "month"],
    )

    return flights_df


def add_metro_level_statistics(flights_df: pd.DataFrame, db_source: str) -> pd.DataFrame:
    """
    Add metro-area population and GDP-per-capita measures for both origin and destination airports.

    The CBSA table is stored in wide format (separate columns for each year). This function:
      1) Loads CBSA population and GDP columns from SQLite.
      2) Reshapes GDP and population to long format by year.
      3) Computes GDP per capita (GDP / population).
      4) Fills missing GDP-per-capita values by imputing the mean within each year (across airports).
      5) Merges metro population and GDP-per-capita onto flights by (airport_id, year) for origin
         and again for destination.

    Notes
    -----
    - The imputation step is intended to avoid missing values in downstream regressions.
    - The function assumes that GDP and population series align by (origin_airport_id, year)
      after melting; this holds given consistent construction of the wide CBSA table.

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level data containing at least:
        ['origin_airport_id', 'dest_airport_id', 'year'].
    db_source : str
        Path to the SQLite database.

    Returns
    -------
    pd.DataFrame
        flights_df with added columns:
        metro_pop_origin, metro_gdp_capita_origin, metro_pop_dest, metro_gdp_capita_dest.
    """
    # Load CBSA table (wide format with year-specific columns).
    with sqlite3.connect(db_source) as conn:
        cbsa = pd.read_sql_query(
            """
            SELECT
                airport_id AS origin_airport_id,
                gdp_missing,
                POPESTIMATE2000 AS pop_estimate_2000,
                POPESTIMATE2001 AS pop_estimate_2001,
                POPESTIMATE2002 AS pop_estimate_2002,
                POPESTIMATE2003 AS pop_estimate_2003,
                POPESTIMATE2004 AS pop_estimate_2004,
                POPESTIMATE2005 AS pop_estimate_2005,
                POPESTIMATE2006 AS pop_estimate_2006,
                POPESTIMATE2007 AS pop_estimate_2007,
                POPESTIMATE2008 AS pop_estimate_2008,
                POPESTIMATE2009 AS pop_estimate_2009,
                POPESTIMATE2010 AS pop_estimate_2010,
                POPESTIMATE2011 AS pop_estimate_2011,
                POPESTIMATE2012 AS pop_estimate_2012,
                POPESTIMATE2013 AS pop_estimate_2013,
                POPESTIMATE2014 AS pop_estimate_2014,
                POPESTIMATE2015 AS pop_estimate_2015,
                POPESTIMATE2016 AS pop_estimate_2016,
                POPESTIMATE2017 AS pop_estimate_2017,
                POPESTIMATE2018 AS pop_estimate_2018,
                POPESTIMATE2019 AS pop_estimate_2019,
                gdp_2001,
                gdp_2002,
                gdp_2003,
                gdp_2004,
                gdp_2005,
                gdp_2006,
                gdp_2007,
                gdp_2008,
                gdp_2009,
                gdp_2010,
                gdp_2011,
                gdp_2012,
                gdp_2013,
                gdp_2014,
                gdp_2015,
                gdp_2016,
                gdp_2017,
                gdp_2018,
                gdp_2019
            FROM cbsa
            """,
            conn,
        )

    # --- GDP: wide -> long (origin_airport_id, year, MetroGDP) ---
    cbsa_gdp = cbsa[
        [
            "origin_airport_id",
            "gdp_2001", "gdp_2002", "gdp_2003", "gdp_2004",
            "gdp_2005", "gdp_2006", "gdp_2007", "gdp_2008", "gdp_2009", "gdp_2010",
            "gdp_2011", "gdp_2012", "gdp_2013", "gdp_2014", "gdp_2015", "gdp_2016",
            "gdp_2017", "gdp_2018", "gdp_2019",
        ]
    ]
    cbsa_gdp = pd.melt(
        cbsa_gdp,
        id_vars=["origin_airport_id"],
        value_vars=[
            "gdp_2001", "gdp_2002", "gdp_2003", "gdp_2004",
            "gdp_2005", "gdp_2006", "gdp_2007", "gdp_2008", "gdp_2009", "gdp_2010",
            "gdp_2011", "gdp_2012", "gdp_2013", "gdp_2014", "gdp_2015", "gdp_2016",
            "gdp_2017", "gdp_2018", "gdp_2019",
        ],
        var_name="year",
        value_name="metro_gdp",
    )
    cbsa_gdp["year"] = cbsa_gdp["year"].str[-4:].astype(int)

    # --- Population: wide -> long (origin_airport_id, year, metro_pop) ---
    cbsa_pop = cbsa[
        [
            "origin_airport_id",
            "pop_estimate_2000",
            "pop_estimate_2001", "pop_estimate_2002", "pop_estimate_2003",
            "pop_estimate_2004", "pop_estimate_2005", "pop_estimate_2006",
            "pop_estimate_2007", "pop_estimate_2008", "pop_estimate_2009",
            "pop_estimate_2010", "pop_estimate_2011", "pop_estimate_2012",
            "pop_estimate_2013", "pop_estimate_2014", "pop_estimate_2015",
            "pop_estimate_2016", "pop_estimate_2017", "pop_estimate_2018",
            "pop_estimate_2019",
        ]
    ]
    cbsa_pop = pd.melt(
        cbsa_pop,
        id_vars=["origin_airport_id"],
        value_vars=[
            "pop_estimate_2001", "pop_estimate_2002", "pop_estimate_2003",
            "pop_estimate_2004", "pop_estimate_2005", "pop_estimate_2006", "pop_estimate_2007",
            "pop_estimate_2008", "pop_estimate_2009", "pop_estimate_2010", "pop_estimate_2011",
            "pop_estimate_2012", "pop_estimate_2013", "pop_estimate_2014", "pop_estimate_2015",
            "pop_estimate_2016", "pop_estimate_2017", "pop_estimate_2018", "pop_estimate_2019",
        ],
        var_name="year",
        value_name="metro_pop",
    )

    cbsa_pop["year"] = cbsa_pop["year"].str[-4:].astype(int)

    # Compute GDP per capita (relies on both long tables being aligned by airport-year).

    cbsa_gdp = cbsa_gdp.merge(cbsa_pop, on=['origin_airport_id', 'year'], how='left')
    cbsa_gdp['gdp_capita'] = cbsa_gdp['metro_gdp'] / cbsa_gdp['metro_pop']

    cbsa_gdp['gdp_capita'] = cbsa_gdp["gdp_capita"] = cbsa_gdp["gdp_capita"].fillna(
        cbsa_gdp.groupby("year")["gdp_capita"].transform("mean")
    )

    cbsa_gdp = (
        cbsa_gdp[['origin_airport_id', 'year', 'metro_pop', 'gdp_capita']]
            .rename(columns={
                "gdp_capita": "metro_gdp_capita_origin",
                "metro_pop": "metro_pop_origin",
            })
    )

    flights_df = flights_df.merge(cbsa_gdp, how="left", on=["origin_airport_id", "year"])

    # Merge the same variables for destination airport by renaming IDs/columns.
    cbsa_gdp = cbsa_gdp.rename(
        columns={
            "origin_airport_id": "dest_airport_id",
            "metro_pop_origin": "metro_pop_dest",
            "metro_gdp_capita_origin": "metro_gdp_capita_dest",
        }
    )
    flights_df = flights_df.merge(cbsa_gdp, how="left", on=["dest_airport_id", "year"])

    return flights_df


def get_depart_datetime(flights_df: pd.DataFrame) -> pd.DataFrame:
    """
    Construct a pandas datetime column from flight date fields and scheduled departure time.

    Uses (year, month, day_of_month) plus `crs_dep_time` (scheduled departure time in HHMM
    format, often stored as an int like 5, 930, 1230). Invalid or missing values are coerced
    to NA.

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level data containing: year, month, day_of_month, crs_dep_time.

    Returns
    -------
    pd.DataFrame
        The same DataFrame with an added `DateTime` column.
    """
    # Build the calendar date from separate year/month/day columns.
    date = pd.to_datetime(
        {"year": flights_df["year"], "month": flights_df["month"], "day": flights_df["day_of_month"]},
        errors="coerce",
    )

    # Parse scheduled departure time as HHMM, padding with leading zeros (e.g., 5 -> "0005").
    t_num = pd.to_numeric(flights_df["crs_dep_time"], errors="coerce")
    t_str = t_num.astype("Int64").astype("string").str.zfill(4)

    # Split HHMM into hours and minutes.
    hh = pd.to_numeric(t_str.str.slice(0, 2), errors="coerce")
    mm = pd.to_numeric(t_str.str.slice(2, 4), errors="coerce")

    # Combine date + time into a single datetime.
    flights_df["DateTime"] = date + pd.to_timedelta(hh, unit="h") + pd.to_timedelta(mm, unit="m")

    return flights_df



def add_husize_dummies(flights_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create hub-size dummy variables for airport and airline hub categories.

    The input columns contain integer hub-size categories (e.g., 0–3). This function converts
    them into one-hot indicator columns for:
      - airport hub size at origin and destination
      - airline hub size at origin and destination

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level data containing hub-size category columns:
        airport_hub_size_origin, airline_hub_size_origin, airport_hub_size_dest, airline_hub_size_dest.

    Returns
    -------
    pd.DataFrame
        flights_df with additional dummy columns appended.
    """
    # One-hot encode hub-size categories and rename to readable indicator names.
    airport_origin = (
        pd.get_dummies(flights_df["airport_hub_size_origin"]).astype('Int8')
        .rename(
            columns={
                0: "non_hub_airport_origin",
                1: "small_hub_airport_origin",
                2: "medium_hub_airport_origin",
                3: "large_hub_airport_origin",
            }
        )
    )

    airline_origin = (
        pd.get_dummies(flights_df["airline_hub_size_origin"]).astype('Int8')
        .rename(
            columns={
                0: "non_hub_airline_origin",
                1: "small_hub_airline_origin",
                2: "medium_hub_airline_origin",
                3: "large_hub_airline_origin",
            }
        )
    )

    airport_dest = (
        pd.get_dummies(flights_df["airport_hub_size_dest"]).astype('Int8')
        .rename(
            columns={
                0: "non_hub_airport_dest",
                1: "small_hub_airport_dest",
                2: "medium_hub_airport_dest",
                3: "large_hub_airport_dest",
            }
        )
    )

    airline_dest = (
        pd.get_dummies(flights_df["airline_hub_size_dest"]).astype('Int8')
        .rename(
            columns={
                0: "non_hub_airline_dest",
                1: "small_hub_airline_dest",
                2: "medium_hub_airline_dest",
                3: "large_hub_airline_dest",
            }
        )
    )

    # Append dummy columns to the main DataFrame.
    flights_df = pd.concat([flights_df, airport_origin, airline_origin, airport_dest, airline_dest], axis=1)
    return flights_df


def add_hubsize_interactions(flights_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create interaction variables between airline hub-size dummies and market-structure measures.

    This function multiplies hub-size indicator variables (non/small/medium/large) by:
      - market share (ms)
      - HHI (market concentration)
      - market share squared (ms2)
      - residual concentration (hhi_minus)

    Interactions are created for both origin and destination markets.

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level data containing hub-size dummies and the relevant market-structure columns.

    Returns
    -------
    pd.DataFrame
        flights_df with added interaction columns.
    """
    # ---- Market share interactions ----
    # Origin
    flights_df["non_hub_airline_ms_origin"] = flights_df["non_hub_airline_origin"] * flights_df["market_share_origin"]
    flights_df["small_hub_airline_ms_origin"] = flights_df["small_hub_airline_origin"] * flights_df["market_share_origin"]
    flights_df["medium_hub_airline_ms_origin"] = flights_df["medium_hub_airline_origin"] * flights_df["market_share_origin"]
    flights_df["large_hub_airline_ms_origin"] = flights_df["large_hub_airline_origin"] * flights_df["market_share_origin"]

    # Destination
    flights_df["non_hub_airline_ms_dest"] = flights_df["non_hub_airline_dest"] * flights_df["market_share_dest"]
    flights_df["small_hub_airline_ms_dest"] = flights_df["small_hub_airline_dest"] * flights_df["market_share_dest"]
    flights_df["medium_hub_airline_ms_dest"] = flights_df["medium_hub_airline_dest"] * flights_df["market_share_dest"]
    flights_df["large_hub_airline_ms_dest"] = flights_df["large_hub_airline_dest"] * flights_df["market_share_dest"]

    # ---- HHI (market concentration) interactions ----
    # Origin
    flights_df["non_hub_airline_hhi_origin"] = flights_df["non_hub_airline_origin"] * flights_df["hhi_origin"]
    flights_df["small_hub_airline_hhi_origin"] = flights_df["small_hub_airline_origin"] * flights_df["hhi_origin"]
    flights_df["medium_hub_airline_hhi_origin"] = flights_df["medium_hub_airline_origin"] * flights_df["hhi_origin"]
    flights_df["large_hub_airline_hhi_origin"] = flights_df["large_hub_airline_origin"] * flights_df["hhi_origin"]

    # Destination
    flights_df["non_hub_airline_hhi_dest"] = flights_df["non_hub_airline_dest"] * flights_df["hhi_dest"]
    flights_df["small_hub_airline_hhi_dest"] = flights_df["small_hub_airline_dest"] * flights_df["hhi_dest"]
    flights_df["medium_hub_airline_hhi_dest"] = flights_df["medium_hub_airline_dest"] * flights_df["hhi_dest"]
    flights_df["large_hub_airline_hhi_dest"] = flights_df["large_hub_airline_dest"] * flights_df["hhi_dest"]

    # ---- Market share squared interactions (misspecification tests) ----
    # Origin
    flights_df["non_hub_airline_ms2_origin"] = flights_df["non_hub_airline_origin"] * flights_df["market_share_squared_origin"]
    flights_df["small_hub_airline_ms2_origin"] = flights_df["small_hub_airline_origin"] * flights_df["market_share_squared_origin"]
    flights_df["medium_hub_airline_ms2_origin"] = flights_df["medium_hub_airline_origin"] * flights_df["market_share_squared_origin"]
    flights_df["large_hub_airline_ms2_origin"] = flights_df["large_hub_airline_origin"] * flights_df["market_share_squared_origin"]

    # Destination
    flights_df["non_hub_airline_ms2_dest"] = flights_df["non_hub_airline_dest"] * flights_df["market_share_squared_dest"]
    flights_df["small_hub_airline_ms2_dest"] = flights_df["small_hub_airline_dest"] * flights_df["market_share_squared_dest"]
    flights_df["medium_hub_airline_ms2_dest"] = flights_df["medium_hub_airline_dest"] * flights_df["market_share_squared_dest"]
    flights_df["large_hub_airline_ms2_dest"] = flights_df["large_hub_airline_dest"] * flights_df["market_share_squared_dest"]

    # ---- Residual concentration interactions (HHI minus own-share component) ----
    # Origin
    flights_df["non_hub_airline_hhi_minus_origin"] = flights_df["non_hub_airline_origin"] * flights_df["hhi_minus_origin"]
    flights_df["small_hub_airline_hhi_minus_origin"] = flights_df["small_hub_airline_origin"] * flights_df["hhi_minus_origin"]
    flights_df["medium_hub_airline_hhi_minus_origin"] = flights_df["medium_hub_airline_origin"] * flights_df["hhi_minus_origin"]
    flights_df["large_hub_airline_hhi_minus_origin"] = flights_df["large_hub_airline_origin"] * flights_df["hhi_minus_origin"]

    # Destination
    flights_df["non_hub_airline_hhi_minus_dest"] = flights_df["non_hub_airline_dest"] * flights_df["hhi_minus_dest"]
    flights_df["small_hub_airline_hhi_minus_dest"] = flights_df["small_hub_airline_dest"] * flights_df["hhi_minus_dest"]
    flights_df["medium_hub_airline_hhi_minus_dest"] = flights_df["medium_hub_airline_dest"] * flights_df["hhi_minus_dest"]
    flights_df["large_hub_airline_hhi_minus_dest"] = flights_df["large_hub_airline_dest"] * flights_df["hhi_minus_dest"]

    return flights_df


def add_lagged_hubsize_interactions(flights_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create lagged interaction variables between airline hub-size dummies and lagged market-structure measures.

    This mirrors `add_hubsize_interactions`, but uses lagged versions of:
      - market share
      - HHI
      - market share squared
      - residual concentration (HHI minus)

    Interactions are created for both origin and destination markets.

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level data containing hub-size dummies and the lagged market-structure columns.

    Returns
    -------
    pd.DataFrame
        flights_df with added lagged interaction columns.
    """
    # ---- Lagged market share interactions ----
    # Origin
    flights_df["l_non_hub_airline_ms_origin"] = flights_df["non_hub_airline_origin"] * flights_df["market_share_origin_lagged"]
    flights_df["l_small_hub_airline_ms_origin"] = flights_df["small_hub_airline_origin"] * flights_df["market_share_origin_lagged"]
    flights_df["l_medium_hub_airline_ms_origin"] = flights_df["medium_hub_airline_origin"] * flights_df["market_share_origin_lagged"]
    flights_df["l_large_hub_airline_ms_origin"] = flights_df["large_hub_airline_origin"] * flights_df["market_share_origin_lagged"]

    # Destination
    flights_df["l_non_hub_airline_ms_dest"] = flights_df["non_hub_airline_dest"] * flights_df["market_share_dest_lagged"]
    flights_df["l_small_hub_airline_ms_dest"] = flights_df["small_hub_airline_dest"] * flights_df["market_share_dest_lagged"]
    flights_df["l_medium_hub_airline_ms_dest"] = flights_df["medium_hub_airline_dest"] * flights_df["market_share_dest_lagged"]
    flights_df["l_large_hub_airline_ms_dest"] = flights_df["large_hub_airline_dest"] * flights_df["market_share_dest_lagged"]

    # ---- Lagged HHI (market concentration) interactions ----
    # Origin
    flights_df["l_non_hub_airline_hhi_origin"] = flights_df["non_hub_airline_origin"] * flights_df["hhi_origin_lagged"]
    flights_df["l_small_hub_airline_hhi_origin"] = flights_df["small_hub_airline_origin"] * flights_df["hhi_origin_lagged"]
    flights_df["l_medium_hub_airline_hhi_origin"] = flights_df["medium_hub_airline_origin"] * flights_df["hhi_origin_lagged"]
    flights_df["l_large_hub_airline_hhi_origin"] = flights_df["large_hub_airline_origin"] * flights_df["hhi_origin_lagged"]

    # Destination
    flights_df["l_non_hub_airline_hhi_dest"] = flights_df["non_hub_airline_dest"] * flights_df["hhi_dest_lagged"]
    flights_df["l_small_hub_airline_hhi_dest"] = flights_df["small_hub_airline_dest"] * flights_df["hhi_dest_lagged"]
    flights_df["l_medium_hub_airline_hhi_dest"] = flights_df["medium_hub_airline_dest"] * flights_df["hhi_dest_lagged"]
    flights_df["l_large_hub_airline_hhi_dest"] = flights_df["large_hub_airline_dest"] * flights_df["hhi_dest_lagged"]

    # ---- Lagged market share squared interactions (misspecification tests) ----
    # Origin
    flights_df["l_non_hub_airline_ms2_origin"] = flights_df["non_hub_airline_origin"] * flights_df["market_share_squared_origin_lagged"]
    flights_df["l_small_hub_airline_ms2_origin"] = flights_df["small_hub_airline_origin"] * flights_df["market_share_squared_origin_lagged"]
    flights_df["l_medium_hub_airline_ms2_origin"] = flights_df["medium_hub_airline_origin"] * flights_df["market_share_squared_origin_lagged"]
    flights_df["l_large_hub_airline_ms2_origin"] = flights_df["large_hub_airline_origin"] * flights_df["market_share_squared_origin_lagged"]

    # Destination
    flights_df["l_non_hub_airline_ms2_dest"] = flights_df["non_hub_airline_dest"] * flights_df["market_share_squared_dest_lagged"]
    flights_df["l_small_hub_airline_ms2_dest"] = flights_df["small_hub_airline_dest"] * flights_df["market_share_squared_dest_lagged"]
    flights_df["l_medium_hub_airline_ms2_dest"] = flights_df["medium_hub_airline_dest"] * flights_df["market_share_squared_dest_lagged"]
    flights_df["l_large_hub_airline_ms2_dest"] = flights_df["large_hub_airline_dest"] * flights_df["market_share_squared_dest_lagged"]

    # ---- Lagged residual concentration interactions (HHI minus) ----
    # Origin
    flights_df["l_non_hub_airline_hhi_minus_origin"] = flights_df["non_hub_airline_origin"] * flights_df["hhi_minus_origin_lagged"]
    flights_df["l_small_hub_airline_hhi_minus_origin"] = flights_df["small_hub_airline_origin"] * flights_df["hhi_minus_origin_lagged"]
    flights_df["l_medium_hub_airline_hhi_minus_origin"] = flights_df["medium_hub_airline_origin"] * flights_df["hhi_minus_origin_lagged"]
    flights_df["l_large_hub_airline_hhi_minus_origin"] = flights_df["large_hub_airline_origin"] * flights_df["hhi_minus_origin_lagged"]

    # Destination
    flights_df["l_non_hub_airline_hhi_minus_dest"] = flights_df["non_hub_airline_dest"] * flights_df["hhi_minus_dest_lagged"]
    flights_df["l_small_hub_airline_hhi_minus_dest"] = flights_df["small_hub_airline_dest"] * flights_df["hhi_minus_dest_lagged"]
    flights_df["l_medium_hub_airline_hhi_minus_dest"] = flights_df["medium_hub_airline_dest"] * flights_df["hhi_minus_dest_lagged"]
    flights_df["l_large_hub_airline_hhi_minus_dest"] = flights_df["large_hub_airline_dest"] * flights_df["hhi_minus_dest_lagged"]

    return flights_df



def create_merger_ids(flights_df: pd.DataFrame, db_source: str) -> pd.DataFrame:
    """
    Create post-merger airline identifiers by collapsing merged carriers after a cutoff date.

    The `merger_cutoff` table is expected to contain rows with:
      - Continue_Airline: the surviving carrier ID
      - Merged_Airline: the absorbed carrier ID
      - YearMonth: cutoff (as a YearMonth numeric value) after which the two carriers are treated as one

    For each merger rule, flights operated by either carrier *after* the cutoff are assigned a
    synthetic airline id (starting at 99999 and decrementing) to ensure each merger event maps
    to a unique identifier.

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level data containing at least: year, month, dot_id_reporting_airline.
    db_source : str
        Path to the SQLite database.

    Returns
    -------
    pd.DataFrame
        flights_df with:
          - YearMonth (constructed as year + (month-1)/12)
          - uniquecarrier_old (original airline id preserved)
          - dot_id_reporting_airline overwritten with synthetic ids post-merger
    """
    # Load merger cutoff rules (sorted so later cutoffs are applied first).
    with sqlite3.connect(db_source) as conn:
        merger_cutoff = pd.read_sql_query(
            "SELECT * FROM merger_cutoff ORDER BY -YearMonth",
            conn,
        )

    # Construct a continuous YearMonth index to compare against merger cutoff dates.
    flights_df["YearMonth"] = flights_df["year"] + (flights_df["month"] - 1) / 12

    # Preserve the original carrier id before applying merger recodes.
    flights_df["uniquecarrier_old"] = flights_df["dot_id_reporting_airline"]

    # Recode post-merger carrier ids to a synthetic id (unique per merger rule).
    new_id = 99999
    for continue_id, merged_id, cutoff_yearmonth in zip(
        merger_cutoff["Continue_Airline"],
        merger_cutoff["Merged_Airline"],
        merger_cutoff["YearMonth"],
    ):
        # Flights by either carrier after the cutoff are treated as the merged entity.
        replace_ind = (
            flights_df["dot_id_reporting_airline"].isin([continue_id, merged_id])
            & (flights_df["YearMonth"] > cutoff_yearmonth)
        )
        flights_df.loc[replace_ind, "dot_id_reporting_airline"] = new_id
        new_id -= 1  # decrement to keep synthetic ids unique across merger rules

    return flights_df


def analyze_weather(weather_name: str, db_source: str) -> pd.DataFrame:
    """
    Load and clean hourly weather data for a single airport, and construct weather controls.

    This function reads from a per-airport table named `weather_{weather_name}` and produces:
      - precipitation indicators (rain/snow and trace variants, based on freezing threshold)
      - wind speed, wind speed squared, wind gust speed, and a gust dummy
      - temperature bins in Celsius as a set of dummy variables

    Parameters
    ----------
    weather_name : str
        Airport identifier suffix used in the table name `weather_{weather_name}`.
        (Typically an airport id consistent with flights_df['origin_airport_id'] grouping.)
    db_source : str
        Path to the SQLite database.

    Returns
    -------
    pd.DataFrame
        Cleaned weather DataFrame with engineered variables, sorted by DateTime.
    """
    # Labels produced by `pd.cut(...).astype(str)` for the temperature bins below.
    col_names = [
        "(-100.001, -10.0]",
        "(-10.0, 0.0]",
        "(0.0, 10.0]",
        "(10.0, 20.0]",
        "(20.0, 30.0]",
        "(30.0, 40.0]",
        "(40.0, 100.0]",
    ]
    dummy_names = [
        "temp_n_infty_n_10",
        "temp_n_10_0",
        "temp_0_10",
        "temp_10_20",
        "temp_20_30",
        "temp_30_40",
        "temp_40_infty",
    ]

    # Load raw hourly weather data for this airport.
    with sqlite3.connect(db_source) as conn:
        weather_df = pd.read_sql_query(
            f"""
            SELECT
                DATE AS DateTime,
                HourlyDryBulbTemperature AS temperature,
                HourlyPrecipitation AS precipitation,
                Trace AS trace,
                HourlyWindGustSpeed AS wind_gust_speed,
                HourlyWindSpeed AS wind_speed
            FROM weather_{weather_name}
            """,
            conn,
        )

    # Ensure time ordering for merge_asof downstream.
    weather_df["DateTime"] = pd.to_datetime(weather_df["DateTime"])
    weather_df = weather_df.sort_values(by=["DateTime"])

    # Precipitation type indicators: use 32F threshold to split rain vs snow.
    is_freezing = weather_df["temperature"] <= 32
    weather_df["is_raining"] = (~is_freezing & (weather_df["precipitation"] > 0)).astype(int)
    weather_df["is_snowing"] = (is_freezing & (weather_df["precipitation"] > 0)).astype(int)
    weather_df["trace_rain"] = (~is_freezing & (weather_df["trace"])).astype(int)
    weather_df["trace_snow"] = (is_freezing & (weather_df["trace"])).astype(int)

    # Coerce numeric wind variables; treat missing gust as zero (no gust reported).
    weather_df["wind_speed"] = pd.to_numeric(weather_df["wind_speed"], errors="coerce")
    weather_df["wind_speed_squared"] = weather_df["wind_speed"] ** 2
    weather_df["wind_gust_speed"] = pd.to_numeric(weather_df["wind_gust_speed"].fillna("0"), errors="coerce")

    # Drop rows missing key controls (keeps downstream regressors complete).
    weather_df = weather_df.dropna(
        how="any",
        subset=["wind_speed", "precipitation", "temperature", "wind_gust_speed"],
    )

    # Cast to int after cleaning (matches typical regression-control expectations).
    weather_df["wind_speed"] = weather_df["wind_speed"].astype(int)
    weather_df["wind_speed_squared"] = weather_df["wind_speed_squared"].astype(int)
    weather_df["wind_gust_speed"] = weather_df["wind_gust_speed"].astype(int)
    weather_df["wind_gust_dummy"] = (weather_df["wind_gust_speed"] > 0).astype(int)

    # Temperature bins in Celsius (for dummy controls).
    weather_df["temperature_c"] = (weather_df["temperature"] - 32) * 5.0 / 9.0
    weather_df["t_range"] = (
        pd.cut(
            weather_df["temperature_c"],
            [-100, -10.0, 0, 10.0, 20.0, 30.0, 40.0, 100.0],
            include_lowest=True,
        )
        .astype(str)
    )

    # Create dummies for each temperature bin; ensure all expected bins exist as columns.
    temp_dummies = pd.get_dummies(weather_df["t_range"]).astype('Int8')
    for col_name, dummy_name in zip(col_names, dummy_names):
        weather_df[dummy_name] = temp_dummies[col_name] if col_name in temp_dummies.columns else 0

    return weather_df


def add_weather_data(flights_df: pd.DataFrame, db_source: str) -> pd.DataFrame:
    """
    Merge hourly weather controls onto flight-level observations by origin airport and time.

    For each origin airport, this function:
      1) loads and engineers hourly weather variables via `analyze_weather`
      2) performs an as-of merge from flights to weather on `DateTime`, allowing the nearest
         weather observation within a tolerance window

    Notes
    -----
    - `merge_asof` requires both inputs to be sorted by the merge key.
    - By default, `merge_asof` matches on the nearest key *at or before* the flight time.
      If you intend "nearest in either direction", pass `direction="nearest"`.

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level data containing `origin_airport_id` and `DateTime`.
    db_source : str
        Path to the SQLite database.

    Returns
    -------
    pd.DataFrame
        flights_df with weather variables appended.
    """
    merged_chunks = []

    # Process airport-by-airport to avoid loading all weather tables into memory at once.
    for airport_id, group in tqdm(
        flights_df.groupby("origin_airport_id"),
        total=flights_df["origin_airport_id"].nunique(),
        desc="Merging weather by origin airport",
    ):
        # Load and engineer hourly weather controls for this airport.
        weather = analyze_weather(airport_id, db_source).sort_values("DateTime")

        # merge_asof requires sorted keys; we merge within a +/- tolerance window.
        group = group.sort_values("DateTime")
        merged = pd.merge_asof(
            group,
            weather,
            on="DateTime",
            tolerance=timedelta(hours=2.5),
            direction="backward",
        )

        merged_chunks.append(merged)

    # Recombine all airport-level merges.
    flights_df = pd.concat(merged_chunks, ignore_index=True)
    return flights_df


def print_missing_data_summary(flights_df: pd.DataFrame) -> None:
    """
    Print a compact summary of missingness for key variables and overall row completeness.

    Reports, for each selected variable:
      - number of missing observations
      - percent missing (relative to total rows)

    Also reports the number/percent of rows with *any* missing value across columns.

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level dataset.
    """
    n = len(flights_df)

    # Selected “headline” missingness checks (variable-level).
    metrics = [
        ("Missing tail numbers (num_seats)", flights_df["num_seats"]),
        ("Missing weather (multiple variables)", flights_df["temp_30_40"]),
        ("Missing load factor (load_factor)", flights_df["load_factor"]),
    ]

    for label, s in metrics:
        miss_n = int(s.isna().sum())
        miss_pct = miss_n / n if n else 0.0
        print(f"{label:<41} {miss_n:>10,}  ({miss_pct:>6.2%})")

    # Row-level: any missing value in any column.
    miss_n = int(flights_df.isna().any(axis=1).sum())
    miss_pct = miss_n / n if n else 0.0
    print(f"{'Missing any flight data (any NA)':<41} {miss_n:>10,}  ({miss_pct:>6.2%})")
    print("")


def print_missing_flights(flights_df: pd.DataFrame) -> None:
    """
    Print a two-column table of missing-value counts by variable.

    This prints only columns with at least one missing value, sorted by missing count
    (descending). For readability in console output, the list is split into two side-by-side
    columns.

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level dataset.
    """
    print("Table of missing flight data:")

    # Count missing values per column and keep only columns with >0 missing.
    flights_na = flights_df.isna().sum()
    s = flights_na[flights_na > 0].sort_values(ascending=False)

    # If there are no missing values, print a friendly message and exit.
    if s.empty:
        print("    (no missing values)")
        print("")
        return

    # Build a tidy two-column layout for console printing.
    df = s.rename("na_count").reset_index().rename(columns={"index": "column"})
    k = int(np.ceil(len(df) / 2))

    left = df.iloc[:k].reset_index(drop=True)
    right = df.iloc[k:].reset_index(drop=True)

    two_col = pd.concat([left, right], axis=1)
    two_col.columns = ["column", "na_count", "column", "na_count"]

    # Indent the printed table so it visually nests under the header.
    indent = "    "
    print(indent + two_col.to_string(index=False).replace("\n", "\n" + indent))
    print("")


def print_variable_names(flights_df: pd.DataFrame) -> None:
    """
    Print the DataFrame's column names in a wrapped, readable format.

    Parameters
    ----------
    flights_df : pd.DataFrame
        Flight-level dataset (or any DataFrame).
    """
    print("Variable names:")
    pprint(flights_df.columns.tolist(), width=100, compact=True, indent=4)
    print("")


def save_csv_mergers(
    flights_df: pd.DataFrame,
    out_path: str | Path = "mergers_delay.csv",
    *,
    dropna: bool = False,
) -> None:
    col_list = [
        # Delay variables
        "dep_delay", "arr_delay",

        # Flight logistics
        "monopoly_route", "distance", "num_seats", "load_factor", "scheduled_flights",

        # Market concentration
        "hhi_origin", "hhi_origin_lagged", "hhi_dest", "hhi_dest_lagged",

        # Airport and airline ids
        "origin_airport_id", "dest_airport_id", "dot_id_reporting_airline",

        # Date time variables
        "scheduled_hour", "year", "month", "day_of_week",

        # Census variables
        "metro_pop_origin", "metro_pop_dest", "metro_gdp_capita_origin", "metro_gdp_capita_dest",

        # Weather variables
        "temp_n_infty_n_10", "temp_n_10_0", "temp_0_10", "temp_10_20",
        "temp_20_30", "temp_30_40", "temp_40_infty",
        "wind_speed", "wind_speed_squared", "wind_gust_speed", "wind_gust_dummy",

        # Weather dummies
        "is_raining", "is_snowing", "trace_rain", "trace_snow",

        # Hub size dummies
        "small_hub_airport_origin", "medium_hub_airport_origin", "large_hub_airport_origin",
        "small_hub_airport_dest", "medium_hub_airport_dest", "large_hub_airport_dest",
        "small_hub_airline_origin", "medium_hub_airline_origin", "large_hub_airline_origin",
        "small_hub_airline_dest", "medium_hub_airline_dest", "large_hub_airline_dest",

        # Market share variables
        "market_share_origin_lagged", "market_share_dest_lagged",
        "market_share_origin", "market_share_dest",

        # Misspecification test variables
        "market_share_squared_origin", "market_share_squared_dest",
        "market_share_squared_origin_lagged", "market_share_squared_dest_lagged",
        "hhi_minus_origin", "hhi_minus_dest",
        "hhi_minus_origin_lagged", "hhi_minus_dest_lagged",
    ]

    missing = [c for c in col_list if c not in flights_df.columns]
    if missing:
        raise KeyError(f"save_csv_mergers: missing columns: {missing}")

    save_df = flights_df.loc[:, col_list]

    if dropna:
        save_df = save_df.dropna(subset=col_list, how="any")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_df.to_csv(out_path, index=False)
