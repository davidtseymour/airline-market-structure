clear 
version 15

// THIS IS THE MAIN FILE FOR RUNNING THE AIRLINE REGRESSIONS FROM FLIGHT LEVEL DATA



// REGRESSION VARAIBLES
global WeatherVars "temp_ninfty_n10 temp_n10_0 temp_0_10 temp_20_30 temp_30_40 temp_40_infty windgustdummy windspeed windspeedsquare windgustspeed raindummy raintracedummy snowdummy snowtracedummy"
global CensusVars "originmetropop originmetrogdppercapita  destmetropop destmetrogdppercapita"
global AirportHubSizes "smallhubairportorigin mediumhubairportorigin largehubairportorigin smallhubairportdest mediumhubairportdest largehubairportdest"
global AirlineHubSizes "smallhubairlineorigin mediumhubairlineorigin largehubairlineorigin 	smallhubairlinedest mediumhubairlinedest largehubairlinedest"
global OtherVariables "loadfactor numflights distance monopolyroute capacity"
global MSdecomposed "nonhubairlinemarketorigin smallhubairlinemarketorigin mediumhubairlinemarketorigin largehubairlinemarketorigin nonhubairlinemarketdest smallhubairlinemarketdest mediumhubairlinemarketdest largehubairlinemarketdest"   
global HHIdecomposed "nonhubairlineconcorigin smallhubairlineconcorigin mediumhubairlineconcorigin largehubairlineconcorigin nonhubairlineconcdest smallhubairlineconcdest mediumhubairlineconcdest largehubairlineconcdest"  


 
// FIXED EFFECT VARIABLES 
global OriginFE "year month dayofweek scheduledhour uniquecarrier originairportid"
global OrigDestFE "year month dayofweek scheduledhour uniquecarrier originairportid destairportid"
global RouteFE "year month dayofweek scheduledhour uniquecarrier routecode"

// CLUSTER VARIABLES
global OriginCluster "cluster year month uniquecarrier"
global OrigDestCluster "cluster year month uniquecarrier"
global RouteCluster "cluster year month uniquecarrier"


import delimited "data/delay.csv" // data/delay.csv is not stored in the GitHub repo. Download from Harvard Dataverse and place in /data.
cap mkdir output


drop if depdelay <-100
drop if depdelay > 1000

egen routecode = concat(uniquecarrier originairportid destairportid)

replace capacity = capacity/ 100 
replace distance = distance/ 100
replace numflights = numflights/1000

replace originmetropop = originmetropop / 1000000
replace destmetropop = destmetropop / 1000000


// GENEARTE SUMMARY STATISTICS 

	
eststo clear

estpost sum

// Output to paper 



