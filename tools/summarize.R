# Use this script to summarize one or multiple concatenated
# runs of evolution data.
# This post helps here:
# http://stackoverflow.com/a/10349375/358873

library(ggplot2)
library(plyr)
library(reshape)

data = read.csv("generations.csv", head=TRUE)
cdata = ddply(data, c("gen"), summarise, Fitness=mean(fitness), Velocity=mean(vel), fsd=sd(fitness), vsd=sd(vel))
mdata = melt(cdata, id=c("gen", "fsd", "vsd"))

fcolor <- "#00A6DE"
vcolor <- "#B00000"


ggplot(mdata, aes(gen)) +
  geom_line(aes(y=value, colour=variable)) +
  geom_ribbon(data=cdata, aes(ymin=Fitness-fsd, ymax=Fitness+fsd), alpha=0.2, fill=fcolor, linetype=0) +
  geom_ribbon(data=cdata, aes(ymin=Velocity-vsd, ymax=Velocity+vsd), alpha=0.2, fill=vcolor, linetype=0) +
  scale_colour_manual(values=c(fcolor, vcolor), labels=c("Fitness*", "Velocity (m/s)"),
                      name="Variable") +
  xlab("Generation") +
  ylab("Value")