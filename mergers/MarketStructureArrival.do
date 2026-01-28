// THIS IS THE MAIN FILE FOR RUNNING THE AIRLINE REGRESSIONS FOR ARRIVAL DELAYS 

version 15
clear all
set more off

// OUTPUT DIRECTORY
global DataDir "data"
global OutDir "output"

global OutSubdir "${OutDir}/arr"
cap mkdir "${OutDir}"
cap mkdir "${OutSubdir}"

// REGRESSION VARAIBLES
global WeatherVars "temp_n_infty_n_10 temp_n_10_0 temp_0_10 temp_20_30 temp_30_40 temp_40_infty wind_gust_dummy wind_speed wind_speed_squared wind_gust_speed is_raining trace_rain is_snowing trace_snow"
global CensusVars "metro_pop_origin metro_gdp_capita_origin  metro_pop_dest metro_gdp_capita_dest"
global AirportHubSizes "small_hub_airport_origin medium_hub_airport_origin large_hub_airport_origin small_hub_airport_dest medium_hub_airport_dest large_hub_airport_dest"
global AirlineHubSizes "small_hub_airline_origin medium_hub_airline_origin large_hub_airline_origin small_hub_airline_dest medium_hub_airline_dest large_hub_airline_dest"
global OtherVariables "load_factor scheduled_flights distance monopoly_route num_seats"

 
// FIXED EFFECT VARIABLES 
global OriginFE "year month day_of_week scheduled_hour dot_id_reporting_airline origin_airport_id"
global OrigDestFE "year month day_of_week scheduled_hour dot_id_reporting_airline origin_airport_id dest_airport_id"
global RouteFE "year month day_of_week scheduled_hour dot_id_reporting_airline route_code"


// CLUSTER VARIABLES
global OriginCluster "year month dot_id_reporting_airline"
global OrigDestCluster "year month dot_id_reporting_airline"
global RouteCluster "year month dot_id_reporting_airline"

import delimited "${DataDir}/delay.csv", clear // data/delay.csv is not stored in the GitHub repo. Download from Harvard Dataverse and place in /data.

// Drop extreme values
drop if arr_delay < -100
drop if arr_delay > 1000

egen route_code = group(dot_id_reporting_airline origin_airport_id dest_airport_id)

replace num_seats = num_seats / 100
replace distance = distance / 100
replace scheduled_flights = scheduled_flights / 1000

replace metro_pop_origin = metro_pop_origin / 1000000
replace metro_pop_dest = metro_pop_dest / 1000000


// --------------------------------------------------------------
// -------------- Airline Regressions - No IVS ------------------
// --------------------------------------------------------------

// BASIC REGRESSION - ORIGIN FE, ORIGIN/DEST FE
eststo clear

eststo: quietly reghdfe arr_delay hhi_origin hhi_dest	/// 
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce(cluster $OriginCluster )

eststo: quietly reghdfe arr_delay hhi_origin hhi_dest	/// 
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce(cluster $OrigDestCluster )

eststo: quietly reghdfe arr_delay market_share_origin market_share_dest	///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce(cluster $OriginCluster )
	
eststo: quietly reghdfe arr_delay market_share_origin market_share_dest	///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce(cluster $OrigDestCluster )
	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Market Conc." "With DestFE" "Market Share" "with DestFE") ///
	   order(hhi_origin hhi_dest market_share_origin market_share_dest) 
	   
esttab using "${OutSubdir}/SimpleRegression.tex", ///
	replace se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label ///
	mgroups("Market Concentration"  "Market Share", pattern(1 0 1 0)	///
		prefix(\multicolumn{@span}{c}{) suffix(})   ///
		span )         ///
		nomtitle  ///      
		order(hhi_origin hhi_dest market_share_origin market_share_dest) ///
		drop(_cons $WeatherVars	$CensusVars $OtherVariables) 

	
// IV REGRESSION - ORIGIN FE, ORIGIN/DEST FE IV 
eststo clear

eststo: quietly ivreghdfe arr_delay (hhi_origin hhi_dest = hhi_origin_lagged hhi_dest_lagged) 	///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce(cluster $OriginCluster )

eststo: quietly ivreghdfe arr_delay (hhi_origin hhi_dest = hhi_origin_lagged hhi_dest_lagged)	/// 	
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce(cluster $OrigDestCluster )

eststo: quietly ivreghdfe arr_delay (market_share_origin market_share_dest = market_share_origin_lagged market_share_dest_lagged)	/// 
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce(cluster $OriginCluster )
	
