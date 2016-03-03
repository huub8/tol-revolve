library(ggplot2);
poses = read.csv("poses.csv", head=TRUE, colClasses=c('factor', 'numeric', 'numeric', 'numeric', 'numeric', 'numeric'));
poses$dist = sqrt(poses$x^2 + poses$y^2);
mlim = 7;

ggplot(data=poses, aes(x=x, y=y)) +
  stat_bin2d(bins=250) +
  xlim(-mlim, mlim) + ylim(-mlim, mlim);

#poses_hp = poses[poses$sec > 3600,];
#ggplot(data=poses_hp, aes(x=x, y=y)) + 
#  stat_bin2d(bins=500) +
#  xlim(-mlim, mlim) + ylim(-mlim, mlim);

#poses_hm = poses[poses$sec < 1800,];
#ggplot(data=poses_hm, aes(x=x, y=y)) + 
#  stat_bin2d(bins=500) +
#  xlim(-mlim, mlim) + ylim(-mlim, mlim);

#fittest = poses[poses$id==1043,];

#ggplot(data=fittest, aes(x=x, y=y)) +
#  xlim(-mlim, mlim) + ylim(-mlim, mlim) +
#  geom_point();