esttab using output/SummaryStatObs.tex ///
	, replace cell((mean(label(Mean) fmt(%9.3f)) sd(label(Std. Dev.) fmt(%9.3f)))) varwidth(25) nomtitle nonumber ///
	drop(uniquecarrier marketsharedest hhidest ///
	smallhubairportdest mediumhubairportdest largehubairportdest ///
	smallhubairlinedest mediumhubairlinedest largehubairlinedest ///
	nonhubairlineconcorigin smallhubairlineconcorigin mediumhubairlineconcorigin ///
	largehubairlineconcorigin nonhubairlineconcdest smallhubairlineconcdest mediumhubairlineconcdest ///
	largehubairlineconcdest nonhubairlinemarketorigin smallhubairlinemarketorigin ///
	mediumhubairlinemarketorigin largehubairlinemarketorigin nonhubairlinemarketdest ///
	smallhubairlinemarketdest mediumhubairlinemarketdest largehubairlinemarketdest ///
	year month dayofweek originairportid destairportid  ///
	scheduledhour marketsharesquareorigin marketsharesquaredest ///
	hhiminusorigin hhiminusdest nonhubairlinemarketsquareorigin smallhubairlinemarketsquareorigi ///
	mediumhubairlinemarketsquareorig largehubairlinemarketsquareorigi nonhubairlinemarketsquaredest ///
	smallhubairlinemarketsquaredest mediumhubairlinemarketsquaredest largehubairlinemarketsquaredest ///
	nonhubairlineconcminusorigin smallhubairlineconcminusorigin mediumhubairlineconcminusorigin ///
	largehubairlineconcminusorigin nonhubairlineconcminusdest smallhubairlineconcminusdest ///
	mediumhubairlineconcminusdest largehubairlineconcminusdest  ///
	temp_ninfty_n10 temp_n10_0 temp_0_10  ///
	temp_20_30 temp_30_40 temp_40_infty windspeed windspeedsquare windgustdummy ///
	windgustspeed raindummy raintracedummy snowdummy snowtracedummy ///
	originmetropop originmetrogdppercapita  destmetropop destmetrogdppercapita ///
	routecode hhiorigin_lagged hhidest_lagged marketshareoriginlagged ///
	marketsharesquareoriginlagged hhiminusorigin_lagged marketsharedestlagged ///
	marketsharesquaredestlagged hhiminusdest_lagged l_nonhubairlineconcorigin ///
	l_smallhubairlineconcorigin l_mediumhubairlineconcorigin ///
	l_largehubairlineconcorigin l_nonhubairlineconcdest l_smallhubairlineconcdest ///
	l_mediumhubairlineconcdest l_largehubairlineconcdest l_nonhubairlinemarketorigin ///
	l_smallhubairlinemarketorigin l_mediumhubairlinemarketorigin  ///
	l_largehubairlinemarketorigin l_nonhubairlinemarketdest l_smallhubairlinemarketdest ///
	l_mediumhubairlinemarketdest l_largehubairlinemarketdest l_nonhubairlinemarketsquaredest ///
	l_smallhubairlinemarketsquaredes l_mediumhubairlinemarketsquarede ///
	l_largehubairlinemarketsquaredes l_nonhubairlineconcminusdest ///
	l_smallhubairlineconcminusdest l_mediumhubairlineconcminusdest ///
	l_largehubairlineconcminusdest l_nonhubairlinemarketsquareorigi ///
	l_smallhubairlinemarketsquareori l_mediumhubairlinemarketsquareor ///
	l_largehubairlinemarketsquareori l_nonhubairlineconcminusorigin ///
	l_smallhubairlineconcminusorigin l_mediumhubairlineconcminusorigi ///
	l_largehubairlineconcminusorigin uniquecarrier_old)

	
eststo clear 



// BASIC REGRESSION - ORIGIN FE, ORIGIN/DEST FE
eststo: quietly reghdfe depdelay hhiorigin hhidest	/// 						Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce($OriginCluster )

eststo: quietly reghdfe depdelay hhiorigin hhidest	/// 						Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce($OrigDestCluster )

eststo: quietly reghdfe depdelay marketshareorigin marketsharedest	/// 						Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce($OriginCluster )
	
eststo: quietly reghdfe depdelay marketshareorigin marketsharedest	/// 						Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce($OrigDestCluster )
	
	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Market Share" "with DestFE" "Market Conc." "With DestFE") ///
	   order(marketshareorigin marketsharedest hhiorigin hhidest) 

	   
	   
// Tables for paper (Basic Regression)
esttab using output/SimpleRegression.tex, ///
	replace se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) ///
	mgroups("Market Concentration"  "Market Share", pattern(1 0 1 0)	///
		prefix(\multicolumn{@span}{c}{) suffix(})   ///
		span )         ///
	mtitles("Origin FE" "+ Destination FE" "Origin FE" "+ Destination FE") label  ///      
		order(marketshareorigin marketsharedest hhiorigin hhidest) ///
		drop(_cons $WeatherVars	$CensusVars $OtherVariables) 
	

	
	
eststo clear
	   

// Robustness checks - Carrier route FE regressions 

