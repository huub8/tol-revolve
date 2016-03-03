library(plyr);
library(ggplot2);

# Read all data
fitness = read.csv("fitness.csv", head=TRUE);
fitness$run = as.factor(fitness$run);

# Filter outliers...
#fitness = fitness[fitness$fitness<0.01,];
cfitness = ddply(fitness, c("t_sim", "run"), summarise, n=length(fitness), fit=mean(fitness), vel=mean(vel), fsd=sd(fitness), vsd=sd(vel))

wsum = read.csv("summary.csv", head=TRUE);
wsum = rename(wsum, c("world_age"="t_sim"));
wsum$run = as.factor(wsum$run);
wsum$ppr = wsum$part_count / wsum$robot_count;

# Dummy facetting (I don't understand this, yet)
# https://github.com/hadley/ggplot2/wiki/Align-two-plots-on-a-page
cfitness$panel = "Fitness";
cfitness2 = cfitness;
cfitness2$panel = "# of individuals";
wsum$panel = "# of robot parts";
wsum2 = wsum;
wsum2$panel = "Avg parts / robot"
wsum3 = wsum;
wsum3$panel = "Main battery charge";

ggplot(data = cfitness, mapping = aes(t_sim, colour=run, fill=run)) +
  facet_grid(panel~., scale="free") +
  geom_ribbon(data=cfitness, aes(ymin=fit-fsd, ymax=fit+fsd), linetype=0, alpha=0.2) +
  geom_line(data=cfitness, aes(y=fit)) +
  geom_line(data=cfitness2, aes(y=n)) +
  geom_line(data=wsum, aes(y=part_count)) +
  geom_line(data=wsum2, aes(y=ppr)) +
  geom_line(data=wsum3, aes(y=charge)) +
  scale_colour_discrete(name="Run") +
  scale_fill_discrete(guide=FALSE) +
  ylab("") + xlab("Simulation time (s)");

