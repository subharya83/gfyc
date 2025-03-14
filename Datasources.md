# Open Data Sources for County-Level Mobility Factors

Here's a tabular overview of publicly available data sources that provide county-level information related to the underlying structural mobility factors. These sources offer free access through APIs or direct downloads without requiring paid API keys.

| Data Source | API/Access Method | Available Data | Geographic Level | Update Frequency | URL/Endpoint |
|-------------|-------------------|----------------|------------------|------------------|--------------|
| U.S. Census Bureau API | API Key (free) | Population, demographics, housing, income, education, commuting patterns | County, tract, block group | Annual/5-year estimates | https://www.census.gov/data/developers/data-sets.html |
| Bureau of Labor Statistics | API (no key required) | Employment, wages, job growth, industry composition | County, metro area | Monthly/Quarterly | https://www.bls.gov/developers/ |
| HUD Exchange | Open data portal | Housing affordability, rent estimates, housing problems | County | Annual | https://www.huduser.gov/portal/datasets/cp.html |
| USDA Economic Research Service | Direct download | Rural-urban classifications, natural amenities scale | County | Periodic | https://www.ers.usda.gov/data-products/ |
| Federal Reserve Economic Data (FRED) | API Key (free) | Economic indicators, housing prices, unemployment | County | Various | https://fred.stlouisfed.org/docs/api/fred/ |
| CDC WONDER | API/Direct download | Health statistics, mortality, climate data | County | Annual | https://wonder.cdc.gov/ |
| County Health Rankings | Direct download | Health outcomes, healthcare access, quality of life | County | Annual | https://www.countyhealthrankings.org/explore-health-rankings/rankings-data-documentation |
| IRS Statistics of Income | Direct download | Migration flows based on tax returns | County-to-county flows | Annual | https://www.irs.gov/statistics/soi-tax-stats-migration-data |
| National Center for Education Statistics | API/Direct download | School quality, educational attainment | County, school district | Annual | https://nces.ed.gov/datalab/ |
| FEMA National Risk Index | API/Direct download | Natural hazard risk metrics | County | Periodic | https://hazards.fema.gov/nri/ |
| Opportunity Insights | Direct download | Economic mobility, opportunity metrics | County, tract | Periodic | https://opportunityinsights.org/data/ |
| Zillow Housing Data | API (free tier) | Housing prices, rental rates, housing market health | County, ZIP | Monthly | https://www.zillow.com/research/data/ |
| MIT Living Wage Calculator | Direct download | Cost of living, living wage estimates | County | Annual | https://livingwage.mit.edu/ |
| NOAA Climate Data | API (no key required) | Temperature, precipitation, climate metrics | County | Monthly/Daily | https://www.ncdc.noaa.gov/cdo-web/webservices/v2 |
| Political Data | Direct download | Voting patterns, political preferences | County | Biennial/quadrennial | https://electionlab.mit.edu/data |

## Notes on Data Access:
1. **Census API**: While requiring a key, it's free and can be obtained instantly through their website by submitting a basic form.
2. **Integration potential**: Many of these datasets can be joined using FIPS county codes as the common identifier.
3. **Data cleaning**: County boundaries occasionally change, requiring standardization across time periods.
4. **Granularity**: Some sources offer sub-county data (census tract, block group) that can be aggregated to county level.
5. **Frequency limitations**: Some metrics are only updated during decennial census years or through 5-year ACS estimates.

## Specific Datasets to consider

### National Database of Childcare Prices (NDCP)
https://apiprod.dol.gov/v4/get/WB/ndcp/csv/metadata?X-API-KEY=nKYXz0hVPpbqF7ewuJWI_zAiV9QssCEhSdioPlTnWVE

### Mines
https://apiprod.dol.gov/v4/get/MSHA/mines/csv/metadata?X-API-KEY=nKYXz0hVPpbqF7ewuJWI_zAiV9QssCEhSdioPlTnWVE