eststo: quietly ivreghdfe arr_delay (market_share_origin market_share_dest = market_share_origin_lagged market_share_dest_lagged)	/// 			
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce(cluster $OrigDestCluster )
	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Market Conc." "With DestFE" "Market Share" "with DestFE") ///
	   order(hhi_origin hhi_dest market_share_origin market_share_dest ) 
   
esttab using "${OutSubdir}/SimpleRegressionIV.tex", ///
	replace se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label ///
	mgroups("Market Concentration"  "Market Share", pattern(1 0 1 0)	///
		prefix(\multicolumn{@span}{c}{) suffix(})  ///
		span )         ///
		nomtitle  ///      
		order(hhi_origin hhi_dest market_share_origin market_share_dest) ///
		drop(_cons $WeatherVars	$CensusVars $OtherVariables) 


// ROBUSTNESS CHECKS - CARRIER ROUTE FIXED EFFECTS
eststo clear

eststo: quietly reghdfe arr_delay hhi_origin hhi_dest	/// 						
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce(cluster $RouteCluster )

eststo: quietly ivreghdfe arr_delay (hhi_origin hhi_dest = hhi_origin_lagged hhi_dest_lagged)	/// 					
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce(cluster $RouteCluster )

eststo: quietly reghdfe arr_delay market_share_origin market_share_dest	/// 
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce(cluster $RouteCluster )
	
eststo: quietly ivreghdfe arr_delay (market_share_origin market_share_dest = market_share_origin_lagged market_share_dest_lagged)	///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce(cluster $RouteCluster )

esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mgroups("Market Concentration"  "Market Share", pattern(1 0 1 0)	///
	prefix(\multicolumn{@span}{c}{) suffix(}) span) ///
	mtitles("Linear Regression" "IV Regression" "Linear Regression" "IV Regression" ) ///
	   order(hhi_origin hhi_dest market_share_origin market_share_dest ) 

esttab using "${OutSubdir}/SimpleFEappendix.tex", ///
	replace wide se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label  ///      
	mgroups("Market Concentration"  "Market Share", pattern(1 0 1 0)	///
		prefix(\multicolumn{@span}{c}{) suffix(})   ///
		span )         ///
		nomtitle  ///      
 	order(hhi_origin hhi_dest market_share_origin market_share_dest ) ///
	   drop(_cons $WeatherVars	$CensusVars  $OtherVariables ) 
	
	
// BASIC REGRESSION - MARKET CONCENTRATION MISSPECIFICAITON TEST
eststo clear
	
eststo: quietly reghdfe arr_delay ///
	market_share_squared_origin market_share_squared_dest hhi_minus_origin hhi_minus_dest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce(cluster $OriginCluster )
	
	test (market_share_squared_origin = hhi_minus_origin) (market_share_squared_dest = hhi_minus_dest)

eststo: quietly reghdfe arr_delay ///
	market_share_squared_origin market_share_squared_dest hhi_minus_origin hhi_minus_dest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce(cluster $OrigDestCluster )
	
	test (market_share_squared_origin = hhi_minus_origin) (market_share_squared_dest = hhi_minus_dest)
	
eststo: quietly ivreghdfe arr_delay ///
	(market_share_squared_origin market_share_squared_dest hhi_minus_origin hhi_minus_dest = ///
		market_share_squared_origin_lagged market_share_squared_dest_lagged hhi_minus_origin_lagged hhi_minus_dest_lagged) ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce(cluster $OriginCluster )
	
	test (market_share_squared_origin = hhi_minus_origin) (market_share_squared_dest = hhi_minus_dest)

eststo: quietly ivreghdfe arr_delay ///
	(market_share_squared_origin market_share_squared_dest hhi_minus_origin hhi_minus_dest = ///
		market_share_squared_origin_lagged market_share_squared_dest_lagged hhi_minus_origin_lagged hhi_minus_dest_lagged) ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce(cluster $OrigDestCluster )
	
	test (market_share_squared_origin = hhi_minus_origin) (market_share_squared_dest = hhi_minus_dest)
	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Linear: Origin FE" "Linear: +Dest FE" "IV: Origin FE" "IV: +Dest FE") ///
	order(market_share_squared_origin hhi_minus_origin market_share_squared_dest hhi_minus_dest) 

esttab using "${OutSubdir}/SimpleHHItest.tex", ///
	replace wide se star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label ///
	mgroups("Linear" "IV", pattern(1 0 1 0)	///
		prefix(\multicolumn{@span}{c}{) suffix(})   ///
		span )         ///
		nomtitle  ///  
	order(market_share_squared_origin  hhi_minus_origin market_share_squared_dest hhi_minus_dest) ///
	drop(_cons $WeatherVars $CensusVars $AirportHubSizes $AirlineHubSizes $OtherVariables)    	   
	   
	   