eststo: quietly reghdfe depdelay hhiorigin hhidest	/// 						Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce($RouteCluster )
	
eststo: quietly reghdfe depdelay marketshareorigin marketsharedest	/// 		Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce($RouteCluster )
	

	

esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Market Conc." "Market Share" ) ///
	   order(hhiorigin hhidest marketshareorigin marketsharedest ) 

// Tables for Paper (Basic Regression - Route FE)
esttab using output/SimpleAppendix.tex, ///
	replace wide se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) mtitles("Market Share"  "Market Conc." ) label  ///      
 	   order(marketshareorigin marketsharedest hhiorigin hhidest) ///
	   drop(_cons $WeatherVars	$CensusVars  $OtherVariables) 

	   

	   
// BASIC REGRESSION - MARKET SHARE MISSPECIFICAITON TEST
eststo clear

	
eststo: quietly reghdfe depdelay ///
	marketshareorigin marketsharedest hhiminusorigin hhiminusdest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce($OriginCluster )
	
	test (hhiminusorigin = 0) ( hhiminusdest = 0)

eststo: quietly reghdfe depdelay ///
	marketshareorigin marketsharedest hhiminusorigin hhiminusdest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce($OrigDestCluster )	
	
	test (hhiminusorigin = 0) ( hhiminusdest = 0)
	


	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Origin FE" "Origin/DestFE")   ///      
	order(marketshareorigin hhiminusorigin marketsharedest hhiminusdest) 

	
// Tables for Paper (Simple Regression - Market Share Misspecification)
esttab using output/SimpleMStest.tex, ///
	replace wide se star(* 0.10 ** 0.05 *** 0.01) varwidth(25) mtitles("Origin FE" "Origin/DestFE") label  ///      
	order(marketshareorigin hhiminusorigin marketsharedest hhiminusdest) ///
		drop(_cons $WeatherVars $CensusVars $AirportHubSizes $AirlineHubSizes $OtherVariables )    




		
	
// BASIC REGRESSION - MARKET CONCENTRATION MISSPECIFICAITON TEST
eststo clear
	
eststo: quietly reghdfe depdelay ///
	marketsharesquareorigin marketsharesquaredest hhiminusorigin hhiminusdest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce($OriginCluster )
	
	test (marketsharesquareorigin = hhiminusorigin) (marketsharesquaredest = hhiminusdest)

eststo: quietly reghdfe depdelay ///
	marketsharesquareorigin marketsharesquaredest hhiminusorigin hhiminusdest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce($OrigDestCluster )
	
	test (marketsharesquareorigin = hhiminusorigin) (marketsharesquaredest = hhiminusdest)
	

	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Origin FE" "Origin/DestFE" "Route FE")   ///      
	order(marketsharesquareorigin hhiminusorigin marketsharesquaredest hhiminusdest) 

// Tables for Paper (Simple Regression - Market Conc. Misspecification)
esttab using output/SimpleHHItest.tex, ///
	replace wide se star(* 0.10 ** 0.05 *** 0.01) varwidth(25) mtitles("Origin FE" "Origin/DestFE") label  ///      
 	   order(marketsharesquareorigin  hhiminusorigin marketsharesquaredest hhiminusdest) ///
	   drop(_cons $WeatherVars $CensusVars $AirportHubSizes $AirlineHubSizes $OtherVariables)    

	   
	   
// BASIC REGRESSION - ROUTE FIXED EFFECTS MISSPECIFICAITON TEST			
eststo clear
		
eststo: quietly reghdfe depdelay ///
	marketshareorigin marketsharedest hhiminusorigin hhiminusdest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce($RouteCluster )
	
	test (hhiminusorigin = 0) (hhiminusdest = 0	)
	
	eststo: quietly reghdfe depdelay ///
	marketsharesquareorigin marketsharesquaredest hhiminusorigin hhiminusdest /// Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE )	vce($RouteCluster )
	
	test (marketsharesquareorigin = hhiminusorigin) (marketsharesquaredest = hhiminusdest)

	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Market Share" "Market Conc.")   ///      
	order(marketshareorigin marketsharesquareorigin hhiminusorigin marketsharedest marketsharesquaredest hhiminusdest) 
	
	
