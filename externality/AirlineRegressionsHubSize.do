clear
version 15

// THIS IS THE MAIN FILE FOR RUNNING THE AIRLINE REGRESSIONS FROM FLIGHT LEVEL DATA



// REGRESSION VARAIBLES
global WeatherVars "temp_ninfty_n10 temp_n10_0 temp_0_10 temp_20_30 temp_30_40 temp_40_infty windgustdummy windspeed windspeedsquare windgustspeed raindummy raintracedummy snowdummy snowtracedummy"
global CensusVars "originmetropop originmetrogdppercapita  destmetropop destmetrogdppercapita"
global AirportHubSizes "smallhubairportorigin mediumhubairportorigin largehubairportorigin smallhubairportdest mediumhubairportdest largehubairportdest"
global AirlineHubSizes "smallhubairlineorigin mediumhubairlineorigin largehubairlineorigin 	smallhubairlinedest mediumhubairlinedest largehubairlinedest"
global OtherVariables "loadfactor numflights distance monopolyroute capacity"
global HHIdecomposed "nonhubairlineconcorigin smallhubairlineconcorigin mediumhubairlineconcorigin largehubairlineconcorigin nonhubairlineconcdest smallhubairlineconcdest mediumhubairlineconcdest largehubairlineconcdest"  
global HHIdecomposed_lagged "l_nonhubairlineconcorigin l_smallhubairlineconcorigin l_mediumhubairlineconcorigin l_largehubairlineconcorigin l_nonhubairlineconcdest l_smallhubairlineconcdest l_mediumhubairlineconcdest l_largehubairlineconcdest"  


 
// FIXED EFFECT VARIABLES 
global OriginFE "year month dayofweek scheduledhour uniquecarrier originairportid"
global OrigDestFE "year month dayofweek scheduledhour uniquecarrier originairportid destairportid"
global RouteFE "year month dayofweek scheduledhour uniquecarrier routecode"

// CLUSTER VARIABLES
global OriginCluster "cluster year month uniquecarrier"
global OrigDestCluster "cluster year month uniquecarrier"
global RouteCluster "cluster year month uniquecarrier"


import delimited delay/delay_data_cleaned.csv // delay/delay_data_cleaned.csv is not stored in the GitHub repo. Download from Harvard Dataverse and place in data/.


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

esttab using results/SummaryStatObs.tex ///
	, replace cell((mean(label(Mean) fmt(%9.3f)) sd(label(Std. Dev.) fmt(%9.3f)))) varwidth(25) nomtitle nonumber ///
	drop(uniquecarrier marketsharedest hhidest ///
	smallhubairportdest marketshareorigin mediumhubairportdest largehubairportdest ///
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


// *****************************************************************************	   
// BASIC REGRESSION - ORIGIN FE, ORIGIN/DEST FE
// *****************************************************************************	   

eststo: quietly reghdfe depdelay hhiorigin hhidest	/// 						Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce($OriginCluster )

	
	putexcel set "data/BasicBetaCovOrig.xlsx", sheet("CovMat") replace
	putexcel A1=matrix(e(V)), names
	putexcel set "data/BasicRegResultOrig.xlsx", sheet("RegRes") replace
	putexcel A1=matrix(e(b)), names

	
eststo: quietly reghdfe depdelay hhiorigin hhidest	/// 						Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce($OrigDestCluster )
	
	putexcel set "data/BasicBetaCovDest.xlsx", sheet("CovMat") replace
	putexcel A1=matrix(e(V)), names
	putexcel set "data/BasicRegResultDest.xlsx", sheet("RegRes") replace
	putexcel A1=matrix(e(b)), names

eststo: quietly ivreghdfe depdelay (hhiorigin hhidest =  ///
	hhiorigin_lagged hhidest_lagged) 	/// 						Market Concentration
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OriginFE ) vce($OriginCluster )
	
	putexcel set "data/BasicBetaCovOrigIV.xlsx", sheet("CovMat") replace
	putexcel A1=matrix(e(V)), names
	putexcel set "data/BasicRegResultOrigIV.xlsx", sheet("RegRes") replace
	putexcel A1=matrix(e(b)), names

	// IV test statistics 
	scalar KP_UNID= e(idstat) 
	scalar KP_UNID_pvalue = e(idpval)
	scalar KP_WID= e(widstat) 
	
	display "Kleibergen-Paap LM Statistic: " KP_UNID " (p-value: " KP_UNID_pvalue ")"
	display "Kleibergen-Paap Wald F-statistic (Weak Identification Test): " KP_WID	
	
