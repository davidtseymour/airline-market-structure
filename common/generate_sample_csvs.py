import sqlite3
import pandas as pd
from pathlib import Path

from pipelines.generate_sample import (
    create_sub_sample, determine_percent_flights, add_tail_numbers,
    add_segment, add_market_structure, misspecification_test, add_metro_level_statistics, get_depart_datetime,
    add_husize_dummies, add_hubsize_interactions, add_lagged_hubsize_interactions, create_merger_ids, add_weather_data,
    print_missing_flights, print_missing_data_summary, print_selection_criteria_flights, print_subsample_diagnosis,
    print_variable_names, save_csv_mergers
)

def main():
    #Settings:
    print_diag=True # print intermediate diagnostics

    save_full_data = False
    save_mergers = True

    # primitives
    here = Path(__file__).resolve().parent
    db_source = str((here / ".." / "delaydata.db").resolve())

    # constants
    pct_subsample =0.02 # percentage of flights included in the sample
    random_seed = 99

    # ----- GENERATES A RANDOM SUBSAMPLE FROM A SAMPLE OF FLIGHTS -----
    flights_df, num_total_flights = create_sub_sample(pct_subsample,db_source,random_seed)

    # number of flights after random sampling
    subsample_num_flights = len(flights_df)


    # Print diagnostics
    if print_diag:
        print_subsample_diagnosis(flights_df)


    # ----- AIRPORTS AND AIRLINES TO ANALYSE -----
    with sqlite3.connect(db_source) as conn:
        airports_to_analyze = pd.read_sql_query(
            """
                SELECT OriginAirportID AS origin_airport_id FROM airports_to_analyze
            """, conn)
        airlines_list = pd.read_sql_query(
            """
                SELECT 
                    DOT_ID_Reporting_Airline AS dot_id_reporting_airline 
                FROM airlines_to_analyze
            """, conn)

    # ----- CARRIER INFO TO ADD TO REGRESSIONS -----
        carrier_info = pd.read_sql_query(
            """
            SELECT 
                Airline_id AS airline_id, 
                unique_carrier_name, 
                start_date_source, 
                thru_date_source 
            FROM carrier_info
            """,
            conn)



    # ----- FIND INDEX TO REMOVE AIRLINES WITH FEWER THAN 1% OF FLIGHTS -----
    # Percent of flights by airline
    keep_large_airlines, large_airlines = determine_percent_flights(flights_df, carrier_info, airlines_list)


    # remove flights with origin and destination with fewer than 10 flights for origin or destination and from airlines
    # outside the continental United States
    keep_large_airports = (
        flights_df['origin_airport_id'].isin(airports_to_analyze['origin_airport_id']) &
        flights_df['dest_airport_id'].isin(airports_to_analyze['origin_airport_id'])
    )


    # ----- INFORMATION ON FLIGHTS THAT ARE BEING DROPPED BY NOT MEETING THE SELECTION CRITERIA -----

    print_selection_criteria_flights(num_total_flights,subsample_num_flights,keep_large_airports,
                                         keep_large_airlines)


    # ----- DROP FLIGHTS THAT DO NOT SATISFY THE CONDITIONS FOR FLIGHT AND AIRPORTS -----
    keep_obs_mask = keep_large_airlines & keep_large_airports
    flights_df = flights_df[keep_obs_mask].copy()


    # ----- ADD TAIL NUMBERS TO DATASET ----
    flights_df = add_tail_numbers(flights_df, db_source)


    # ----- CONNECT SEGMENT DATA TO THE DATASET -----
    flights_df = add_segment(flights_df, db_source, large_airlines, airports_to_analyze)


    # ----- ADD AIRPORT MARKET CONCENTRATION AND HUB SIZE -----
    flights_df = add_market_structure(flights_df, db_source)


    # ----- ADD MARKET SHARE AND MISSPECIFICATION TEST VARIABLES
    # Add additional market structure variables for misspecification tests
    flights_df = misspecification_test(flights_df, db_source)


    # ----- GET AGGREGATE FLIGHT LEVEL DATA -----
    with sqlite3.connect(db_source) as conn:
        flight_stats = pd.read_sql_query(
            """
            SELECT 
                DayofMonth as day_of_month,
                Month as month, 
                Year as year, 
                ScheduledFlights as scheduled_flights 
            FROM daily_flight_stats""",conn)

    flights_df = flights_df.merge(flight_stats,how='left',on=['day_of_month','year','month'])


    # ----- ADD METROPOLITAN STATISTICAL AREA INFO -----
    # - note: For missing observations, imputed the average values -> No missing values
    flights_df = add_metro_level_statistics(flights_df, db_source)


    # ----- DETERMINE DATETIME FROM COLUMNS -----
    flights_df = get_depart_datetime(flights_df)


    # ----- ADD HUB SIZE DUMMIES -----
    flights_df = add_husize_dummies(flights_df)


    # ----- MARKET STRUCTURE HUB SIZE INTERACTIONS -----
    flights_df = add_hubsize_interactions(flights_df)


    # ----- MARKET STRUCTURE HUB SIZE LAGGED INTERACTIONS -----
    flights_df = add_lagged_hubsize_interactions(flights_df)


    # ----- CREATE NEW ID FOR POST-MERGER AIRLINES -----
    flights_df = create_merger_ids(flights_df, db_source)


    # ----- ADDING WEATHER DATA -----
    flights_df = add_weather_data(flights_df, db_source)


    # ----- PRINTING THE MAIN SOURCES OF MISSING DATA -----
    print_missing_data_summary(flights_df)


    # ----- PRINT THE TABLE OF COUNT OF MISSING DATA BY VARIABLE NAME -----
    if print_diag:
        print_missing_flights(flights_df)

    if print_diag:
        print_variable_names(flights_df)

    flights_df = flights_df.dropna(axis=0, how='any')

    if save_full_data:
        # Save full dataset
        flights_df.to_csv("flights_df.csv", index=False)

    if save_mergers:
        # save mergers dataset
        save_csv_mergers(flights_df)



if __name__ == "__main__":
    main()