// Tables for Paper (Simple Regression - Market Share Misspecification)
esttab using output/SimpleRouteFEtest.tex, ///
	replace wide se star(* 0.10 ** 0.05 *** 0.01) varwidth(25) mtitles("Market Share" "Market Conc.") label  ///      
		order(marketshareorigin marketsharesquareorigin hhiminusorigin marketsharedest marketsharesquaredest hhiminusdest)  ///
		drop(_cons $WeatherVars $CensusVars $AirportHubSizes $AirlineHubSizes $OtherVariables )   

	   
	   
	   
	   
eststo clear

// Regressions with decomposition of market structure effect by hubsize


eststo: quietly reghdfe depdelay $HHIdecomposed	/// 						Market Concentration
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce($OriginCluster )
	
	// Tests whether the decomposed variables are significantly different from each other
	test (nonhubairlineconcorigin = smallhubairlineconcorigin) ///
	(smallhubairlineconcorigin = mediumhubairlineconcorigin) /// 
	(mediumhubairlineconcorigin = largehubairlineconcorigin) 
	
	test (nonhubairlineconcdest = smallhubairlineconcdest) ///
	(smallhubairlineconcdest = mediumhubairlineconcdest) ///
	(mediumhubairlineconcdest =largehubairlineconcdest) 
	
	
	test (smallhubairlineconcorigin = mediumhubairlineconcorigin) /// 
	(mediumhubairlineconcorigin = largehubairlineconcorigin) 
	

putexcel set "output/BetaCovOrig.xlsx", sheet("CovMat") replace
putexcel A1=matrix(e(V)), names
putexcel set "output/RegResultOrig.xlsx", sheet("RegRes") replace
putexcel A1=matrix(e(b)), names

	
eststo: quietly reghdfe depdelay $HHIdecomposed	/// 						Market Concentration
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce($OrigDestCluster )
	
	// Tests whether the decoposed variables are significantly different from each other
	test (nonhubairlineconcorigin = smallhubairlineconcorigin) ///
	(smallhubairlineconcorigin = mediumhubairlineconcorigin) /// 
	(mediumhubairlineconcorigin = largehubairlineconcorigin) ///
	
	test (nonhubairlineconcdest = smallhubairlineconcdest) ///
	(smallhubairlineconcdest = mediumhubairlineconcdest) ///
	(mediumhubairlineconcdest = largehubairlineconcdest) 
	
	test (smallhubairlineconcorigin = mediumhubairlineconcorigin) /// 
	(mediumhubairlineconcorigin = largehubairlineconcorigin) 
	

	
putexcel set "output/BetaCovDest.xlsx", sheet("CovMat") replace
putexcel A1=matrix(e(V)), names
putexcel set "output/RegResultDest.xlsx", sheet("RegRes") replace
putexcel A1=matrix(e(b)), names


eststo: quietly reghdfe depdelay $MSdecomposed	/// 						Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables	$WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce($OriginCluster )

eststo: quietly reghdfe depdelay $MSdecomposed	/// 						Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables	$WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce($OrigDestCluster )
	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Market Share" "with DestFE" "Market Conc." "With DestFE") ///
		order($MSdecomposed $HHIdecomposed ) 	
	
// Table for paper (Decomposed Regression)
esttab using output/DecomposedRegression.tex, ///
	replace wide se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) mtitles("Market Conc." "With DestFE" "Market Share" "with DestFE") label  ///      
 	   order($HHIdecomposed $MSdecomposed) ///
	   drop(_cons $WeatherVars $CensusVars $OtherVariables) 
	

eststo clear	
 
