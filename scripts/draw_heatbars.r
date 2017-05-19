rm(list=ls())
#==== USER SECTION ==========
u_sheetName <- "BECCS (so far only bioenergy potential)"
#u_sheetName <- "Afforestation and Reforestation"
#u_sheetName <- "DAC"
u_sheetName <- "BECCS (Bioenergy)"
DEBUG       <- TRUE

#==== INITIALISE ==========
# Load libraries
library(googlesheets)
library(dplyr)
library(tidyr)
library(ggplot2)

source("heatbar_functions.R")

# Authorise googlesheets to access your Google Sheets account
gs_auth()


#==== READ IN SPREADSHEET ==========
gs  <- gs_title("NETs Review")
ss  <- gs_read(gs, ws = u_sheetName,verbose=DEBUG)

data <- get_data(ss)

################################################
## Generate a new df of ranges

ranges <- seq(1,1000)
df <- data.frame(v=ranges)

# Get a list of resources, or define it yourself
resources <- unique(
  data[data$measurement=="max" & data$variable!="cost",]$variable
)
resources <- resources[!is.na(resources)]

# Count the studies with a maximum under each range for each resource

res2050 <- countranges(df,filter(data,year=="2050"),resources)

heatbar(res2050,"pcnt") +
  labs(x="Resource",y="Potential [EJ/yr]")

ggsave("heatbar_example.png",width=8,height=5)