eststo: quietly ivreghdfe depdelay (hhiorigin hhidest =  ///
	hhiorigin_lagged hhidest_lagged) 	/// 		
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($OrigDestFE ) vce($OrigDestCluster )

	putexcel set "data/BasicBetaCovDestIV.xlsx", sheet("CovMat") replace
	putexcel A1=matrix(e(V)), names
	putexcel set "data/BasicRegResultDestIV.xlsx", sheet("RegRes") replace
	putexcel A1=matrix(e(b)), names
	
	
	// IV test statistics 
	scalar KP_UNID= e(idstat) 
	scalar KP_UNID_pvalue = e(idpval)
	scalar KP_WID= e(widstat) 
	
	display "Kleibergen-Paap LM Statistic: " KP_UNID " (p-value: " KP_UNID_pvalue ")"
	display "Kleibergen-Paap Wald F-statistic (Weak Identification Test): " KP_WID	
	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Origin FE" "Origin, Dest FE" "Route FE") ///
	   order(marketshareorigin marketsharedest hhiorigin hhidest) 

	   
	   
	   
// Tables for paper (Basic Regression)
esttab using results/SimpleRegression.tex, ///
	replace se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) ///
	 label  ///      
		order(hhiorigin hhidest) ///
		drop(_cons $WeatherVars	$CensusVars $OtherVariables) 
	
	   






// *****************************************************************************	   
// Regressions with decomposition of market structure effect by hubsize
// *****************************************************************************

eststo clear

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
	

putexcel set "data/BetaCovOrig.xlsx", sheet("CovMat") replace
putexcel A1=matrix(e(V)), names
putexcel set "data/RegResultOrig.xlsx", sheet("RegRes") replace
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
	

	
putexcel set "data/BetaCovDest.xlsx", sheet("CovMat") replace
putexcel A1=matrix(e(V)), names
putexcel set "data/RegResultDest.xlsx", sheet("RegRes") replace
putexcel A1=matrix(e(b)), names

eststo: quietly ivreghdfe depdelay ($HHIdecomposed = $HHIdecomposed_lagged) 	/// 						Market Concentration
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
	

	// IV test statistics 
	scalar KP_UNID= e(idstat) 
	scalar KP_UNID_pvalue = e(idpval)
	scalar KP_WID= e(widstat) 
	
	display "Kleibergen-Paap LM Statistic: " KP_UNID " (p-value: " KP_UNID_pvalue ")"
	display "Kleibergen-Paap Wald F-statistic (Weak Identification Test): " KP_WID	
		
	
putexcel set "data/BetaCovOrigIV.xlsx", sheet("CovMat") replace
putexcel A1=matrix(e(V)), names
putexcel set "data/RegResultOrigIV.xlsx", sheet("RegRes") replace
putexcel A1=matrix(e(b)), names

	
eststo: quietly ivreghdfe depdelay ($HHIdecomposed = $HHIdecomposed_lagged) 	/// 						Market Concentration
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
	
	
	// IV test statistics 
	scalar KP_UNID= e(idstat) 
	scalar KP_UNID_pvalue = e(idpval)
	scalar KP_WID= e(widstat) 
	
	display "Kleibergen-Paap LM Statistic: " KP_UNID " (p-value: " KP_UNID_pvalue ")"
	display "Kleibergen-Paap Wald F-statistic (Weak Identification Test): " KP_WID	
	
	