//  Route fixed effects with hubsize decomposition with carrier fixed effects

eststo: quietly reghdfe depdelay $HHIdecomposed ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce($RouteCluster )	
	
	// Tests whether the decoposed variables are significantly different from each other
	test (nonhubairlineconcorigin = smallhubairlineconcorigin) ///
	(smallhubairlineconcorigin = mediumhubairlineconcorigin) /// 
	(mediumhubairlineconcorigin = largehubairlineconcorigin) ///
	
	test (nonhubairlineconcdest = smallhubairlineconcdest) ///
	(smallhubairlineconcdest = mediumhubairlineconcdest) ///
	(mediumhubairlineconcdest = largehubairlineconcdest) 
	
	test (smallhubairlineconcorigin = mediumhubairlineconcorigin) /// 
	(mediumhubairlineconcorigin = largehubairlineconcorigin) 
	
eststo: quietly reghdfe depdelay $MSdecomposed /// 						Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce($RouteCluster )
	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Market Share" "Market Conc." ) ///
	order($MSdecomposed $HHIdecomposed )

esttab using output/DecomposedAppendix.tex, ///
	replace wide se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) mtitles("Market Conc." "Market Share") label  ///      
 	   order($HHIdecomposed $MSdecomposed) ///
	   drop(_cons $WeatherVars $CensusVars  $OtherVariables )
		   

		   
// Regressions with decomponsition and market share test	
eststo clear


eststo: quietly reghdfe depdelay 	/// 						Market Share
	nonhubairlinemarketorigin smallhubairlinemarketorigin ///
	mediumhubairlinemarketorigin largehubairlinemarketorigin ///
	nonhubairlineconcminusorigin smallhubairlineconcminusorigin ///
	mediumhubairlineconcminusorigin largehubairlineconcminusorigin ///
	nonhubairlinemarketdest smallhubairlinemarketdest ///
	mediumhubairlinemarketdest largehubairlinemarketdest ///
	nonhubairlineconcminusdest smallhubairlineconcminusdest ///
	mediumhubairlineconcminusdest largehubairlineconcminusdest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE )	vce($OriginCluster )
						
test (nonhubairlineconcminusorigin = 0) (smallhubairlineconcminusorigin = 0) ///
	(mediumhubairlineconcminusorigin = 0) (largehubairlineconcminusorigin = 0) ///
	(nonhubairlineconcminusdest = 0) (smallhubairlineconcminusdest = 0) ///
	(mediumhubairlineconcminusdest = 0) (largehubairlineconcminusdest = 0)

eststo: quietly reghdfe depdelay 	/// 						Market Share
	nonhubairlinemarketorigin smallhubairlinemarketorigin ///
	nonhubairlineconcminusorigin smallhubairlineconcminusorigin ///
	mediumhubairlineconcminusorigin largehubairlineconcminusorigin ///
	mediumhubairlinemarketorigin largehubairlinemarketorigin ///
	nonhubairlinemarketdest smallhubairlinemarketdest ///
	mediumhubairlinemarketdest largehubairlinemarketdest ///
	nonhubairlineconcminusdest smallhubairlineconcminusdest ///
	mediumhubairlineconcminusdest largehubairlineconcminusdest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce($OrigDestCluster )	

test (nonhubairlineconcminusorigin = 0) (smallhubairlineconcminusorigin = 0) ///
	(mediumhubairlineconcminusorigin = 0) (largehubairlineconcminusorigin = 0) ///
	(nonhubairlineconcminusdest = 0) (smallhubairlineconcminusdest = 0) ///
	(mediumhubairlineconcminusdest = 0) (largehubairlineconcminusdest = 0)
	
