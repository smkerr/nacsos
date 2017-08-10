get_data <- function(ss){
  if (dim(ss)[1] <= 2) stop("No data in selected spreadsheet")
  
  #==== PROCESS DATA ==========
  # Get 3 header lines
  header1 <- names(ss)
  header2 <- paste(ss[1,])
  header3 <- paste(ss[2,])
  
  # Make a new data frame with the actual data
  data <- ss[3:dim(ss)[1], ]
  
  # loop through and combine the column names
  lcol1 <- ''
  lcol2 <- ''
  lcol3 <- ''
  separator <- 'Â§'
  for (col in seq(1,dim(ss)[2])) {
    h1 <- if (grepl('^X[0-9]+$',header1[col])) lcol1 else header1[col]
    lcol1 <- h1
    h2 <- if (grepl('^NA$',header2[col])) lcol2 else header2[col]
    lcol2 <- h2
    h3 <- if (grepl('^NA$',header3[col])) lcol3 else header3[col]
    lcol3 <- h3
    var <- paste(h1,h2,h3,sep=separator)
    names(data)[col] <- var
  } 
  
  # Switch the data to long format
  data <- data %>% 
    gather_("variable", "value",names(data)[7:dim(ss)[2]]) %>% 
    separate(variable, into=c("category", "subcategory", "variable"), sep="Â§") %>%
    separate(
      variable,into=c("variable","measurement"), 
      sep="\\.",fill="right",extra="drop"
    )
  
  
  names(data) <- gsub(separator,'',names(data))
  names(data) <- gsub('Dimensions','',names(data))
  
  return(data)
}

countranges <- function(df,data,headers, measure) {
  
  countrange <- function(x, resource, measure) {
    if (measure=="range") {
      dataf <- filter(
        suppressWarnings(mutate(data,value=as.numeric(value))),
        measurement %in% c("min","max"),
        variable==resource,
        !is.na(value)
      ) %>% spread(
        measurement, value
      ) %>%
      filter(
        min <=x,
        max >=x
      )
    } else {
      dataf <- filter(
        suppressWarnings(mutate(data,value=as.numeric(value))),
        measurement==measure,
        variable==resource,
        !is.na(value),
        value>=x
      )      
    }

    dataf$TI <- if ("TI" %in% names(dataf)) dataf$TI else dataf$UT
    if (length(dataf$TI) > length(unique(dataf$TI))) {
        print("warning, some titles seem to be duplicated, do you
            need to filter by a dimension?")       
    } 
    return(as.numeric(count(dataf)))
    }
  
  
  
  # For each resource, count the number of values under each threshold
  for (r in headers) {
    df[[r]] <- as.numeric(lapply(df$v,countrange, r, measure))
  }
  
  data_r_sum <- filter(
      suppressWarnings(mutate(data,value=as.numeric(value))),
      measurement %in% c("min","max"),
      !is.na(value)
    ) %>% spread(
      measurement, value
    ) %>%
    filter(
      !is.na(min),
      !is.na(max)
    ) %>% 
    group_by(variable) %>%
    summarise(
      maxvalue = n()
    )
    
  
  n_studies = length(unique(dataf$TI))
  
  # Gather the resources
  res <- df %>%
    gather(resource,value,-v) %>% #gather resources into a resource column
    group_by(resource) %>% 
    left_join(data_r_sum, by = c("resource" = "variable")) %>%
    mutate(pcnt=value/maxvalue*100) # calculate the value as a pcnt of the total
  
  return(res)
}

heatbar <- function(df,f) {
  flab <- if (f=="pcnt") "% of Studies" else "Number of Studies" 
  df <- df[df[[f]]>0,]
  df <- df %>%
    group_by(resource) %>%
    mutate(resourcelab=paste0(resource,'\n[',max(value),' studies]'))
  ggplot() +
    theme_bw() +
    geom_bar(
      data=df,
      aes_string(x="resourcelab",y=1,fill=f),
      stat="identity",
      width=0.6,
      color=NA
    ) +
    geom_bar(
      data=df,
      aes(x=resourcelab),
      fill=NA,
      color="grey22",
      width=0.6
    ) +
    scale_fill_gradientn(
      colours=c(NA,"#fffcef","#fcf0ba","#d30000"),
      values = scales::rescale(c(0,min(df[[f]]),max(df[[f]])/2,max(df[[f]]))),
      name=flab
    ) +
    guides(fill = guide_colourbar(reverse = TRUE))
}

