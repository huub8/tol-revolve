library(ggplot2)
library(plyr)
library(reshape)

fitness = read.csv("fitness.csv", head=TRUE);
cfitness = ddply(fitness, c("t_sim"), summarise, n=length(fitness), fit=mean(fitness), vel=mean(vel), fsd=sd(fitness), vsd=sd(vel))

fcolor <- "#00A6DE";

ggplot(cfitness, aes(t_sim)) +
  geom_line(aes(y=fit), colour=fcolor) +
  geom_ribbon(data=cfitness, aes(ymin=fit-fsd, ymax=fit+fsd), alpha=0.2, fill=fcolor, linetype=0);

ggplot(cfitness, aes(x=t_sim, y=n)) +
  geom_point() + geom_line();