// BASIC REGRESSION - MARKET SHARE MISSPECIFICAITON TEST
eststo clear
	
eststo: quietly reghdfe arr_delay ///
	market_share_origin market_share_dest hhi_minus_origin hhi_minus_dest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce(cluster $OriginCluster )
	
	test (hhi_minus_origin = 0) ( hhi_minus_dest = 0)

eststo: quietly reghdfe arr_delay ///
	market_share_origin market_share_dest hhi_minus_origin hhi_minus_dest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce(cluster $OrigDestCluster )	
	
	test (hhi_minus_origin = 0) ( hhi_minus_dest = 0)
	
eststo: quietly ivreghdfe arr_delay ///
	(market_share_origin market_share_dest hhi_minus_origin hhi_minus_dest =  ///
	market_share_origin_lagged market_share_dest_lagged hhi_minus_origin_lagged hhi_minus_dest_lagged) ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce(cluster $OriginCluster )
	
	test (hhi_minus_origin = 0) ( hhi_minus_dest = 0)

eststo: quietly ivreghdfe arr_delay ///
	(market_share_origin market_share_dest hhi_minus_origin hhi_minus_dest =  ///
	market_share_origin_lagged market_share_dest_lagged hhi_minus_origin_lagged hhi_minus_dest_lagged) ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce(cluster $OrigDestCluster )	
	
	test (hhi_minus_origin = 0) ( hhi_minus_dest = 0)
	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Origin FE" "Origin/DestFE")   ///      
	order(market_share_origin hhi_minus_origin market_share_dest hhi_minus_dest) 

// Tables for Paper (Simple Regression - Market Share Misspecification)
esttab using "${OutSubdir}/SimpleMStest.tex", ///
	replace wide se star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label  ///      
	mgroups("Market Concentration"  "Market Share", pattern(1 0 1 0)	///
		prefix(\multicolumn{@span}{c}{) suffix(})   ///
		span )         ///
		nomtitle  ///  
	order(market_share_origin hhi_minus_origin market_share_dest hhi_minus_dest) ///
		drop(_cons $WeatherVars $CensusVars $AirportHubSizes $AirlineHubSizes $OtherVariables )    
	

// BASIC REGRESSION - ROUTE FIXED EFFECTS MISSPECIFICAITON TEST			
eststo clear
		
eststo: quietly reghdfe arr_delay ///
	market_share_squared_origin market_share_squared_dest hhi_minus_origin hhi_minus_dest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE )	vce(cluster $RouteCluster )
	
	test (market_share_squared_origin = hhi_minus_origin) (market_share_squared_dest = hhi_minus_dest)

eststo: quietly ivreghdfe arr_delay ///
	(market_share_squared_origin market_share_squared_dest hhi_minus_origin hhi_minus_dest = ///
		market_share_squared_origin_lagged market_share_squared_dest_lagged hhi_minus_origin_lagged hhi_minus_dest_lagged) ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE )	vce(cluster $RouteCluster )

	test (market_share_squared_origin = hhi_minus_origin) (market_share_squared_dest = hhi_minus_dest)	
	
eststo: quietly reghdfe arr_delay ///
	market_share_origin market_share_dest hhi_minus_origin hhi_minus_dest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce(cluster $RouteCluster )
	
	test (hhi_minus_origin = 0) (hhi_minus_dest = 0	)

eststo: quietly ivreghdfe arr_delay ///
	(market_share_origin market_share_dest hhi_minus_origin hhi_minus_dest =  ///
	market_share_origin_lagged market_share_dest_lagged hhi_minus_origin_lagged hhi_minus_dest_lagged) ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce(cluster $RouteCluster )
	
	test (hhi_minus_origin = 0) (hhi_minus_dest = 0	)
	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Market Share" "Market Conc.")   ///      
	order(market_share_origin market_share_squared_origin hhi_minus_origin market_share_dest market_share_squared_dest hhi_minus_dest) 
	
esttab using "${OutSubdir}/SimpleRouteFEtest.tex", ///
	replace wide se star(* 0.10 ** 0.05 *** 0.01) varwidth(25) ///
	mtitles("Linear" "IV" "Linear" "IV") label  ///      
	mgroups("Market Concentration"  "Market Share", pattern(1 0 1 0)	///
		prefix(\multicolumn{@span}{c}{) suffix(})   ///
		span )         ///
	order(market_share_squared_origin hhi_minus_origin market_share_squared_dest hhi_minus_dest) ///
		drop(_cons market_share_origin market_share_dest $WeatherVars $CensusVars  ///
		$AirportHubSizes $AirlineHubSizes $OtherVariables ) 
		