putexcel set "data/BetaCovDestIV.xlsx", sheet("CovMat") replace
putexcel A1=matrix(e(V)), names
putexcel set "data/RegResultDestIV.xlsx", sheet("RegRes") replace
putexcel A1=matrix(e(b)), names
	
	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	order($HHIdecomposed )

// Table for paper (Decomposed Regression)
esttab using results/DecomposedRegression.tex, ///
	replace se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25)   ///      
 	   order($HHIdecomposed) ///
	   drop(_cons $WeatherVars $CensusVars $OtherVariables) 

   

	   
	
	
	

// *****************************************************************************	   
// BASIC IV REGRESSION - ORIGIN FE, ORIGIN/DEST FE
// *****************************************************************************	   

eststo clear


eststo: quietly reghdfe depdelay hhiorigin hhidest	/// 						Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce($RouteCluster )

	
eststo: quietly quietly ivreghdfe depdelay (hhiorigin hhidest =  ///
	hhiorigin_lagged hhidest_lagged) 	/// 								Market Share
	$AirportHubSizes $AirlineHubSizes $OtherVariables $WeatherVars $CensusVars, /// 
	absorb($RouteFE ) vce($RouteCluster )


	// IV test statistics 
	scalar KP_UNID= e(idstat) 
	scalar KP_UNID_pvalue = e(idpval)
	scalar KP_WID= e(widstat) 
	
	display "Kleibergen-Paap LM Statistic: " KP_UNID " (p-value: " KP_UNID_pvalue ")"
	display "Kleibergen-Paap Wald F-statistic (Weak Identification Test): " KP_WID	 
	

esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	mtitles("Origin FE" "Origin, Dest FE" "Route FE") ///
	   order(marketshareorigin marketsharedest hhiorigin hhidest) 

	   
	   
	   
// Tables for paper (Basic Regression)
esttab using results/SimpleRegressionFE.tex, ///
	replace wide se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) ///
	 label  ///      
		order(hhiorigin hhidest) ///
		drop($WeatherVars	$CensusVars $OtherVariables) 
	

	
		

// *****************************************************************************	   
// IV Regressions with decomposition of market structure effect by hubsize
// *****************************************************************************
eststo clear

	

	
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
	
	putexcel set "data/BetaCovRoute.xlsx", sheet("CovMat") replace
	putexcel A1=matrix(e(V)), names
	putexcel set "data/RegResultRoute.xlsx", sheet("RegRes") replace
	putexcel A1=matrix(e(b)), names

	eststo: quietly ivreghdfe depdelay ($HHIdecomposed = $HHIdecomposed_lagged) ///
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
	
	putexcel set "data/BetaCovRouteIV.xlsx", sheet("CovMat") replace
	putexcel A1=matrix(e(V)), names
	putexcel set "data/RegResultRouteIV.xlsx", sheet("RegRes") replace
	putexcel A1=matrix(e(b)), names
		
	// IV test statistics 
	scalar KP_UNID= e(idstat) 
	scalar KP_UNID_pvalue = e(idpval)
	scalar KP_WID= e(widstat) 
	
	display "Kleibergen-Paap LM Statistic: " KP_UNID " (p-value: " KP_UNID_pvalue ")"
	display "Kleibergen-Paap Wald F-statistic (Weak Identification Test): " KP_WID	

	
esttab, se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25) label nonumbers ///
	order($HHIdecomposed)
	

// Table for paper (Decomposed Regression)
esttab using results/DecomposedRegressionFE.tex, ///
	replace wide se stats(r2 N) star(* 0.10 ** 0.05 *** 0.01) varwidth(25)   ///      
 	   order($HHIdecomposed) ///
	   drop(_cons $WeatherVars $CensusVars $OtherVariables) 

