library(ggplot2)
library(plyr)
library(reshape)

# Read all data
fitness = read.csv("fitness.csv", head=TRUE);
fitness$run = as.factor(fitness$run);
cfitness = ddply(fitness, c("t_sim", "run"), summarise, n=length(fitness), fit=mean(fitness), vel=mean(vel), fsd=sd(fitness), vsd=sd(vel))

wsum = read.csv("summary.csv", head=TRUE);
wsum$run = as.factor(wsum$run);
wsum$ppr = wsum$part_count / wsum$robot_count;

robots = read.csv("robots.csv", head=TRUE);
robots$run = as.factor(robots$run);

ggplot(cfitness, aes(t_sim)) +
  geom_ribbon(aes(ymin=fit-fsd, ymax=fit+fsd, colour=run, fill=run), linetype=0, alpha=0.2) +
  geom_line(aes(y=fit, colour=run)) +
  ylab("Average fitness") + xlab("Simulation time (s)");

ggplot(cfitness, aes(x=t_sim)) +
  xlab("Time (s)") + ylab("# of individuals") +
  geom_line(aes(y=n, colour=run));



#max_fit = fitness[order(-fitness$fitness),]


ggplot(wsum, aes(world_age)) +
  xlab("Time (s)") + ylab("Main battery charge") +
  geom_line(aes(y=charge, colour=run));

ggplot(wsum, aes(world_age)) +
  xlab("Time (s)") + ylab("Part count") +
  geom_line(aes(y=part_count, colour=run));

