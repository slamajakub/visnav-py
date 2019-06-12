#!/bin/bash
WIN="50 60 70 80 90 100"
sigma_col="5 10 15 20 25 30"
sigma_space="10 20 30 40 50"
sigma_coeff="80 90 100 110 120 130"

for w in $WIN; do
	sudo DRI_PRIME=1 python3 src/batch1.py didy1w akaze+smn 70 False $w 5 10 100 >> output2.txt
done

for c in $sigma_col; do
	sudo DRI_PRIME=1 python3 src/batch1.py didy1w akaze+smn 70 False 20 $c 10 100 >> output2.txt
done

for s in $sigma_space; do
	sudo DRI_PRIME=1 python3 src/batch1.py didy1w akaze+smn 70 False 20 5 $s 100 >> output2.txt
done

for c in $sigma_coeff; do
	sudo DRI_PRIME=1 python3 src/batch1.py didy1w akaze+smn 70 False 20 5 10 $c >> output2.txt
done

