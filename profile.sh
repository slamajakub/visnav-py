#!/bin/bash
WIN="10 20 30 40 50 60 70"
sigma_col="10 20 30"
sigma_space="20"
sigma_coeff="100"

for sc in $sigma_col; do
    for w in $WIN; do
        sudo DRI_PRIME=1 python3 -m cProfile -o profiles/win-$w-$sc.out src/batch1.py didy1w akaze+smn 5 False True $w $sc $sigma_space $sigma_coeff
    done
done