eststo: quietly reghdfe depdelay 	/// 						Market Share
	nonhubairlinemarketorigin smallhubairlinemarketorigin ///
	mediumhubairlinemarketorigin largehubairlinemarketorigin ///
	nonhubairlineconcminusorigin smallhubairlineconcminusorigin ///
	mediumhubairlineconcminusorigin largehubairlineconcminusorigin ///
	nonhubairlinemarketdest smallhubairlinemarketdest ///
	mediumhubairlinemarketdest largehubairlinemarketdest ///
	nonhubairlineconcminusdest smallhubairlineconcminusdest ///
	mediumhubairlineconcminusdest largehubairlineconcminusdest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce($RouteCluster )

test (nonhubairlineconcminusorigin = 0) (smallhubairlineconcminusorigin = 0) ///
	(mediumhubairlineconcminusorigin = 0) (largehubairlineconcminusorigin = 0) ///
	(nonhubairlineconcminusdest = 0) (smallhubairlineconcminusdest = 0) ///
	(mediumhubairlineconcminusdest = 0) (largehubairlineconcminusdest = 0)

	   
	esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers  ///
	mtitles("Origin FE" "Origin/DestFE" "Route FE")         
	


esttab using output/DecomposedMStest.tex, ///
	replace wide se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) mtitles("Origin FE" "with Origin/Dest FE" "Route FE") label  ///      
		order(    nonhubairlineconcminusorigin smallhubairlineconcminusorigin ///
	mediumhubairlineconcminusorigin largehubairlineconcminusorigin ///
	nonhubairlineconcminusdest smallhubairlineconcminusdest ///
	mediumhubairlineconcminusdest largehubairlineconcminusdest) ///
		drop(_cons nonhubairlinemarketorigin smallhubairlinemarketorigin ///
	mediumhubairlinemarketorigin largehubairlinemarketorigin ///
	nonhubairlinemarketdest smallhubairlinemarketdest ///
	mediumhubairlinemarketdest largehubairlinemarketdest ///	
	$AirportHubSizes $AirlineHubSizes $WeatherVars $CensusVars $OtherVariables)
	


	
// Regressions with decomponsition and HHI test
eststo clear


eststo: quietly reghdfe depdelay 	/// 						Market Share
	nonhubairlinemarketsquareorigin smallhubairlinemarketsquareorigi ///
	mediumhubairlinemarketsquareorig largehubairlinemarketsquareorigi ///
	nonhubairlineconcminusorigin smallhubairlineconcminusorigin ///
	mediumhubairlineconcminusorigin largehubairlineconcminusorigin ///
	nonhubairlinemarketsquaredest smallhubairlinemarketsquaredest ///
	mediumhubairlinemarketsquaredest largehubairlinemarketsquaredest ///
	nonhubairlineconcminusdest smallhubairlineconcminusdest ///
	mediumhubairlineconcminusdest largehubairlineconcminusdest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce($OriginCluster )

test (nonhubairlinemarketsquareorigin = nonhubairlineconcminusorigin) ///
	(smallhubairlinemarketsquareorigi =	smallhubairlineconcminusorigin) ///
	(mediumhubairlinemarketsquareorig = mediumhubairlineconcminusorigin) ///
	(largehubairlinemarketsquareorigi = largehubairlineconcminusorigin) ///
	(nonhubairlinemarketsquaredest = nonhubairlineconcminusdest) ///
	(smallhubairlinemarketsquaredest =	smallhubairlineconcminusdest) ///
	(mediumhubairlinemarketsquaredest = mediumhubairlineconcminusdest) ///
	(largehubairlinemarketsquaredest = largehubairlineconcminusdest)
	
eststo: quietly reghdfe depdelay 	/// 						Market Share
	nonhubairlinemarketsquareorigin smallhubairlinemarketsquareorigi ///
	mediumhubairlinemarketsquareorig largehubairlinemarketsquareorigi ///
	nonhubairlineconcminusorigin smallhubairlineconcminusorigin ///
	mediumhubairlineconcminusorigin largehubairlineconcminusorigin ///
	nonhubairlinemarketsquaredest smallhubairlinemarketsquaredest ///
	mediumhubairlinemarketsquaredest largehubairlinemarketsquaredest ///
	nonhubairlineconcminusdest smallhubairlineconcminusdest ///
	mediumhubairlineconcminusdest largehubairlineconcminusdest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce($OrigDestCluster )	

