### PLOTS 

# 0. Packages
# 1. Set path
# 2. Define country
# 2. Read data
# 3. Create coefficient such that both y-axis make sense.
# 4. Plots (absolute and relative employment change)


## 0 Packages======

rm(list=ls())
library(rlang)
library(highcharter)
library(vctrs)
library(plyr)
library(dplyr)
library(tidyverse)
library(xlsx)
library(doBy)
library(reshape)
library(fastDummies)
library(expss)
library(rgdal)
library(rlang)
library(sf)
library(ggplot2)
library(utils)
library(janitor)
library(haven)
library(readxl)
library(reldist)
library(questionr)
library(scales)


# Path - TO BE ADAPTED: In order for this code to run the working directory has to be set to the root
# folder where of country_household_results
# setwd

### 2. Define country list and scenario list
country_list<-list("BGR")


  
for (country in country_list) {
  
    
setwd(paste(country,"_household_results",sep=""))

pdf(file = (paste0(country,"_incidence.pdf")), width=12, height=6)
par(mar=c(3,2,1.5,1))

### 3. Read data
# table with tax burden per decile
taxburden<-read_excel('incidence.xlsx')
# table with per capita direct transfer
transfers<-read_excel('transfers.xlsx')

if (file.exists('public_infr.xlsx')) {
  public_inf <- read_excel('public_infr.xlsx')
}


### 4. Create coefficient such that both y-axis make sense. 
#(Setting differences of both vectors equal)
coeff_tb=(max(taxburden["abs_inc_MS"])-min(taxburden["abs_inc_MS"]))/(max(taxburden["rel_inc_MS"])-min(taxburden["rel_inc_MS"]))

### 5. Plots
#Plot 1 - Tax burden - base
p<-ggplot()+
  geom_bar(data=taxburden, aes(x =  quant_cons, y = abs_inc_MS/coeff_tb),stat="identity" ,fill = ifelse(taxburden$abs_inc_MS > 0, "#e58080", "#69c269"))+
  geom_point(data=taxburden, aes(x = quant_cons, y = rel_inc_MS, shape="Relative tax burden")) +
  geom_text(data = taxburden, aes(x = quant_cons, y = abs_inc_MS / coeff_tb, label = round(abs_inc_MS, 2)), 
            vjust = 0.5, size = 3, color = "black", position = position_stack(vjust = 0.5)) +
  scale_x_continuous(breaks = 1:10) +
  scale_y_continuous(
    
    # Features of the first axis
    name =  "Relative tax burden (in % of pre-policy expenditure)",
    labels = scales::percent,
    # Add a second axis and specify its features
    sec.axis = sec_axis(~.*coeff_tb, name= "Absolute tax burden (in 2019 US$)")
  )+
  labs(title=paste0("Tax burden (compensating variation) without beh. reactions", ", ", country," per expenditure decile"), x="")+
  theme_minimal()+
  theme(legend.position="left",axis.text.x=element_text(angle=90,hjust=1,vjust=0.5))
p<-p + guides(shape=guide_legend(title=""))
plot(p)

#Plot 2 - Labor demand change by isic 2d with table sector2d
tidy_name <- function(name, n_char) {
  ifelse(nchar(name) > (n_char - 2), 
         {substr(name, 1, n_char) %>% paste0(., "..")},
         name)
}

#Plot 2 - Tax burden - price reactions
p<-ggplot()+
  geom_bar(data=taxburden, aes(x =  quant_cons, y = abs_inc_ela_MS/coeff_tb),stat="identity" ,fill = ifelse(taxburden$abs_inc_ela_MS > 0, "#e58080", "#69c269"))+
  geom_point(data=taxburden, aes(x = quant_cons, y = rel_inc_ela_MS, shape="Relative tax burden"))+
  geom_text(data = taxburden, aes(x = quant_cons, y = abs_inc_ela_MS / coeff_tb, label = round(abs_inc_ela_MS, 2)), 
            vjust = 0.5, size = 3, color = "black", position = position_stack(vjust = 0.5)) +
  scale_x_continuous(breaks = 1:10) +
  scale_y_continuous(
    
    # Features of the first axis
    name =  "Relative tax burden (in % of pre-policy expenditure)",
    labels = scales::percent,
    
    # Add a second axis and specify its features
    sec.axis = sec_axis(~.*coeff_tb, name= "Absolute tax burden (in 2019 US$)")
  )+
  labs(title=paste0("Tax burden (compensating variation) with beh. reactions", ", ", country," per expenditure decile"), x="")+
  theme_minimal()+
  theme(legend.position="left",axis.text.x=element_text(angle=90,hjust=1,vjust=0.5))
p<-p + guides(shape=guide_legend(title=""))
plot(p)


#Plot 3 - Revenue Recycling / targeted transfer - no reactions
p<-ggplot()+
  geom_bar(data=transfers, aes(x =  quant_cons, y = abs_inc_RR/coeff_tb),stat="identity" ,fill = ifelse(transfers$abs_inc_RR > 0,"#e58080", "#69c269"))+
  geom_text(data = transfers, aes(x = quant_cons, y = abs_inc_RR / coeff_tb, label = round(abs_inc_RR,2)), 
            vjust = 0.5, size = 3, color = "black", position = position_stack(vjust = 0.5)) +
  geom_point(data=transfers, aes(x = quant_cons, y = rel_inc_RR, shape="Relative tax burden"))+
  scale_x_continuous(breaks = 1:10) +
  scale_y_continuous(
    
    # Features of the first axis --- add decile target as column in dataframe
    name =  "Relative tax burden (in % of pre-policy expenditure) with lump sum transfer",
    labels = scales::percent,
    # Add a second axis and specify its features
    sec.axis = sec_axis(~.*coeff_tb, name= "Absolute tax burden (in 2019 US$)")
  )+
  labs(title=paste0("Tax burden (compensating variation) with lump-sum transfer", ", ", country," per expenditure decile"), x="")+
  theme_minimal()+
  theme(legend.position="left",axis.text.x=element_text(angle=90,hjust=1,vjust=0.5))
p<-p + guides(shape=guide_legend(title=""))
plot(p)

# Plot 4 - Revenue Recycling/ targeted transfer - with reaction

p<-ggplot()+
  geom_bar(data=transfers, aes(x =  quant_cons, y = abs_inc_ela_RR/coeff_tb),stat="identity" ,fill = ifelse(transfers$abs_inc_ela_RR > 0,"#e58080", "#69c269"))+
   geom_text(data = transfers, aes(x = quant_cons, y = abs_inc_ela_RR / coeff_tb, label = round(abs_inc_ela_RR,2)), 
            vjust = 0.5, size = 3, color = "black", position = position_stack(vjust = 0.5)) +
  geom_point(data=transfers, aes(x = quant_cons, y = rel_inc_ela_RR, shape="Relative tax burden"))+
  scale_x_continuous(breaks = 1:10) +
  scale_y_continuous(
    
    # Features of the first axis
    name =  "Relative tax burden (in % of pre-policy expenditure) with lump-sum transfer + reaction",
    labels = scales::percent,
    # Add a second axis and specify its features
    sec.axis = sec_axis(~.*coeff_tb, name= "Absolute tax burden (in 2019 US$)")
  )+
  labs(title=paste0("Tax burden (compensating variation) with lump sum + beh. reactions", ", ", country," per expenditure decile"), x="")+
  theme_minimal()+
  theme(legend.position="left",axis.text.x=element_text(angle=90,hjust=1,vjust=0.5))
p<-p + guides(shape=guide_legend(title=""))
plot(p)


# Plot 5 - If public infrastructure access exists
if (file.exists('public_infr.xlsx')) {
  p<-ggplot()+
  geom_bar(data=public_inf, aes(x =  quant_cons, y = total_publ_infr_transfer),stat="identity" ,fill =  "#69c269")+
   geom_text(data = public_inf, aes(x = quant_cons, y = total_publ_infr_transfer, label = round(total_publ_infr_transfer,2)), 
            vjust = 0.5, size = 3, color = "black", position = position_stack(vjust = 0.5)) +
  scale_x_continuous(breaks = 1:10) +
  scale_y_continuous(
    
    # Features of the first axis
    name =  "Proxied per capita transfer",
  )+
  labs(title=paste0("Total proxied per capita transfer from investment in infrastructure access per expenditure decile","," ,country), x="")+
  theme_minimal()+
  theme(legend.position="left",axis.text.x=element_text(angle=90,hjust=1,vjust=0.5))
  p<-p + guides(shape=guide_legend(title=""))
  plot(p)

}
dev.off()

setwd('..') #Going back one directory level

}
# end file exist