test (nonhubairlinemarketsquareorigin = nonhubairlineconcminusorigin) ///
	(smallhubairlinemarketsquareorigi =	smallhubairlineconcminusorigin) ///
	(mediumhubairlinemarketsquareorig = mediumhubairlineconcminusorigin) ///
	(largehubairlinemarketsquareorigi = largehubairlineconcminusorigin) ///
	(nonhubairlinemarketsquaredest = nonhubairlineconcminusdest) ///
	(smallhubairlinemarketsquaredest =	smallhubairlineconcminusdest) ///
	(mediumhubairlinemarketsquaredest = mediumhubairlineconcminusdest) ///
	(largehubairlinemarketsquaredest = largehubairlineconcminusdest)
		
	
eststo: quietly reghdfe depdelay 	/// 						Market Share
	nonhubairlinemarketsquareorigin smallhubairlinemarketsquareorigi ///
	mediumhubairlinemarketsquareorig largehubairlinemarketsquareorigi ///
	nonhubairlineconcminusorigin smallhubairlineconcminusorigin ///
	mediumhubairlineconcminusorigin largehubairlineconcminusorigin ///
	nonhubairlinemarketsquaredest smallhubairlinemarketsquaredest ///
	mediumhubairlinemarketsquaredest largehubairlinemarketsquaredest ///
	nonhubairlineconcminusdest smallhubairlineconcminusdest ///
	mediumhubairlineconcminusdest largehubairlineconcminusdest ///
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce($RouteCluster )

test (nonhubairlinemarketsquareorigin = nonhubairlineconcminusorigin) ///
	(smallhubairlinemarketsquareorigi =	smallhubairlineconcminusorigin) ///
	(mediumhubairlinemarketsquareorig = mediumhubairlineconcminusorigin) ///
	(largehubairlinemarketsquareorigi = largehubairlineconcminusorigin) ///
	(nonhubairlinemarketsquaredest = nonhubairlineconcminusdest) ///
	(smallhubairlinemarketsquaredest =	smallhubairlineconcminusdest) ///
	(mediumhubairlinemarketsquaredest = mediumhubairlineconcminusdest) ///
	(largehubairlinemarketsquaredest = largehubairlineconcminusdest)
		
	   
	esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers  ///
	mtitles("Origin FE" "Origin/DestFE" "Route FE")         


esttab using output/DecomposedHHItest.tex, ///
	replace wide se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) mtitles("Origin FE" "Origin/Dest FE" "Route FE") label  ///      
 	   order(  nonhubairlinemarketsquareorigin  nonhubairlineconcminusorigin  ///
	smallhubairlinemarketsquareorigi 	smallhubairlineconcminusorigin ///
	mediumhubairlinemarketsquareorig  mediumhubairlineconcminusorigin ///
	largehubairlinemarketsquareorigi  largehubairlineconcminusorigin ///
	nonhubairlinemarketsquaredest  nonhubairlineconcminusdest ///
	smallhubairlinemarketsquaredest 	smallhubairlineconcminusdest ///
	mediumhubairlinemarketsquaredest  mediumhubairlineconcminusdest ///
	largehubairlinemarketsquaredest  largehubairlineconcminusdest) ///
	   drop(_cons $WeatherVars $CensusVars $OtherVariables ///
	smallhubairportorigin mediumhubairportorigin largehubairportorigin ///		Origin Airport Hubs
	smallhubairportdest mediumhubairportdest largehubairportdest ///			Destination Airport Hubs
	smallhubairlineorigin mediumhubairlineorigin largehubairlineorigin ///		Origin Airline Hubs
	smallhubairlinedest mediumhubairlinedest largehubairlinedest)    
	